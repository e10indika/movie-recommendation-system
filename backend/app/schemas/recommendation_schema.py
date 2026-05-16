"""
Pydantic schemas for recommendation API responses.
"""

from typing import List

from pydantic import BaseModel


class MovieRecommendation(BaseModel):
    movie_id: int
    title: str
    genres: str
    predicted_rating: float


class RecommendationResponse(BaseModel):
    user_id: int
    recommendations: List[MovieRecommendation]
    total: int
    model_version: str = "ALS-v1"


class HealthResponse(BaseModel):
    status: str
    version: str
    model_loaded: bool
    spark_active: bool


class UserListResponse(BaseModel):
    users: List[int]
    total: int


class MovieListResponse(BaseModel):
    movies: List[dict]
    total: int
