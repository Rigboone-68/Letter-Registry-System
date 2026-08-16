"""Application entry point.

Creates and configures the FastAPI application: the application factory,
logging setup, CORS policy, the versioned API router, and a liveness probe
used by operations to confirm the service is up.

Run locally:
    uvicorn app.main:app --reload
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1.router import api_router
from app.core.config import settings
from app.core.logging import configure_logging, get_logger

logger = get_logger(__name__)


def create_application() -> FastAPI:
    """Build the FastAPI application instance."""
    configure_logging()

    application = FastAPI(
        title=settings.APP_NAME,
        description="Internal registry for incoming official letters. "
                    "A Production of AJ-Labs.",
        version="0.1.0",
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url=f"{settings.API_V1_PREFIX}/openapi.json",
    )

    if settings.CORS_ORIGINS:
        application.add_middleware(
            CORSMiddleware,
            allow_origins=settings.CORS_ORIGINS,
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )

    application.include_router(api_router, prefix=settings.API_V1_PREFIX)

    @application.get("/health", tags=["system"])
    def health() -> dict:
        """Liveness probe. Reports process health only, not database status."""
        return {
            "status": "ok",
            "application": settings.APP_NAME,
            "environment": settings.APP_ENV,
            "version": application.version,
        }

    logger.info("%s initialized in %s mode", settings.APP_NAME, settings.APP_ENV)
    return application


app = create_application()
