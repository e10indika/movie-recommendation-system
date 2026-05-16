"""
ALSModelManager — Spark session + ALS model lifecycle manager.

Loads model from disk on initialisation. All recommendation inference
runs through this class. Designed to be instantiated once at startup
and stored on app.state.
"""

import logging
import os
from typing import Dict, List, Optional

# ── Java 17 required for PySpark 3.5 ──────────────────────────────────────
# PySpark 3.5 is compiled for Java 17 (class file version 61).
# Force JAVA_HOME to Java 17+ regardless of the shell environment.
_JAVA17 = "/opt/homebrew/Cellar/openjdk@17/17.0.17/libexec/openjdk.jdk/Contents/Home"
_JAVA21 = "/Library/Java/JavaVirtualMachines/temurin-21.jdk/Contents/Home"
for _jpath in (_JAVA17, _JAVA21):
    if os.path.isdir(_jpath):
        os.environ["JAVA_HOME"] = _jpath
        break

import numpy as np
import pandas as pd
from pyspark.ml.recommendation import ALSModel
from pyspark.sql import SparkSession
from pyspark.sql import functions as F
from pyspark.sql.types import IntegerType, StructField, StructType

from app.config import settings

logger = logging.getLogger(__name__)


class ALSModelManager:
    def __init__(self) -> None:
        self._spark: Optional[SparkSession] = None
        self._model: Optional[ALSModel] = None
        self._movies_df: Optional[pd.DataFrame] = None
        self._users: List[int] = []
        # Cold-start helpers — populated in load_movies_metadata()
        self._popularity_stats: Optional[pd.DataFrame] = None   # movieId, score, title, genres
        self._item_factors: Optional[pd.DataFrame] = None       # movieId + k factor cols

        self._spark = self._init_spark()
        self.load_model()
        if self._model is not None:
            self.load_movies_metadata()

    # ── Spark ─────────────────────────────────────────────────────────────────

    def _init_spark(self) -> SparkSession:
        logger.info("Initialising SparkSession …")
        spark = (
            SparkSession.builder
            .appName(settings.SPARK_APP_NAME)
            .master(settings.SPARK_MASTER)
            .config("spark.driver.memory", "2g")
            .config("spark.sql.shuffle.partitions", "8")
            .config("spark.ui.enabled", "false")
            .getOrCreate()
        )
        spark.sparkContext.setLogLevel("WARN")
        logger.info("SparkSession ready.")
        return spark

    # ── Model loading ─────────────────────────────────────────────────────────

    def load_model(self) -> None:
        model_path = os.path.abspath(
            os.path.join(os.path.dirname(__file__), "..", "..", settings.ALS_MODEL_PATH)
        )
        if not os.path.exists(model_path):
            logger.warning("ALS model not found at %s. Run train_and_save.py first.", model_path)
            return

        logger.info("Loading ALS model from %s …", model_path)
        self._model = ALSModel.load(model_path)
        logger.info("ALS model loaded successfully.")

    def load_movies_metadata(self) -> None:
        metadata_path = os.path.abspath(
            os.path.join(os.path.dirname(__file__), "..", "..", settings.MOVIES_METADATA_PATH)
        )
        if not os.path.exists(metadata_path):
            logger.warning("Movies metadata not found at %s.", metadata_path)
            return

        logger.info("Loading movies metadata from %s …", metadata_path)
        self._movies_df = pd.read_parquet(metadata_path)
        logger.info("Loaded %d movies.", len(self._movies_df))

        # Load sample users if available
        users_path = os.path.abspath(
            os.path.join(os.path.dirname(__file__), "..", "..", settings.SAMPLE_USERS_PATH)
        )
        if os.path.exists(users_path):
            users_df = pd.read_parquet(users_path)
            self._users = sorted(users_df["userId"].astype(int).tolist())
            logger.info("Loaded %d sample users.", len(self._users))

        # ── Cold-start: build popularity stats from ALS item factors ──────────
        self._build_cold_start_data()

    def _build_cold_start_data(self) -> None:
        """
        Precompute two artefacts used by cold-start strategies:

        1. popularity_stats — score = L2 norm of each item's factor vector
           (items with large norms are generally popular / high-signal).
           Merged with movie title/genre for direct use.

        2. item_factors — item factor matrix as a pandas DataFrame
           (movieId  +  k float columns f0…fk-1).
           Used by ItemSimilarity and OnboardingFallback.
        """
        if self._model is None or self._movies_df is None:
            return

        logger.info("Extracting ALS item factors for cold-start strategies …")
        try:
            # itemFactors is a Spark DataFrame: id (movieId), features (array<float>)
            item_factors_spark = self._model.itemFactors
            item_factors_pd    = item_factors_spark.toPandas()

            # Expand the features array into individual columns f0, f1, …
            feat_matrix = pd.DataFrame(
                item_factors_pd["features"].tolist(),
                columns=[f"f{i}" for i in range(len(item_factors_pd["features"].iloc[0]))],
            )
            feat_matrix["movieId"] = item_factors_pd["id"].values
            self._item_factors = feat_matrix[["movieId"] +
                                              [c for c in feat_matrix.columns if c != "movieId"]]

            # Popularity score = L2 norm of the factor vector
            feat_cols  = [c for c in feat_matrix.columns if c != "movieId"]
            norms      = np.linalg.norm(feat_matrix[feat_cols].values, axis=1)
            norm_df    = pd.DataFrame({"movieId": feat_matrix["movieId"].values, "score": norms})

            # Normalise to [0, 5] so scores feel like ratings
            max_score  = norm_df["score"].max()
            if max_score > 0:
                norm_df["score"] = norm_df["score"] / max_score * 5.0

            # Merge with movie metadata
            self._popularity_stats = norm_df.merge(
                self._movies_df[["movieId", "title", "genres"]], on="movieId", how="inner"
            )
            logger.info("Cold-start data ready — %d item factor vectors.", len(self._item_factors))

        except Exception:
            logger.exception("Failed to build cold-start data — strategies will be unavailable.")
            self._item_factors     = None
            self._popularity_stats = None

    # ── Inference ─────────────────────────────────────────────────────────────

    def get_recommendations(self, user_id: int, n: int = 10) -> List[dict]:
        if self._model is None:
            raise RuntimeError("Model not loaded. Run train_and_save.py first.")
        if self._movies_df is None:
            raise RuntimeError("Movies metadata not loaded.")

        user_schema = StructType([StructField("userId", IntegerType(), False)])
        user_df = self._spark.createDataFrame([(user_id,)], schema=user_schema)

        recs_rows = self._model.recommendForUserSubset(user_df, numItems=n).collect()
        if not recs_rows:
            raise ValueError(f"User {user_id} not found in training data (cold-start).")

        raw_recs = recs_rows[0]["recommendations"]

        results = []
        for rec in raw_recs:
            movie_id = int(rec["movieId"])
            match = self._movies_df[self._movies_df["movieId"] == movie_id]
            title = match["title"].iloc[0] if not match.empty else "Unknown"
            genres = match["genres"].iloc[0] if not match.empty else "Unknown"
            results.append({
                "movie_id": movie_id,
                "title": str(title),
                "genres": str(genres),
                "predicted_rating": round(float(rec["rating"]), 4),
            })

        return sorted(results, key=lambda r: r["predicted_rating"], reverse=True)

    # ── Accessors ─────────────────────────────────────────────────────────────

    def get_all_users(self) -> List[int]:
        return self._users

    def get_all_movies(self) -> List[dict]:
        if self._movies_df is None:
            return []
        return self._movies_df[["movieId", "title", "genres"]].to_dict(orient="records")

    def get_movies_df(self) -> Optional[pd.DataFrame]:
        return self._movies_df

    def get_popularity_stats(self) -> Optional[pd.DataFrame]:
        return self._popularity_stats

    def get_item_factors(self) -> Optional[pd.DataFrame]:
        return self._item_factors

    def is_model_loaded(self) -> bool:
        return self._model is not None

    def is_spark_active(self) -> bool:
        return self._spark is not None and self._spark.sparkContext._jsc is not None

    def is_cold_start_ready(self) -> bool:
        return self._item_factors is not None and self._popularity_stats is not None
