"""RESUMIND AI — FastAPI Main Entrypoint.

Provides core application initialization, CORS configuration,
health monitoring, anonymous session lifecycle, and resume document parsing endpoints.
"""

import asyncio
import logging
from contextlib import asynccontextmanager, suppress
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.config import settings
from app.middleware.security import SecurityHeadersMiddleware, SecurityRateLimitMiddleware
from app.database import engine, Base, async_session_factory
import app.models  # Ensures all ORM models are registered
from app.routers.session import router as session_router
from app.routers.resume import router as resume_router
from app.routers.assessment import router as assessment_router
from app.routers.job_match import router as job_match_router
from app.routers.improvement import router as improvement_router
from app.routers.builder import router as builder_router
from app.routers.export import router as export_router
from app.routers.reanalysis import router as reanalysis_router
from app.services.session_service import cleanup_expired_sessions

logger = logging.getLogger(__name__)


async def _expired_session_cleanup_loop() -> None:
    """Periodically remove expired anonymous-session records and isolated files.

    The initial sleep avoids racing app startup/migrations. Cleanup is idempotent;
    failures are logged and retried at the next interval.
    """
    interval = max(60, int(settings.SESSION_CLEANUP_INTERVAL_SECONDS))
    while True:
        await asyncio.sleep(interval)
        try:
            async with async_session_factory() as db:
                purged = await cleanup_expired_sessions(db)
                await db.commit()
            if purged:
                logger.info("Expired anonymous sessions cleaned up: %s", purged)
        except asyncio.CancelledError:
            raise
        except Exception:
            logger.exception("Scheduled expired-session cleanup failed")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize database and schedule expired anonymous-session cleanup."""
    if settings.APP_ENV.casefold() != "production":
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

    cleanup_task = asyncio.create_task(_expired_session_cleanup_loop())
    try:
        yield
    finally:
        cleanup_task.cancel()
        with suppress(asyncio.CancelledError):
            await cleanup_task


app = FastAPI(
    title=settings.APP_NAME,
    version="0.1.0",
    description="Privacy-First, No-Login AI Resume Optimization & ATS Intelligence Engine API",
    docs_url="/api/docs",
    openapi_url="/api/openapi.json",
    lifespan=lifespan,
)

# Middleware is added inside-out: CORS wraps rate-limit responses so browsers
# receive CORS headers even when a request is rejected with 429.
app.add_middleware(
    SecurityRateLimitMiddleware,
    settings=settings,
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["Retry-After", "X-RateLimit-Policy"],
)
app.add_middleware(SecurityHeadersMiddleware, settings=settings)

# Include API Routers
app.include_router(session_router)
app.include_router(resume_router)
app.include_router(assessment_router)
app.include_router(job_match_router)
app.include_router(improvement_router)
app.include_router(builder_router)
app.include_router(export_router)
app.include_router(reanalysis_router)


@app.get("/api/health", tags=["Health"])
async def health_check():
    """Health check endpoint to verify backend operational readiness."""
    return {
        "status": "healthy",
        "service": "resumind-api",
        "version": "0.1.0",
        "environment": settings.APP_ENV,
    }
