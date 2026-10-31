"""Automated test suite for anonymous sessions, database persistence,
isolated ephemeral storage, lifecycle expiry, and CORS boundary controls.
"""

import hashlib
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path
import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from app.config import settings
from app.database import Base, get_db
from app.main import app
from app.models.session import AnonymousSession
from app.services.session_service import (
    cleanup_expired_sessions,
    create_session,
    hash_session_token,
)
from app.services.storage_service import (
    StorageSecurityError,
    ensure_session_storage,
    get_session_storage_dirs,
    validate_session_id,
)

# Test Database Configuration (Isolated SQLite file in temp dir)
@pytest.fixture
async def test_env(tmp_path: Path):
    """Provisions an isolated SQLite test database and temporary storage root."""
    test_db_path = tmp_path / "test_resumind.db"
    test_storage_root = tmp_path / "storage"
    test_storage_root.mkdir(parents=True, exist_ok=True)

    db_url = f"sqlite+aiosqlite:///{test_db_path}"
    engine = create_async_engine(db_url, connect_args={"check_same_thread": False})
    session_factory = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    # Override app settings storage root
    original_storage_root = settings.STORAGE_ROOT
    settings.STORAGE_ROOT = str(test_storage_root)

    async def override_get_db():
        async with session_factory() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise
            finally:
                await session.close()

    app.dependency_overrides[get_db] = override_get_db

    yield {
        "engine": engine,
        "session_factory": session_factory,
        "storage_root": test_storage_root,
    }

    app.dependency_overrides.clear()
    settings.STORAGE_ROOT = original_storage_root
    await engine.dispose()


@pytest.fixture
async def client():
    """Async HTTP test client bound to FastAPI application."""
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        yield ac


@pytest.mark.asyncio
async def test_new_session_creation_and_cookie_attributes(test_env, client):
    """Verify new anonymous session creation, isolated storage folders, and cookie flags."""
    response = await client.post("/api/session")
    assert response.status_code == 200

    data = response.json()
    assert "id" in data
    assert data["is_active"] is True
    assert "token" not in data
    assert "token_hash" not in data
    assert "storage" not in data

    # Verify Set-Cookie header attributes
    cookie_header = response.headers.get("set-cookie")
    assert cookie_header is not None
    assert f"{settings.SESSION_COOKIE_NAME}=" in cookie_header
    assert "httponly" in cookie_header.lower()
    assert f"samesite={settings.SESSION_COOKIE_SAMESITE.lower()}" in cookie_header.lower()
    assert f"path={settings.SESSION_COOKIE_PATH}" in cookie_header.lower()

    # Verify isolated ephemeral directories were provisioned
    session_id = data["id"]
    dirs = get_session_storage_dirs(session_id, base_root=test_env["storage_root"])
    for category_path in dirs.values():
        assert category_path.exists()
        assert category_path.is_dir()


@pytest.mark.asyncio
async def test_only_token_hash_stored_in_database(test_env, client):
    """Verify that only the SHA-256 hash is persisted in the database, never the raw token."""
    response = await client.post("/api/session")
    raw_token = response.cookies.get(settings.SESSION_COOKIE_NAME)
    assert raw_token is not None
    assert len(raw_token) >= 32

    expected_hash = hashlib.sha256(raw_token.encode("utf-8")).hexdigest()

    async with test_env["session_factory"]() as db:
        session_id = response.json()["id"]
        db_session = await db.get(AnonymousSession, session_id)
        assert db_session is not None
        assert db_session.token_hash == expected_hash
        # Raw token string must not be stored anywhere in the database record
        assert raw_token != db_session.token_hash
        assert not hasattr(db_session, "token")


