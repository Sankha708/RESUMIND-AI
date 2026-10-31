from fastapi import FastAPI
from fastapi.testclient import TestClient
from fastapi.middleware.cors import CORSMiddleware
import hashlib

from app.config import Settings
from app.middleware.security import (
    SecurityHeadersMiddleware,
    SecurityRateLimitMiddleware,
    SlidingWindowRateLimiter,
)


def make_client(**overrides):
    values = {
        "APP_ENV": "development",
        "DEBUG": False,
        "RATE_LIMIT_ENABLED": True,
        "RATE_LIMIT_API_PER_MINUTE": 100,
        "RATE_LIMIT_UPLOAD_COUNT": 1,
        "RATE_LIMIT_UPLOAD_WINDOW_SECONDS": 600,
        "RATE_LIMIT_AI_COUNT": 1,
        "RATE_LIMIT_AI_WINDOW_SECONDS": 300,
        "DATABASE_URL": "postgresql+asyncpg://user:placeholder@db.example.com/resumind",
        "CORS_ORIGINS": "https://app.example.com",
    }
    values.update(overrides)
    settings = Settings(**values)
    app = FastAPI()
    app.add_middleware(
        SecurityRateLimitMiddleware,
        settings=settings,
        rate_limiter=SlidingWindowRateLimiter(),
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
    app.add_api_route("/api/health", lambda: {"status": "healthy"})
    app.add_api_route("/api/{path:path}", lambda: {"ok": True}, methods=["GET", "POST"])
    return TestClient(app)


def test_upload_limit_returns_retry_after_and_security_headers():
    with make_client() as client:
        first = client.post("/api/resume/upload")
        second = client.post("/api/resume/upload")

    assert first.status_code == 200
    assert second.status_code == 429
    assert second.headers["retry-after"].isdigit()
    assert second.headers["x-ratelimit-limit"] == "1"
    assert second.headers["x-content-type-options"] == "nosniff"
    assert second.headers["x-frame-options"] == "DENY"
    assert second.headers["referrer-policy"] == "strict-origin-when-cross-origin"
    assert second.headers["permissions-policy"] == "camera=(), microphone=(), geolocation=()"


def test_ai_quota_is_scoped_by_hashed_session_cookie():
    client = make_client(RATE_LIMIT_AI_COUNT=1)
    token = "synthetic-session-token"
    client.cookies.set("resumind_session", token)
    try:
        first = client.post(
            "/api/improvement/generate",
            headers={"Origin": "https://app.example.com"},
        )
        second = client.post(
            "/api/improvement/generate",
            headers={
                "Origin": "https://app.example.com",
                "x-test-client": "different-client",
            },
        )
    finally:
        client.close()

    assert first.status_code == 200
    assert second.status_code == 429
    middleware = next(item for item in client.app.user_middleware if "rate_limiter" in item.kwargs)
    assert second.headers["x-ratelimit-policy"] == "ai"
    assert second.headers["retry-after"].isdigit()
    assert "retry-after" in second.headers["access-control-expose-headers"].lower()
    keys = middleware.kwargs["rate_limiter"]._windows
    assert ("ai", hashlib.sha256(token.encode()).hexdigest()) in keys
    assert all(token not in key for _, key in keys)


def test_health_is_exempt_and_hsts_requires_production_https():
    with make_client(
        APP_ENV="production",
        SESSION_COOKIE_SECURE=True,
        CORS_ORIGINS="https://app.example.com",
    ) as client:
        health = client.get("/api/health")
        regular = client.get("/api/resume")

    assert health.status_code == 200
    assert "strict-transport-security" in health.headers
    assert regular.status_code == 200


def test_options_preflight_does_not_consume_quota():
    with make_client(RATE_LIMIT_API_PER_MINUTE=1) as client:
        preflight = client.options(
            "/api/resume",
            headers={
                "Origin": "https://app.example.com",
                "Access-Control-Request-Method": "GET",
            },
        )
        request = client.get("/api/resume")

    assert preflight.status_code == 200
    assert preflight.headers["access-control-allow-origin"] == "https://app.example.com"
    assert preflight.headers["x-content-type-options"] == "nosniff"
    assert request.status_code == 200
