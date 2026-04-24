"""
FastAPI application factory.

Responsibilities:
- Configure structlog before anything else runs
- Open / close the database connection pool via lifespan
- Register exception handlers that translate domain errors to HTTP responses
- Mount the API router
- Wire up Prometheus metrics and CORS
"""
from __future__ import annotations

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.router import api_router
from app.config import AppEnv, get_settings
from app.core.exceptions import (
    FDISError,
)
from app.core.logging import configure_logging
from app.db.session import close_db, init_db

settings = get_settings()


# ── Lifespan ──────────────────────────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Manage startup and shutdown resources."""
    configure_logging(
        log_level=settings.log_level,
        log_format=settings.log_format.value,
    )
    logger = structlog.get_logger(__name__)
    logger.info("fdis_starting", env=settings.app_env.value)

    # Database
    init_db(
        database_url=settings.database_url,
        echo=settings.app_debug and settings.app_env == AppEnv.development,
    )
    logger.info("startup_complete")

    yield

    # Shutdown
    await close_db()
    logger.info("fdis_shutdown")


# ── App factory ───────────────────────────────────────────────────────────────

def create_app() -> FastAPI:
    app = FastAPI(
        title="Financial Document Intelligence System",
        description=(
            "Production-grade AI system for processing sensitive financial documents "
            "with full auditability, PII masking, and compliance-aware extraction."
        ),
        version="0.1.0",
        docs_url="/docs" if not settings.is_production else None,
        redoc_url="/redoc" if not settings.is_production else None,
        openapi_url="/openapi.json" if not settings.is_production else None,
        lifespan=lifespan,
    )

    # ── CORS ──────────────────────────────────────────────────────────────────
    origins = ["http://localhost:3000", "http://localhost:8080"]
    if settings.is_production:
        origins = []  # Configure per-deployment in production

    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE"],
        allow_headers=["Authorization", "Content-Type", "X-Request-ID"],
    )

    # ── Prometheus metrics ────────────────────────────────────────────────────
    if settings.enable_metrics:
        try:
            from prometheus_fastapi_instrumentator import Instrumentator
            Instrumentator(
                should_group_status_codes=True,
                should_ignore_untemplated=True,
                excluded_handlers=["/health/live", "/health/ready"],
            ).instrument(app).expose(app, endpoint="/metrics", include_in_schema=False)
        except ImportError:
            pass  # Optional in dev — metrics disabled if package not installed

    # ── Routers ───────────────────────────────────────────────────────────────
    app.include_router(api_router)

    # ── Exception handlers ────────────────────────────────────────────────────
    _register_exception_handlers(app)

    return app


def _register_exception_handlers(app: FastAPI) -> None:
    """Map domain exceptions to structured HTTP responses."""

    @app.exception_handler(FDISError)
    async def fdis_error_handler(request: Request, exc: FDISError) -> JSONResponse:
        logger = structlog.get_logger(__name__)
        logger.warning(
            "domain_error",
            error_type=type(exc).__name__,
            message=exc.message,
            path=str(request.url),
        )
        return JSONResponse(
            status_code=exc.status_code,
            content={"error": type(exc).__name__, "message": exc.message},
        )

    @app.exception_handler(Exception)
    async def unhandled_error_handler(request: Request, exc: Exception) -> JSONResponse:
        logger = structlog.get_logger(__name__)
        logger.exception("unhandled_error", path=str(request.url), exc_info=exc)
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"error": "InternalServerError", "message": "An unexpected error occurred"},
        )


app = create_app()