@pytest.mark.asyncio
async def test_valid_cookie_reuses_session_and_updates_last_seen(test_env, client):
    """Verify that submitting a valid session cookie reuses the session and refreshes last_seen_at."""
    res1 = await client.post("/api/session")
    session_id = res1.json()["id"]
    cookie_val = res1.cookies.get(settings.SESSION_COOKIE_NAME)

    async with test_env["session_factory"]() as db:
        initial_db = await db.get(AnonymousSession, session_id)
        first_last_seen = initial_db.last_seen_at

    # Subsequent request using the cookie
    client.cookies.set(settings.SESSION_COOKIE_NAME, cookie_val)
    res2 = await client.get("/api/session")
    assert res2.status_code == 200
    assert res2.json()["id"] == session_id

    async with test_env["session_factory"]() as db:
        refreshed_db = await db.get(AnonymousSession, session_id)
        assert refreshed_db.last_seen_at >= first_last_seen


@pytest.mark.asyncio
async def test_missing_invalid_and_expired_cookies(test_env, client):
    """Verify 401 Unauthorized for missing, forged, or expired session cookies."""
    # 1. Missing cookie
    res_missing = await client.get("/api/session")
    assert res_missing.status_code == 401
    assert "Session missing, invalid or expired" in res_missing.json()["detail"]

    # 2. Forged / invalid cookie
    client.cookies.set(settings.SESSION_COOKIE_NAME, "forged_non_existent_token_1234567890")
    res_invalid = await client.get("/api/session")
    assert res_invalid.status_code == 401

    # 3. Expired cookie
    async with test_env["session_factory"]() as db:
        expired_time = datetime.now(timezone.utc) - timedelta(hours=2)
        sess, token = await create_session(
            db, ttl_hours=1, current_time=expired_time - timedelta(hours=5),
            base_root=test_env["storage_root"]
        )
        await db.commit()

    client.cookies.set(settings.SESSION_COOKIE_NAME, token)
    res_expired = await client.get("/api/session")
    assert res_expired.status_code == 401


@pytest.mark.asyncio
async def test_session_isolation_across_multiple_sessions(test_env, client):
    """Verify strict tenant isolation between two concurrent anonymous sessions."""
    # Create Session A
    res_a = await client.post("/api/session")
    id_a = res_a.json()["id"]
    token_a = res_a.cookies.get(settings.SESSION_COOKIE_NAME)

    # Create Session B
    client.cookies.clear()
    res_b = await client.post("/api/session")
    id_b = res_b.json()["id"]
    token_b = res_b.cookies.get(settings.SESSION_COOKIE_NAME)

    assert id_a != id_b
    assert token_a != token_b

    # Verify storage isolation
    dirs_a = get_session_storage_dirs(id_a, base_root=test_env["storage_root"])
    dirs_b = get_session_storage_dirs(id_b, base_root=test_env["storage_root"])

    # Write synthetic file into Session A uploads
    test_file_a = dirs_a["uploads"] / "sample_resume_a.txt"
    test_file_a.write_text("Session A Confidential Data")

    # Ensure Session B directory does not contain Session A's file
    assert not (dirs_b["uploads"] / "sample_resume_a.txt").exists()
    assert dirs_a["uploads"] != dirs_b["uploads"]


@pytest.mark.asyncio
async def test_session_reset_invalidates_and_deletes_storage(test_env, client):
    """Verify session revocation marks DB record inactive and purges ephemeral directories."""
    res = await client.post("/api/session")
    session_id = res.json()["id"]
    token = res.cookies.get(settings.SESSION_COOKIE_NAME)

    dirs = get_session_storage_dirs(session_id, base_root=test_env["storage_root"])
    # Seed files in each storage category
    (dirs["uploads"] / "resume.pdf").write_text("mock binary content")
    (dirs["exports"] / "export.docx").write_text("mock docx content")
    (dirs["reports"] / "report.pdf").write_text("mock report content")

    # Reset session
    client.cookies.set(settings.SESSION_COOKIE_NAME, token)
    reset_res = await client.post("/api/session/reset")
    assert reset_res.status_code == 200
    assert reset_res.json()["status"] == "reset"

    # Verify storage directories were removed
    for path in dirs.values():
        assert not path.exists()

    # Verify session is inactive in DB
    async with test_env["session_factory"]() as db:
        sess = await db.get(AnonymousSession, session_id)
        assert sess.is_active is False

    # Subsequent check with old cookie returns 401
    status_res = await client.get("/api/session")
    assert status_res.status_code == 401


