"""
Pydantic response models — define the exact JSON shape returned by every endpoint.
Keeping schemas in a dedicated module decouples serialisation from business logic.
"""

from typing import List

from pydantic import BaseModel, Field


class HealthResponse(BaseModel):
    status: str  = Field(..., example='ok')
    message: str = Field(..., example='Movie Recommendation API is running.')


# ── /recommend/{user_id} ──────────────────────────────────────────────────────

class MovieRecommendation(BaseModel):
    movieId:          int   = Field(..., example=318)
    title:            str   = Field(..., example='Shawshank Redemption, The (1994)')
    genres:           str   = Field(..., example='Crime|Drama')
    predicted_rating: float = Field(..., example=4.87)


class RecommendationResponse(BaseModel):
    userId:          int                      = Field(..., example=1)
    recommendations: List[MovieRecommendation]


# ── /top-movies ───────────────────────────────────────────────────────────────

class TopMovie(BaseModel):
    movieId:     int   = Field(..., example=356)
    title:       str   = Field(..., example='Forrest Gump (1994)')
    genres:      str   = Field(..., example='Comedy|Drama|Romance|War')
    num_ratings: int   = Field(..., example=329)
    avg_rating:  float = Field(..., example=4.01)


class TopMoviesResponse(BaseModel):
    movies: List[TopMovie]
