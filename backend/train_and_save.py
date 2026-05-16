#!/usr/bin/env python3
"""
Train ALS collaborative filtering model on MovieLens data and save to disk.

Run from the backend/ directory:
    python3 train_and_save.py
"""

import logging
import os
import shutil
import sys

# ── Java 17 required for PySpark 3.5 ──────────────────────────────────────
# PySpark 3.5 is compiled for Java 17 (class file version 61).
# Force JAVA_HOME to Java 17+ regardless of the shell environment.
_JAVA17 = "/opt/homebrew/Cellar/openjdk@17/17.0.17/libexec/openjdk.jdk/Contents/Home"
_JAVA21 = "/Library/Java/JavaVirtualMachines/temurin-21.jdk/Contents/Home"
for _jpath in (_JAVA17, _JAVA21):
    if os.path.isdir(_jpath):
        os.environ["JAVA_HOME"] = _jpath
        break

from pyspark.ml.evaluation import RegressionEvaluator
from pyspark.ml.recommendation import ALS
from pyspark.sql import SparkSession
from pyspark.sql import functions as F
from pyspark.sql.types import FloatType, IntegerType, LongType, StringType, StructField, StructType

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    stream=sys.stdout,
)
logger = logging.getLogger(__name__)

# ── Paths ─────────────────────────────────────────────────────────────────────

_BACKEND_DIR = os.path.dirname(os.path.abspath(__file__))
_PROJECT_ROOT = os.path.dirname(_BACKEND_DIR)

# Candidate data paths — check both flat and ml-latest-small layouts
_RATINGS_CANDIDATES = [
    os.path.join(_PROJECT_ROOT, "data", "ratings.csv"),
    os.path.join(_PROJECT_ROOT, "data", "ml-latest-small", "ratings.csv"),
    os.path.join(_BACKEND_DIR, "data", "ratings.csv"),
]
_MOVIES_CANDIDATES = [
    os.path.join(_PROJECT_ROOT, "data", "movies.csv"),
    os.path.join(_PROJECT_ROOT, "data", "ml-latest-small", "movies.csv"),
    os.path.join(_BACKEND_DIR, "data", "movies.csv"),
]

MODELS_DIR = os.path.join(_PROJECT_ROOT, "models")
ALS_MODEL_PATH = os.path.join(MODELS_DIR, "als_model")
MOVIES_PARQUET_PATH = os.path.join(MODELS_DIR, "movies_metadata.parquet")
USERS_PARQUET_PATH = os.path.join(MODELS_DIR, "sample_users.parquet")


def _find_file(candidates):
    for path in candidates:
        if os.path.exists(path):
            return path
    return None


# ── Spark ─────────────────────────────────────────────────────────────────────

def build_spark() -> SparkSession:
    spark = (
        SparkSession.builder
        .appName("MovieLensTraining")
        .master("local[*]")
        .config("spark.driver.memory", "4g")
        .config("spark.sql.shuffle.partitions", "20")
        .getOrCreate()
    )
    spark.sparkContext.setLogLevel("WARN")
    return spark


# ── Data loading ──────────────────────────────────────────────────────────────

def load_ratings(spark: SparkSession, path: str):
    schema = StructType([
        StructField("userId",    IntegerType(), nullable=False),
        StructField("movieId",   IntegerType(), nullable=False),
        StructField("rating",    FloatType(),   nullable=False),
        StructField("timestamp", LongType(),    nullable=True),
    ])
    return (
        spark.read
        .option("header", "true")
        .schema(schema)
        .csv(path)
        .dropna(subset=["userId", "movieId", "rating"])
        .dropDuplicates(["userId", "movieId"])
        .filter(F.col("rating").between(0.5, 5.0))
    )


def load_movies(spark: SparkSession, path: str):
    schema = StructType([
        StructField("movieId", IntegerType(), nullable=False),
        StructField("title",   StringType(),  nullable=True),
        StructField("genres",  StringType(),  nullable=True),
    ])
    return (
        spark.read
        .option("header", "true")
        .schema(schema)
        .csv(path)
    )


# ── Training ──────────────────────────────────────────────────────────────────

