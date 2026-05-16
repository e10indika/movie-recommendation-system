"""
FastAPI router for the recommendation API — prefix /api/v1.
"""

import logging
from typing import List, Optional

from fastapi import APIRouter, Body, Query, Request

from app.schemas.recommendation_schema import (
    ColdStartRequest,
    HealthResponse,
    MovieListResponse,
    RecommendationResponse,
    UserListResponse,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1", tags=["recommendations"])


def _service(request: Request):
    return request.app.state.recommendation_service


# ── Health ────────────────────────────────────────────────────────────────────

@router.get("/health", response_model=HealthResponse, tags=["Health"])
def health(request: Request) -> HealthResponse:
    manager = _service(request)._manager
    return HealthResponse(
        status="ok" if manager.is_model_loaded() else "degraded",
        version=request.app.version,
        model_loaded=manager.is_model_loaded(),
        spark_active=manager.is_spark_active(),
        cold_start_ready=manager.is_cold_start_ready(),
    )


# ── Catalogue ─────────────────────────────────────────────────────────────────

@router.get("/users", response_model=UserListResponse)
def list_users(request: Request) -> UserListResponse:
    return _service(request).get_users()


@router.get("/movies", response_model=MovieListResponse)
def list_movies(request: Request) -> MovieListResponse:
    return _service(request).get_movies()


# ── ALS recommendations (auto cold-start fallback) ────────────────────────────

@router.get("/recommend/{user_id}", response_model=RecommendationResponse)
def recommend(
    user_id: int,
    request: Request,
    n: int = Query(default=10, ge=1, le=50, description="Number of recommendations"),
    strategy: str = Query(
        default="popularity",
        description="Cold-start fallback strategy if user unknown: "
                    "popularity | content_based | item_similarity | onboarding",
    ),
) -> RecommendationResponse:
    return _service(request).get_recommendations_for_user(
        user_id=user_id, n=n, fallback_strategy=strategy
    )


# ── Explicit cold-start endpoints ─────────────────────────────────────────────

@router.get("/cold-start/popular", response_model=RecommendationResponse,
            summary="Strategy 1 — Globally popular movies")
def cold_start_popular(
    request: Request,
    n: int = Query(default=10, ge=1, le=50),
) -> RecommendationResponse:
    return _service(request).get_popular(n=n)


@router.get("/cold-start/by-genre", response_model=RecommendationResponse,
            summary="Strategy 2 — Content-based genre filter")
def cold_start_genre(
    request: Request,
    genres: List[str] = Query(default=[], description="e.g. Action&genres=Comedy"),
    n: int = Query(default=10, ge=1, le=50),
) -> RecommendationResponse:
    return _service(request).get_by_genre(genres=genres, n=n)


@router.get("/cold-start/similar-to/{movie_id}", response_model=RecommendationResponse,
            summary="Strategy 3 — Item-item similarity via ALS item factors")
def cold_start_similar(
    movie_id: int,
    request: Request,
    n: int = Query(default=10, ge=1, le=50),
) -> RecommendationResponse:
    return _service(request).get_similar_to_movie(seed_movie_id=movie_id, n=n)


@router.post("/cold-start/onboarding", response_model=RecommendationResponse,
             summary="Strategy 4 — Onboarding: rate a few movies, get personalised recommendations")
def cold_start_onboarding(
    request: Request,
    body: ColdStartRequest = Body(...),
) -> RecommendationResponse:
    return _service(request).get_onboarding(
        seed_ratings=body.seed_ratings or [],
        n=body.n,
    )
