"""
Pydantic schemas for recommendation API responses.
"""

from typing import List, Optional

from pydantic import BaseModel


class MovieRecommendation(BaseModel):
    movie_id: int
    title: str
    genres: str
    predicted_rating: float


class RecommendationResponse(BaseModel):
    user_id: Optional[int]
    recommendations: List[MovieRecommendation]
    total: int
    model_version: str = "ALS-v1"
    cold_start: bool = False                    # True when ALS had no data for this user
    cold_start_strategy: Optional[str] = None  # which strategy was used


class ColdStartRequest(BaseModel):
    """Body for cold-start endpoints that need extra context."""
    n: int = 10
    genres: Optional[List[str]] = None          # for content_based
    seed_movie_id: Optional[int] = None         # for item_similarity
    seed_ratings: Optional[List[dict]] = None   # for onboarding [{movie_id, rating}]


class HealthResponse(BaseModel):
    status: str
    version: str
    model_loaded: bool
    spark_active: bool
    cold_start_ready: bool = False


class UserListResponse(BaseModel):
    users: List[int]
    total: int


class MovieListResponse(BaseModel):
    movies: List[dict]
    total: int
