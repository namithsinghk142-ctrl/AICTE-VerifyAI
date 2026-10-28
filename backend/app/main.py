"""FastAPI application factory."""

from __future__ import annotations

import os
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.config import get_settings
from app.database import Base, SessionLocal, engine, ensure_schema_compatibility
from app.routes import (
    applications,
    audit,
    auth,
    compliance,
    dashboard,
    documents,
    evaluation,
    health,
    reference_data,
    reviewer,
)
from app.services.auth import seed_reviewer_accounts
from app.services.dataset_importer import import_verified_dataset


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Application lifespan — runs on startup and shutdown."""
    settings = get_settings()
    # Ensure private storage directory exists
    os.makedirs(settings.storage_dir, exist_ok=True)

    # Startup: create tables and synchronize schema
    import app.models as _models  # noqa: F841
    Base.metadata.create_all(bind=engine)
    ensure_schema_compatibility(engine)

    # Ensure baseline and demo reviewer accounts are safely seeded without overwriting
    with SessionLocal() as db_session:
        seed_reviewer_accounts(db_session)
        from app.services.synthetic_seeder import seed_synthetic_applications_if_empty
        seed_synthetic_applications_if_empty(db_session)
        from app.models import PublicReferenceInstitution
        if db_session.query(PublicReferenceInstitution).count() == 0:
            import_verified_dataset(db_session, dry_run=False)

    yield
    # Shutdown: cleanup if needed


def create_app() -> FastAPI:
    """Build and return the configured FastAPI application instance."""
    settings = get_settings()

    app = FastAPI(
        title=settings.app_title,
        version=settings.app_version,
        description=(
            "AI-Powered Application Validation, Document Authentication "
            "and Regulatory Compliance Verification for AICTE."
        ),
        lifespan=lifespan,
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
    )

    # ------------------------------------------------------------------
    # CORS
    # ------------------------------------------------------------------
    allowed_origins = list(settings.cors_origin_list)
    for dev_origin in (
        "http://localhost:5173",
        "http://localhost:5174",
        "http://127.0.0.1:5173",
        "http://127.0.0.1:5174",
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ):
        if dev_origin not in allowed_origins:
            allowed_origins.append(dev_origin)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=allowed_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # ------------------------------------------------------------------
    # Global exception handler — never leak stack traces to clients
    # ------------------------------------------------------------------
    @app.exception_handler(Exception)
    async def _unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
        return JSONResponse(
            status_code=500,
            content={"detail": "An internal server error occurred."},
        )

    # ------------------------------------------------------------------
    # Routers — health checks and domain APIs
    # ------------------------------------------------------------------
    app.include_router(health.router)  # /health
    app.include_router(health.router, prefix="/api/v1")  # /api/v1/health
    app.include_router(health.router, prefix="/api")  # /api/health

    # Mount domain routes under both /api and /api/v1 for unified client support
    for pfx in ("/api", "/api/v1"):
        app.include_router(applications.router, prefix=pfx)
        app.include_router(applications.submissions_router, prefix=pfx)
        app.include_router(documents.router, prefix=pfx)
        app.include_router(dashboard.router, prefix=pfx)
        app.include_router(compliance.router, prefix=pfx)
        app.include_router(audit.router, prefix=pfx)
        app.include_router(reviewer.router, prefix=pfx)
        app.include_router(reference_data.router, prefix=pfx)
        app.include_router(evaluation.router, prefix=pfx)

    # ------------------------------------------------------------------
    # Authentication routes — exposed under /api/v1/auth and /api/auth
    # ------------------------------------------------------------------
    app.include_router(auth.router, prefix="/api/v1/auth")
    app.include_router(auth.router, prefix="/api/auth")

    return app


app = create_app()
