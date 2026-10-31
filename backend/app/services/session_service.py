"""Anonymous Session Service.

Handles high-entropy token generation, cryptographic hashing, session lifecycle,
and inactivity-based expiration logic.
"""

import hashlib
import secrets
from datetime import datetime, timedelta, timezone
from pathlib import Path
from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession
from app.config import settings
from app.models.session import AnonymousSession, utc_now
from app.services.storage_service import (
    ensure_session_storage,
    delete_session_storage,
)


def generate_session_token() -> str:
    """Generates a cryptographically secure random token with >= 256 bits of entropy."""
    # 32 bytes = 256 bits of CSPRNG entropy
    return secrets.token_urlsafe(32)


def hash_session_token(token: str) -> str:
    """Computes the SHA-256 hex digest of a raw token.
    
    Tokens are hashed before database lookup or storage to prevent raw token exposure.
    """
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


async def create_session(
    db: AsyncSession,
    ttl_hours: int | None = None,
    current_time: datetime | None = None,
    base_root: Path | None = None,
) -> tuple[AnonymousSession, str]:
    """Creates a new anonymous session record and provisions isolated storage folders.
    
    Returns:
        tuple of (persisted AnonymousSession, raw_token)
    """
    raw_token = generate_session_token()
    token_hash = hash_session_token(raw_token)
    now = current_time or utc_now()
    ttl = ttl_hours if ttl_hours is not None else settings.SESSION_TTL_HOURS
    expires_at = now + timedelta(hours=ttl)

    session = AnonymousSession(
        token_hash=token_hash,
        created_at=now,
        last_seen_at=now,
        expires_at=expires_at,
        is_active=True,
    )
    db.add(session)
    await db.flush()

    # Provision isolated storage directories
    ensure_session_storage(session.id, base_root=base_root)

    return session, raw_token


async def get_session_by_token(
    db: AsyncSession,
    raw_token: str | None,
    current_time: datetime | None = None,
) -> AnonymousSession | None:
    """Retrieves and validates an active session by its raw cookie token.
    
    Refreshes last_seen_at and rolls the 24-hour inactivity expiry window for active sessions.
    Returns None if token is missing, invalid, or expired.
    """
    if not raw_token or len(raw_token.strip()) < 16:
        return None

    token_hash = hash_session_token(raw_token.strip())
    stmt = select(AnonymousSession).where(
        AnonymousSession.token_hash == token_hash,
        AnonymousSession.is_active == True,
    )
    result = await db.execute(stmt)
    session = result.scalars().first()

    if not session:
        return None

    now = current_time or utc_now()
    if session.is_expired(now):
        # Invalidate expired session
        session.is_active = False
        await db.flush()
        return None

    # Refresh last_seen_at and extend expires_at by 24 hours of inactivity allowance
    session.last_seen_at = now
    session.expires_at = now + timedelta(hours=settings.SESSION_TTL_HOURS)
    await db.flush()

    return session


async def revoke_session(
    db: AsyncSession,
    raw_token: str | None,
    base_root: Path | None = None,
) -> bool:
    """Explicitly revokes an active session and expunges its isolated storage files."""
    if not raw_token:
        return False

    token_hash = hash_session_token(raw_token.strip())
    stmt = select(AnonymousSession).where(AnonymousSession.token_hash == token_hash)
    result = await db.execute(stmt)
    session = result.scalars().first()

    if not session:
        return False

    # Purge isolated filesystem directories
    delete_session_storage(session.id, base_root=base_root)

    # Invalidate session in database
    session.is_active = False
    await db.flush()
    return True


async def cleanup_expired_sessions(
    db: AsyncSession,
    current_time: datetime | None = None,
    base_root: Path | None = None,
) -> int:
    """Removes expired or inactive session storage directories and database records.
    
    Idempotent and safe against missing filesystem paths.
    Returns the count of purged sessions.
    """
    now = current_time or utc_now()

    # Query for all expired or inactive sessions
    stmt = select(AnonymousSession).where(
        (AnonymousSession.expires_at <= now) | (AnonymousSession.is_active == False)
    )
    result = await db.execute(stmt)
    expired_sessions = result.scalars().all()

    if not expired_sessions:
        return 0

    purged_count = 0
    expired_ids = []
    for session in expired_sessions:
        delete_session_storage(session.id, base_root=base_root)
        expired_ids.append(session.id)
        purged_count += 1

    # Delete database rows
    del_stmt = delete(AnonymousSession).where(AnonymousSession.id.in_(expired_ids))
    await db.execute(del_stmt)
    await db.flush()

    return purged_count
