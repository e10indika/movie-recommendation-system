"""
RecommendationService — business logic layer bridging routes and ALSModelManager.
"""

import logging

from fastapi import HTTPException

from app.model.als_model import ALSModelManager
from app.schemas.recommendation_schema import (
    MovieListResponse,
    MovieRecommendation,
    RecommendationResponse,
    UserListResponse,
)

logger = logging.getLogger(__name__)


class RecommendationService:
    def __init__(self, model_manager: ALSModelManager) -> None:
        self._manager = model_manager

    def get_recommendations_for_user(
        self, user_id: int, n: int = 10
    ) -> RecommendationResponse:
        if not self._manager.is_model_loaded():
            raise HTTPException(
                status_code=503,
                detail="Model not trained yet. Run train_and_save.py first.",
            )

        try:
            recs = self._manager.get_recommendations(user_id=user_id, n=n)
        except ValueError as exc:
            raise HTTPException(status_code=404, detail=str(exc))
        except RuntimeError as exc:
            raise HTTPException(status_code=503, detail=str(exc))
        except Exception:
            logger.exception("Unexpected error generating recommendations for user %d", user_id)
            raise HTTPException(status_code=500, detail="Internal server error.")

        recommendations = [
            MovieRecommendation(
                movie_id=r["movie_id"],
                title=r["title"],
                genres=r["genres"],
                predicted_rating=r["predicted_rating"],
            )
            for r in recs
        ]

        return RecommendationResponse(
            user_id=user_id,
            recommendations=recommendations,
            total=len(recommendations),
        )

    def get_users(self) -> UserListResponse:
        users = self._manager.get_all_users()
        return UserListResponse(users=users, total=len(users))

    def get_movies(self) -> MovieListResponse:
        movies = self._manager.get_all_movies()
        return MovieListResponse(movies=movies[:100], total=len(movies))