def train(spark: SparkSession, ratings_path: str, movies_path: str) -> None:
    logger.info("Loading ratings from %s", ratings_path)
    ratings = load_ratings(spark, ratings_path)
    ratings.cache()

    logger.info("Loading movies from %s", movies_path)
    movies = load_movies(spark, movies_path)

    # Dataset stats
    total_ratings = ratings.count()
    unique_users  = ratings.select("userId").distinct().count()
    unique_movies = ratings.select("movieId").distinct().count()
    rating_stats  = ratings.select(
        F.mean("rating").alias("mean"),
        F.expr("percentile_approx(rating, 0.5)").alias("median"),
        F.min("rating").alias("min"),
        F.max("rating").alias("max"),
    ).collect()[0]

    print("\n" + "=" * 55)
    print("  DATASET STATISTICS")
    print("=" * 55)
    print(f"  Total ratings   : {total_ratings:>10,}")
    print(f"  Unique users    : {unique_users:>10,}")
    print(f"  Unique movies   : {unique_movies:>10,}")
    print(f"  Rating mean     : {rating_stats['mean']:>10.3f}")
    print(f"  Rating median   : {rating_stats['median']:>10.3f}")
    print(f"  Rating range    : {rating_stats['min']:.1f} – {rating_stats['max']:.1f}")
    print("=" * 55 + "\n")

    train_df, test_df = ratings.randomSplit([0.8, 0.2], seed=42)
    train_df.cache()
    test_df.cache()

    logger.info("Training ALS model (rank=10, maxIter=10, regParam=0.1) …")
    als = ALS(
        userCol="userId",
        itemCol="movieId",
        ratingCol="rating",
        rank=10,
        maxIter=10,
        regParam=0.1,
        coldStartStrategy="drop",
        nonnegative=True,
        seed=42,
    )
    model = als.fit(train_df)

    evaluator = RegressionEvaluator(
        metricName="rmse", labelCol="rating", predictionCol="prediction"
    )
    train_rmse = evaluator.evaluate(model.transform(train_df))
    test_rmse  = evaluator.evaluate(model.transform(test_df))

    print(f"  Training RMSE: {train_rmse:.4f}")
    print(f"  Test RMSE    : {test_rmse:.4f}\n")

    # Save ALS model
    os.makedirs(MODELS_DIR, exist_ok=True)
    if os.path.exists(ALS_MODEL_PATH):
        logger.info("Removing previous model …")
        shutil.rmtree(ALS_MODEL_PATH)
    model.save(ALS_MODEL_PATH)
    logger.info("ALS model saved → %s", ALS_MODEL_PATH)

    # Save movies metadata as parquet
    movies_pd = movies.toPandas()
    movies_pd.to_parquet(MOVIES_PARQUET_PATH, index=False)
    logger.info("Movies metadata saved → %s", MOVIES_PARQUET_PATH)

    # Save up to 1000 sample user IDs as parquet
    sample_users = (
        ratings.select("userId")
        .distinct()
        .orderBy("userId")
        .limit(1000)
    )
    sample_users.toPandas().to_parquet(USERS_PARQUET_PATH, index=False)
    logger.info("Sample users saved → %s", USERS_PARQUET_PATH)

    print("=" * 55)
    print("  ARTEFACTS SAVED")
    print("=" * 55)
    print(f"  ALS model     : {ALS_MODEL_PATH}")
    print(f"  Movies parquet: {MOVIES_PARQUET_PATH}")
    print(f"  Users parquet : {USERS_PARQUET_PATH}")
    print("=" * 55)
    print("\nNext step: cd backend && uvicorn app.main:app --port 8003\n")


# ── Entry point ───────────────────────────────────────────────────────────────

def main() -> None:
    ratings_path = _find_file(_RATINGS_CANDIDATES)
    movies_path  = _find_file(_MOVIES_CANDIDATES)

    if not ratings_path:
        logger.error("ratings.csv not found. Download MovieLens data first:")
        logger.error("  cd data && bash download_movielens.sh")
        sys.exit(1)

    if not movies_path:
        logger.error("movies.csv not found. Download MovieLens data first:")
        logger.error("  cd data && bash download_movielens.sh")
        sys.exit(1)

    spark = build_spark()
    try:
        train(spark, ratings_path, movies_path)
    finally:
        spark.stop()
        logger.info("Spark stopped.")


if __name__ == "__main__":
    main()
