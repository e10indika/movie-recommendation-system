#!/usr/bin/env python3
"""
Train the ALS recommendation model on MovieLens data and persist artefacts.

Run once from the project root before starting the backend:
    python train_and_save.py

Produces:
    backend/data/ratings.csv          - raw ratings (downloaded)
    backend/data/movies.csv           - movie metadata (downloaded)
    backend/model/saved_als_model/    - trained Spark ALS model
    backend/model/top_movies.json     - pre-computed popular movies list
"""

import io
import json
import logging
import os
import shutil
import urllib.request
import zipfile

from pyspark.ml.evaluation import RegressionEvaluator
from pyspark.ml.recommendation import ALS
from pyspark.sql import SparkSession
from pyspark.sql import functions as F
from pyspark.sql.types import (
    FloatType, IntegerType, LongType, StringType,
    StructField, StructType,
)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s %(levelname)s  %(message)s',
    datefmt='%H:%M:%S',
)
logger = logging.getLogger(__name__)

# ── Paths (resolved relative to this script) ──────────────────────────────────
_HERE           = os.path.dirname(os.path.abspath(__file__))
DATA_DIR        = os.path.join(_HERE, 'backend', 'data')
MODEL_DIR       = os.path.join(_HERE, 'backend', 'model')
MODEL_PATH      = os.path.join(MODEL_DIR, 'saved_als_model')
TOP_MOVIES_PATH = os.path.join(MODEL_DIR, 'top_movies.json')
RATINGS_CSV     = os.path.join(DATA_DIR, 'ratings.csv')
MOVIES_CSV      = os.path.join(DATA_DIR, 'movies.csv')

ML_URL = 'https://files.grouplens.org/datasets/movielens/ml-latest-small.zip'


# ── Data download ──────────────────────────────────────────────────────────────

def download_movielens() -> None:
    """Download MovieLens ml-latest-small if not already cached."""
    if os.path.exists(RATINGS_CSV):
        logger.info('MovieLens data already present — skipping download.')
        return

    logger.info('Downloading MovieLens ml-latest-small …')
    os.makedirs(DATA_DIR, exist_ok=True)
    os.makedirs(MODEL_DIR, exist_ok=True)

    with urllib.request.urlopen(ML_URL) as resp:
        zf = zipfile.ZipFile(io.BytesIO(resp.read()))

    for name in zf.namelist():
        if name.endswith('ratings.csv'):
            with open(RATINGS_CSV, 'wb') as f:
                f.write(zf.read(name))
        elif name.endswith('movies.csv'):
            with open(MOVIES_CSV, 'wb') as f:
                f.write(zf.read(name))

    logger.info('Download complete.')


# ── Spark session ──────────────────────────────────────────────────────────────

def build_spark() -> SparkSession:
    spark = (
        SparkSession.builder
        .appName('ALS-Training')
        .master('local[*]')
        .config('spark.driver.memory', '4g')
        .config('spark.sql.shuffle.partitions', '20')
        .getOrCreate()
    )
    spark.sparkContext.setLogLevel('WARN')
    return spark


# ── Data loading ───────────────────────────────────────────────────────────────

def load_ratings(spark: SparkSession):
    """Load, validate, and deduplicate the ratings CSV."""
    schema = StructType([
        StructField('userId',    IntegerType(), nullable=False),
        StructField('movieId',   IntegerType(), nullable=False),
        StructField('rating',    FloatType(),   nullable=False),
        StructField('timestamp', LongType(),    nullable=False),
    ])
    return (
        spark.read
        .option('header', 'true')
        .schema(schema)
        .csv(RATINGS_CSV)
        .dropna()
        .dropDuplicates(['userId', 'movieId'])
        .filter(F.col('rating').between(0.5, 5.0))
        .filter((F.col('userId') > 0) & (F.col('movieId') > 0))
        .select('userId', 'movieId', 'rating')
    )


