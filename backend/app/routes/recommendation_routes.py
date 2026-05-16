"""
FastAPI router for the recommendation API — prefix /api/v1.
"""

import logging

from fastapi import APIRouter, Query, Request

from app.schemas.recommendation_schema import (
    HealthResponse,
    MovieListResponse,
    RecommendationResponse,
    UserListResponse,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1", tags=["recommendations"])


def _service(request: Request):
    return request.app.state.recommendation_service


@router.get("/health", response_model=HealthResponse, tags=["Health"])
def health(request: Request) -> HealthResponse:
    manager = _service(request)._manager
    return HealthResponse(
        status="ok" if manager.is_model_loaded() else "degraded",
        version=request.app.version,
        model_loaded=manager.is_model_loaded(),
        spark_active=manager.is_spark_active(),
    )


@router.get("/users", response_model=UserListResponse)
def list_users(request: Request) -> UserListResponse:
    return _service(request).get_users()


@router.get("/movies", response_model=MovieListResponse)
def list_movies(request: Request) -> MovieListResponse:
    return _service(request).get_movies()


@router.get("/recommend/{user_id}", response_model=RecommendationResponse)
def recommend(
    user_id: int,
    request: Request,
    n: int = Query(default=10, ge=1, le=50, description="Number of recommendations"),
) -> RecommendationResponse:
    return _service(request).get_recommendations_for_user(user_id=user_id, n=n)
