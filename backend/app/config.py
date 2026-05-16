"""
Application configuration using pydantic-settings.
Values can be overridden via environment variables or a .env file.
"""

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    APP_NAME: str = "Movie Recommendation System"
    APP_VERSION: str = "1.0.0"
    HOST: str = "0.0.0.0"
    PORT: int = 8003

    CORS_ORIGINS: list = ["http://localhost:5173", "http://localhost:5174", "http://localhost:3000"]

    DATA_DIR: str = "../data"
    MODELS_DIR: str = "../models"
    ALS_MODEL_PATH: str = "../models/als_model"
    MOVIES_METADATA_PATH: str = "../models/movies_metadata.parquet"
    SAMPLE_USERS_PATH: str = "../models/sample_users.parquet"

    SPARK_APP_NAME: str = "MovieRecommendationAPI"
    SPARK_MASTER: str = "local[*]"

    ALS_MAX_ITER: int = 10
    ALS_REG_PARAM: float = 0.1
    ALS_RANK: int = 10
    TOP_N_RECOMMENDATIONS: int = 10

    LOG_LEVEL: str = "INFO"

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()