def load_movies(spark: SparkSession):
    schema = StructType([
        StructField('movieId', IntegerType(), nullable=False),
        StructField('title',   StringType(),  nullable=False),
        StructField('genres',  StringType(),  nullable=True),
    ])
    return (
        spark.read
        .option('header', 'true')
        .schema(schema)
        .csv(MOVIES_CSV)
    )


# ── Model training ─────────────────────────────────────────────────────────────

def train_als(train_df):
    """Train ALS with the hyperparameters chosen during notebook CV."""
    als = ALS(
        userCol           = 'userId',
        itemCol           = 'movieId',
        ratingCol         = 'rating',
        rank              = 20,     # latent factor dimensionality
        maxIter           = 15,     # convergence iterations
        regParam          = 0.05,   # L2 regularisation
        coldStartStrategy = 'drop', # drop NaN predictions for unseen users/items
        nonnegative       = False,
        implicitPrefs     = False,  # explicit star ratings
        seed              = 42,
    )
    logger.info('Training ALS model …')
    model = als.fit(train_df)
    logger.info('Training complete.')
    return model


def evaluate_model(model, test_df) -> float:
    evaluator = RegressionEvaluator(
        metricName    = 'rmse',
        labelCol      = 'rating',
        predictionCol = 'prediction',
    )
    rmse = evaluator.evaluate(model.transform(test_df))
    logger.info(f'Test RMSE: {rmse:.4f}')
    return rmse


# ── Persist artefacts ──────────────────────────────────────────────────────────

def save_model(model) -> None:
    if os.path.exists(MODEL_PATH):
        logger.info('Removing previous model …')
        shutil.rmtree(MODEL_PATH)
    model.save(MODEL_PATH)
    logger.info(f'Model saved → {MODEL_PATH}')


def save_top_movies(ratings_df, movies_df, min_ratings: int = 50, limit: int = 50) -> None:
    """
    Pre-compute the most popular movies and write to top_movies.json.
    The backend serves this file directly — no Spark query on each request.
    """
    top = (
        ratings_df.groupBy('movieId')
        .agg(
            F.count('rating')            .alias('num_ratings'),
            F.round(F.avg('rating'), 4)  .alias('avg_rating'),
        )
        .filter(F.col('num_ratings') >= min_ratings)
        .join(movies_df.select('movieId', 'title', 'genres'), on='movieId', how='left')
        .orderBy(F.desc('num_ratings'))
        .limit(limit)
        .select('movieId', 'title', 'genres', 'num_ratings', 'avg_rating')
        .collect()
    )

    data = [
        {
            'movieId':     int(row['movieId']),
            'title':       row['title']  or 'Unknown',
            'genres':      row['genres'] or 'Unknown',
            'num_ratings': int(row['num_ratings']),
            'avg_rating':  float(row['avg_rating']),
        }
        for row in top
    ]

    os.makedirs(MODEL_DIR, exist_ok=True)
    with open(TOP_MOVIES_PATH, 'w') as f:
        json.dump(data, f, indent=2)

    logger.info(f'Top movies saved ({len(data)} entries) → {TOP_MOVIES_PATH}')


# ── Entry point ────────────────────────────────────────────────────────────────

def main() -> None:
    download_movielens()

    spark = build_spark()
    try:
        ratings = load_ratings(spark)
        movies  = load_movies(spark)
        ratings.cache()

        logger.info(f'Total ratings after cleaning: {ratings.count():,}')

        train_df, test_df = ratings.randomSplit([0.8, 0.2], seed=42)
        train_df.cache()
        test_df.cache()

        model = train_als(train_df)
        evaluate_model(model, test_df)
        save_model(model)
        save_top_movies(ratings, movies)

    finally:
        spark.stop()
        logger.info('Spark stopped. All artefacts are ready.')
        logger.info('Start the backend: cd backend && uvicorn app.main:app --reload')


if __name__ == '__main__':
    main()
