"""
cold_start/strategies.py

Four cold-start strategies for users absent from ALS training data.

Strategy 1 — Popularity Fallback
    Return globally most-rated movies. Works with zero user info.

Strategy 2 — Content-Based (Genre Filter)
    User supplies preferred genres → top-rated movies in those genres.

Strategy 3 — Item-Item Similarity
    Given a seed movie_id the user likes → find similar movies via
    cosine similarity on ALS item factor vectors.

Strategy 4 — Onboarding (Mini Rating Collection)
    User rates ≥3 seed movies in-session; those ratings are injected
    as temporary facts and used directly for ALS re-rank.
    (Stateless approximation: weighted average of item factors.)
"""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, List, Optional

import numpy as np
import pandas as pd

if TYPE_CHECKING:
    from app.model.als_model import ALSModelManager

logger = logging.getLogger(__name__)


# ── Base ──────────────────────────────────────────────────────────────────────

class ColdStartStrategy(ABC):
    """All strategies return a list of recommendation dicts."""

    name: str = "base"

    @abstractmethod
    def recommend(self, n: int, **kwargs) -> List[dict]:
        ...

    def _format(self, movies_df: pd.DataFrame, scores: pd.Series,
                n: int) -> List[dict]:
        """Join scores onto movies_df and return top-n dicts."""
        result = movies_df.copy()
        result["predicted_rating"] = result["movieId"].map(scores).fillna(0.0)
        result = result[result["predicted_rating"] > 0].nlargest(n, "predicted_rating")
        return [
            {
                "movie_id":        int(row["movieId"]),
                "title":           str(row["title"]),
                "genres":          str(row["genres"]),
                "predicted_rating": round(float(row["predicted_rating"]), 4),
            }
            for _, row in result.iterrows()
        ]


# ── Strategy 1 — Popularity Fallback ─────────────────────────────────────────

class PopularityFallback(ColdStartStrategy):
    """
    Recommend the globally most-rated movies weighted by their mean rating.
    Score = (num_ratings / max_ratings) * mean_rating
    No user input needed — pure item statistics.
    """

    name = "popularity"

    def __init__(self, manager: "ALSModelManager") -> None:
        self._movies  = manager.get_movies_df()
        self._popular = manager.get_popularity_stats()   # precomputed

    def recommend(self, n: int, **kwargs) -> List[dict]:
        top = self._popular.nlargest(n, "score")
        return [
            {
                "movie_id":         int(row["movieId"]),
                "title":            str(row["title"]),
                "genres":           str(row["genres"]),
                "predicted_rating": round(float(row["score"]), 4),
            }
            for _, row in top.iterrows()
        ]


# ── Strategy 2 — Content-Based Genre Filter ───────────────────────────────────

class ContentBasedGenre(ColdStartStrategy):
    """
    Filter movies by user-supplied genre preferences, rank by mean rating.

    kwargs:
        genres: List[str]  e.g. ["Action", "Comedy"]
    """

    name = "content_based"

    def __init__(self, manager: "ALSModelManager") -> None:
        self._movies  = manager.get_movies_df()
        self._popular = manager.get_popularity_stats()

    def recommend(self, n: int, genres: Optional[List[str]] = None, **kwargs) -> List[dict]:
        if not genres:
            logger.warning("content_based called with no genres — falling back to popularity")
            top = self._popular.nlargest(n, "score")
            return [
                {
                    "movie_id":         int(row["movieId"]),
                    "title":            str(row["title"]),
                    "genres":           str(row["genres"]),
                    "predicted_rating": round(float(row["score"]), 4),
                }
                for _, row in top.iterrows()
            ]

        mask = self._movies["genres"].str.contains(
            "|".join(genres), case=False, na=False
        )
        filtered = self._movies[mask].copy()
        if filtered.empty:
            logger.warning("No movies found for genres %s — falling back to all", genres)
            filtered = self._movies.copy()

        # Attach popularity score for ranking
        merged = filtered.merge(
            self._popular[["movieId", "score"]], on="movieId", how="left"
        ).fillna({"score": 0.0})
        top = merged.nlargest(n, "score")
        return [
            {
                "movie_id":         int(row["movieId"]),
                "title":            str(row["title"]),
                "genres":           str(row["genres"]),
                "predicted_rating": round(float(row["score"]), 4),
            }
            for _, row in top.iterrows()
        ]


# ── Strategy 3 — Item-Item Similarity via ALS Item Factors ───────────────────

