"""
RecommendationService — business logic layer bridging routes and ALSModelManager.
"""

import logging
from typing import List, Optional

from fastapi import HTTPException

from app.cold_start.strategies import (
    ContentBasedGenre,
    ItemSimilarity,
    OnboardingFallback,
    PopularityFallback,
    STRATEGY_NAMES,
)
from app.model.als_model import ALSModelManager
from app.schemas.recommendation_schema import (
    ColdStartRequest,
    MovieListResponse,
    MovieRecommendation,
    RecommendationResponse,
    UserListResponse,
)

logger = logging.getLogger(__name__)


class RecommendationService:
    def __init__(self, model_manager: ALSModelManager) -> None:
        self._manager = model_manager

    # ── ALS recommendations (known users) ─────────────────────────────────────

    def get_recommendations_for_user(
        self, user_id: int, n: int = 10,
        fallback_strategy: str = "popularity",
    ) -> RecommendationResponse:
        if not self._manager.is_model_loaded():
            raise HTTPException(
                status_code=503,
                detail="Model not trained yet. Run train_and_save.py first.",
            )

        # ── Try ALS first ──────────────────────────────────────────────────────
        try:
            recs = self._manager.get_recommendations(user_id=user_id, n=n)
            return self._build_response(user_id, recs, cold_start=False)

        except ValueError:
            # Cold-start — user not in training data
            logger.info(
                "Cold-start detected for user %d — applying '%s' strategy",
                user_id, fallback_strategy,
            )
            return self._apply_cold_start(
                user_id=user_id, n=n,
                strategy_name=fallback_strategy,
            )

        except RuntimeError as exc:
            raise HTTPException(status_code=503, detail=str(exc))
        except Exception:
            logger.exception("Unexpected error for user %d", user_id)
            raise HTTPException(status_code=500, detail="Internal server error.")

    # ── Explicit cold-start endpoints ──────────────────────────────────────────

    def get_popular(self, n: int = 10) -> RecommendationResponse:
        """Strategy 1 — globally popular movies."""
        self._require_cold_start()
        recs = PopularityFallback(self._manager).recommend(n)
        return self._build_response(None, recs, cold_start=True,
                                    strategy="popularity")

    def get_by_genre(self, genres: List[str], n: int = 10) -> RecommendationResponse:
        """Strategy 2 — content-based genre filter."""
        self._require_cold_start()
        recs = ContentBasedGenre(self._manager).recommend(n, genres=genres)
        return self._build_response(None, recs, cold_start=True,
                                    strategy="content_based")

    def get_similar_to_movie(self, seed_movie_id: int, n: int = 10) -> RecommendationResponse:
        """Strategy 3 — item-item cosine similarity via ALS item factors."""
        self._require_cold_start()
        try:
            recs = ItemSimilarity(self._manager).recommend(
                n, seed_movie_id=seed_movie_id
            )
        except ValueError as exc:
            raise HTTPException(status_code=404, detail=str(exc))
        return self._build_response(None, recs, cold_start=True,
                                    strategy="item_similarity")

    def get_onboarding(self, seed_ratings: List[dict], n: int = 10) -> RecommendationResponse:
        """Strategy 4 — infer user vector from onboarding ratings."""
        self._require_cold_start()
        try:
            recs = OnboardingFallback(self._manager).recommend(
                n, seed_ratings=seed_ratings
            )
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc))
        return self._build_response(None, recs, cold_start=True,
                                    strategy="onboarding")

    # ── Helpers ────────────────────────────────────────────────────────────────

    def _apply_cold_start(
        self, user_id: int, n: int, strategy_name: str, **kwargs
    ) -> RecommendationResponse:
        self._require_cold_start()
        StrategyClass = STRATEGY_NAMES.get(strategy_name)
        if StrategyClass is None:
            raise HTTPException(status_code=400,
                                detail=f"Unknown strategy '{strategy_name}'. "
                                       f"Choose: {list(STRATEGY_NAMES)}")
        recs = StrategyClass(self._manager).recommend(n, **kwargs)
        return self._build_response(user_id, recs, cold_start=True,
                                    strategy=strategy_name)

    def _require_cold_start(self) -> None:
        if not self._manager.is_model_loaded():
            raise HTTPException(status_code=503,
                                detail="Model not loaded. Run train_and_save.py first.")
        if not self._manager.is_cold_start_ready():
            raise HTTPException(status_code=503,
                                detail="Cold-start data not ready. Restart after training.")

    def _build_response(
        self, user_id: Optional[int], recs: List[dict],
        cold_start: bool = False, strategy: Optional[str] = None,
    ) -> RecommendationResponse:
        return RecommendationResponse(
            user_id=user_id,
            recommendations=[
                MovieRecommendation(
                    movie_id=r["movie_id"],
                    title=r["title"],
                    genres=r["genres"],
                    predicted_rating=r["predicted_rating"],
                )
                for r in recs
            ],
            total=len(recs),
            cold_start=cold_start,
            cold_start_strategy=strategy,
        )

    # ── Catalogue ──────────────────────────────────────────────────────────────

    def get_users(self) -> UserListResponse:
        users = self._manager.get_all_users()
        return UserListResponse(users=users, total=len(users))

    def get_movies(self) -> MovieListResponse:
        movies = self._manager.get_all_movies()
        return MovieListResponse(movies=movies[:100], total=len(movies))
