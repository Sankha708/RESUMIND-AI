"""Session management API endpoints.

Handles anonymous session creation, retrieval, status checking, and revocation.
All interactions rely on secure HttpOnly cookies; raw tokens are never exposed in bodies.
"""

from fastapi import APIRouter, Cookie, Depends, HTTPException, Response, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.config import settings
from app.database import get_db
from app.schemas.session import SessionResponse, SessionResetResponse
from app.services.session_service import (
    create_session,
    get_session_by_token,
    revoke_session,
)

router = APIRouter(prefix="/api/session", tags=["Session"])


def _set_session_cookie(response: Response, raw_token: str) -> None:
    """Attaches the HttpOnly, SameSite session token cookie to the response."""
    response.set_cookie(
        key=settings.SESSION_COOKIE_NAME,
        value=raw_token,
        max_age=settings.SESSION_TTL_HOURS * 3600,
        httponly=settings.SESSION_COOKIE_HTTPONLY,
        samesite=settings.SESSION_COOKIE_SAMESITE,
        secure=settings.SESSION_COOKIE_SECURE,
        path=settings.SESSION_COOKIE_PATH,
    )


def _clear_session_cookie(response: Response) -> None:
    """Clears the session token cookie from the client."""
    response.delete_cookie(
        key=settings.SESSION_COOKIE_NAME,
        path=settings.SESSION_COOKIE_PATH,
    )


@router.post(
    "",
    response_model=SessionResponse,
    status_code=status.HTTP_200_OK,
    summary="Create or reuse an anonymous session",
)
async def create_or_reuse_session(
    response: Response,
    resumind_session: str | None = Cookie(default=None, alias=settings.SESSION_COOKIE_NAME),
    db: AsyncSession = Depends(get_db),
):
    """Establishes or verifies an anonymous session.
    
    If a valid session cookie already exists, it is refreshed and returned.
    Otherwise, a new 256-bit cryptographically secure session is minted,
    isolated storage roots are provisioned, and an HttpOnly cookie is attached.
    """
    if resumind_session:
        existing = await get_session_by_token(db, resumind_session)
        if existing:
            return SessionResponse.model_validate(existing)

    # Mint fresh session
    session, raw_token = await create_session(db)
    _set_session_cookie(response, raw_token)
    return SessionResponse.model_validate(session)


@router.get(
    "",
    response_model=SessionResponse,
    summary="Inspect current anonymous session status",
)
async def get_current_session(
    resumind_session: str | None = Cookie(default=None, alias=settings.SESSION_COOKIE_NAME),
    db: AsyncSession = Depends(get_db),
):
    """Validates the active session from the HttpOnly cookie.
    
    Returns 401 Unauthorized if the cookie is missing, invalid, or expired.
    """
    if not resumind_session:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Session missing, invalid or expired",
        )

    session = await get_session_by_token(db, resumind_session)
    if not session:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Session missing, invalid or expired",
        )

    return SessionResponse.model_validate(session)


@router.post(
    "/reset",
    response_model=SessionResetResponse,
    summary="Revoke session and purge ephemeral files",
)
async def reset_session(
    response: Response,
    resumind_session: str | None = Cookie(default=None, alias=settings.SESSION_COOKIE_NAME),
    db: AsyncSession = Depends(get_db),
):
    """Revokes the active session, deletes associated ephemeral files, and clears the cookie."""
    if resumind_session:
        await revoke_session(db, resumind_session)

    _clear_session_cookie(response)
    return SessionResetResponse(
        status="reset",
        message="Session invalidated and temporary files removed",
    )