class ItemSimilarity(ColdStartStrategy):
    """
    Given a seed movie_id, find the N most similar movies using cosine
    similarity on the ALS item (product) factor vectors.

    This works for any user — even completely new — as long as they can
    name one movie they like.

    kwargs:
        seed_movie_id: int
    """

    name = "item_similarity"

    def __init__(self, manager: "ALSModelManager") -> None:
        self._movies      = manager.get_movies_df()
        self._item_factors = manager.get_item_factors()  # pd.DataFrame: movieId + factor cols

    def recommend(self, n: int, seed_movie_id: Optional[int] = None, **kwargs) -> List[dict]:
        if seed_movie_id is None:
            raise ValueError("item_similarity strategy requires seed_movie_id")

        factors = self._item_factors
        seed_row = factors[factors["movieId"] == seed_movie_id]
        if seed_row.empty:
            raise ValueError(f"seed_movie_id {seed_movie_id} not found in item factors")

        # Extract numpy vectors
        feat_cols = [c for c in factors.columns if c != "movieId"]
        seed_vec  = seed_row[feat_cols].values[0]               # (k,)
        all_vecs  = factors[feat_cols].values                   # (m, k)

        # Cosine similarity: dot(seed, all) / (||seed|| * ||all||)
        seed_norm = np.linalg.norm(seed_vec)
        all_norms = np.linalg.norm(all_vecs, axis=1)
        denom     = seed_norm * all_norms
        denom     = np.where(denom == 0, 1e-9, denom)           # avoid div/0
        sims      = all_vecs.dot(seed_vec) / denom              # (m,)

        sim_df = pd.DataFrame({
            "movieId": factors["movieId"].values,
            "similarity": sims,
        })
        # Exclude the seed movie itself
        sim_df = sim_df[sim_df["movieId"] != seed_movie_id]
        top    = sim_df.nlargest(n, "similarity")

        result = top.merge(self._movies, on="movieId", how="left")
        return [
            {
                "movie_id":         int(row["movieId"]),
                "title":            str(row.get("title", "Unknown")),
                "genres":           str(row.get("genres", "Unknown")),
                "predicted_rating": round(float(row["similarity"]), 4),
            }
            for _, row in result.iterrows()
        ]


# ── Strategy 4 — Onboarding (Weighted Factor Averaging) ──────────────────────

class OnboardingFallback(ColdStartStrategy):
    """
    User rates a small set of seed movies (3–10) during onboarding.
    We approximate a user factor vector as the rating-weighted average
    of the seed movies' item factor vectors, then rank all other movies
    by dot-product score.

    This is a stateless, cheap approximation of ALS user-factor inference.
    No retraining required.

    kwargs:
        seed_ratings: List[dict]  e.g. [{"movie_id": 1, "rating": 4.5}, ...]
    """

    name = "onboarding"

    def __init__(self, manager: "ALSModelManager") -> None:
        self._movies       = manager.get_movies_df()
        self._item_factors = manager.get_item_factors()

    def recommend(
        self, n: int,
        seed_ratings: Optional[List[dict]] = None,
        **kwargs,
    ) -> List[dict]:
        if not seed_ratings:
            raise ValueError("onboarding strategy requires seed_ratings list")

        factors   = self._item_factors
        feat_cols = [c for c in factors.columns if c != "movieId"]
        rated_ids = {r["movie_id"] for r in seed_ratings}

        # Build weighted sum of item factors
        user_vec = np.zeros(len(feat_cols))
        total_w  = 0.0
        for entry in seed_ratings:
            mid   = entry["movie_id"]
            w     = float(entry.get("rating", 3.5))
            row   = factors[factors["movieId"] == mid]
            if row.empty:
                logger.warning("seed movie_id %d not in item factors — skipped", mid)
                continue
            user_vec += w * row[feat_cols].values[0]
            total_w  += w

        if total_w == 0:
            raise ValueError("None of the seed_ratings movie_ids were found in the model")

        user_vec /= total_w   # normalise by total weight

        # Score all items: dot product with inferred user vector
        all_vecs = factors[feat_cols].values
        scores   = all_vecs.dot(user_vec)

        score_df = pd.DataFrame({
            "movieId": factors["movieId"].values,
            "predicted_rating": scores,
        })
        # Exclude seed movies already rated
        score_df = score_df[~score_df["movieId"].isin(rated_ids)]
        top      = score_df.nlargest(n, "predicted_rating")

        result   = top.merge(self._movies, on="movieId", how="left")
        return [
            {
                "movie_id":         int(row["movieId"]),
                "title":            str(row.get("title", "Unknown")),
                "genres":           str(row.get("genres", "Unknown")),
                "predicted_rating": round(float(row["predicted_rating"]), 4),
            }
            for _, row in result.iterrows()
        ]


# ── Registry ──────────────────────────────────────────────────────────────────

STRATEGY_NAMES = {
    "popularity":      PopularityFallback,
    "content_based":   ContentBasedGenre,
    "item_similarity": ItemSimilarity,
    "onboarding":      OnboardingFallback,
}