@pytest.mark.asyncio
async def test_24_hour_inactivity_boundary_and_cleanup(test_env):
    """Verify that cleanup removes sessions past 24h inactivity and leaves active sessions untouched."""
    now = datetime.now(timezone.utc)

    async with test_env["session_factory"]() as db:
        # Active session: created now, expires in 24 hours
        active_sess, active_token = await create_session(
            db, ttl_hours=24, current_time=now, base_root=test_env["storage_root"]
        )
        active_dirs = get_session_storage_dirs(active_sess.id, base_root=test_env["storage_root"])
        (active_dirs["uploads"] / "active.txt").write_text("active payload")

        # Expired session: created 26 hours ago
        expired_time = now - timedelta(hours=26)
        expired_sess = AnonymousSession(
            token_hash=hash_session_token("expired_token_mock_12345"),
            created_at=expired_time,
            last_seen_at=expired_time,
            expires_at=expired_time + timedelta(hours=24),  # Expired 2 hours ago
            is_active=True,
        )
        db.add(expired_sess)
        await db.flush()
        ensure_session_storage(expired_sess.id, base_root=test_env["storage_root"])
        expired_dirs = get_session_storage_dirs(expired_sess.id, base_root=test_env["storage_root"])
        (expired_dirs["uploads"] / "expired.txt").write_text("stale payload")
        await db.commit()

        # Execute cleanup
        purged = await cleanup_expired_sessions(db, current_time=now, base_root=test_env["storage_root"])
        await db.commit()
        assert purged == 1

        # Assert expired session files and DB record are gone
        assert not expired_dirs["uploads"].exists()
        assert await db.get(AnonymousSession, expired_sess.id) is None

        # Assert active session files and DB record are preserved
        assert active_dirs["uploads"].exists()
        assert (active_dirs["uploads"] / "active.txt").exists()
        assert await db.get(AnonymousSession, active_sess.id) is not None


@pytest.mark.asyncio
async def test_cleanup_idempotent_and_safe_with_missing_dirs(test_env):
    """Verify cleanup succeeds idempotently when directories have already been removed."""
    now = datetime.now(timezone.utc)

    async with test_env["session_factory"]() as db:
        past = now - timedelta(hours=30)
        stale_sess = AnonymousSession(
            token_hash=hash_session_token("stale_token_test_12345"),
            created_at=past,
            last_seen_at=past,
            expires_at=past + timedelta(hours=24),
            is_active=True,
        )
        db.add(stale_sess)
        await db.commit()

        # Run cleanup without creating any storage folder
        purged = await cleanup_expired_sessions(db, current_time=now, base_root=test_env["storage_root"])
        await db.commit()
        assert purged == 1


def test_path_traversal_defense_rejected():
    """Verify that path traversal attempts are strictly rejected by session ID validator."""
    with pytest.raises(StorageSecurityError):
        validate_session_id("../etc/passwd")

    with pytest.raises(StorageSecurityError):
        validate_session_id("..\\..\\windows\\system32")

    with pytest.raises(StorageSecurityError):
        validate_session_id("invalid/char/id")

    with pytest.raises(StorageSecurityError):
        validate_session_id("")

    # Valid UUID must pass
    valid_id = str(uuid.uuid4())
    assert validate_session_id(valid_id) == valid_id


@pytest.mark.asyncio
async def test_cors_and_credentials_narrowly_restricted(test_env, client):
    """Verify that CORS with credentials is only granted to explicit trusted origins."""
    # Trusted origin
    res_trusted = await client.options(
        "/api/session",
        headers={
            "Origin": "http://localhost:3000",
            "Access-Control-Request-Method": "POST",
        },
    )
    assert res_trusted.headers.get("access-control-allow-origin") == "http://localhost:3000"
    assert res_trusted.headers.get("access-control-allow-credentials") == "true"

    # Untrusted origin
    res_untrusted = await client.options(
        "/api/session",
        headers={
            "Origin": "http://malicious-attacker.com",
            "Access-Control-Request-Method": "POST",
        },
    )
    assert res_untrusted.headers.get("access-control-allow-origin") != "http://malicious-attacker.com"
