"""
FastAPI application entry point for the Movie Recommendation System.

Run from the backend/ directory:
    uvicorn app.main:app --reload --host 0.0.0.0 --port 8003
"""

import logging
import sys
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.model.als_model import ALSModelManager
from app.routes.recommendation_routes import router
from app.services.recommendation_service import RecommendationService

# ── Logging setup ─────────────────────────────────────────────────────────────

logging.basicConfig(
    level=getattr(logging, settings.LOG_LEVEL, logging.INFO),
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    stream=sys.stdout,
)
logger = logging.getLogger(__name__)


# ── Lifespan ──────────────────────────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting %s v%s", settings.APP_NAME, settings.APP_VERSION)
    logger.info("Host: %s  Port: %d", settings.HOST, settings.PORT)
    logger.info("ALS model path: %s", settings.ALS_MODEL_PATH)

    model_manager = ALSModelManager()
    app.state.recommendation_service = RecommendationService(model_manager)

    if model_manager.is_model_loaded():
        logger.info("Model loaded — API ready.")
    else:
        logger.warning("Model NOT loaded. Train with: python3 train_and_save.py")

    yield

    logger.info("Application shutting down.")


# ── App factory ───────────────────────────────────────────────────────────────

app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="ALS collaborative filtering powered by Apache Spark MLlib.",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_methods=["GET"],
    allow_headers=["*"],
)

app.include_router(router)
