"""Resume upload, parsing, review, and correction API router.

Handles secure multi-part uploads (PDF/DOCX), bound streaming validation (10MB limit),
isolated filesystem storage, PyMuPDF/python-docx extraction, and structured profile editing.
"""

import os
import uuid
from pathlib import Path
from typing import Optional
from fastapi import (
    APIRouter,
    Cookie,
    Depends,
    File,
    HTTPException,
    Response,
    UploadFile,
    status,
)
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database import get_db
from app.models.resume import UploadedResume
from app.models.session import AnonymousSession
from app.schemas.resume import ResumeResponse, ResumeUpdateRequest
from app.services.parser_service import (
    CorruptDocumentError,
    DocumentLimitExceededError,
    EncryptedDocumentError,
    ParserError,
    UnsupportedFileTypeError,
    parse_resume_document,
)
from app.services.session_service import create_session, get_session_by_token
from app.services.storage_service import (
    ensure_session_storage,
    get_session_storage_dirs,
)

router = APIRouter(prefix="/api/resume", tags=["Resume"])

MAX_UPLOAD_SIZE = 10 * 1024 * 1024  # 10 MB maximum
CHUNK_SIZE = 64 * 1024  # 64 KB read buffer


async def resolve_session(
    response: Response,
    db: AsyncSession,
    cookie_token: Optional[str],
) -> AnonymousSession:
    """Resolves existing active session or mints a fresh one if missing or expired."""
    if cookie_token:
        session = await get_session_by_token(db, cookie_token)
        if session:
            return session

    # Mint fresh session if absent or expired
    session, raw_token = await create_session(db)
    response.set_cookie(
        key=settings.SESSION_COOKIE_NAME,
        value=raw_token,
        max_age=settings.SESSION_TTL_HOURS * 3600,
        httponly=settings.SESSION_COOKIE_HTTPONLY,
        samesite=settings.SESSION_COOKIE_SAMESITE,
        secure=settings.SESSION_COOKIE_SECURE,
        path=settings.SESSION_COOKIE_PATH,
    )
    return session


@router.post(
    "/upload",
    response_model=ResumeResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Upload and parse a PDF or DOCX resume document",
)
async def upload_resume(
    response: Response,
    file: UploadFile = File(...),
    resumind_session: Optional[str] = Cookie(default=None, alias=settings.SESSION_COOKIE_NAME),
    db: AsyncSession = Depends(get_db),
):
    """Uploads, validates, extracts, and stores an authentic resume document within the active session."""
    session = await resolve_session(response, db, resumind_session)

    # 1. Validate declared filename and extension
    original_filename = Path(file.filename or "resume.pdf").name
    ext = Path(original_filename).suffix.lower()
    if ext not in [".pdf", ".docx"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported file format '{ext}'. Only .pdf and .docx documents are accepted.",
        )

    # 2. Bounded stream reading to enforce 10MB ceiling without unbounded memory consumption
    file_bytes = bytearray()
    total_size = 0

    while True:
        chunk = await file.read(CHUNK_SIZE)
        if not chunk:
            break
        total_size += len(chunk)
        if total_size > MAX_UPLOAD_SIZE:
            raise HTTPException(
                status_code=status.HTTP_413_CONTENT_TOO_LARGE,
                detail="File exceeds maximum allowable size of 10 MB.",
            )
        file_bytes.extend(chunk)

    if total_size == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="The uploaded document is empty (0 bytes).",
        )

    raw_content = bytes(file_bytes)

    # 3. Ensure isolated session storage directory exists
    storage_dirs = ensure_session_storage(session.id)
    uploads_dir = storage_dirs["uploads"]

    # Generate server-side random filename to eliminate path traversal
    server_filename = f"{uuid.uuid4().hex}{ext}"
    target_storage_path = uploads_dir / server_filename

    # Write file to session-isolated disk
    try:
        with open(target_storage_path, "wb") as f:
            f.write(raw_content)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to store uploaded document securely on the server.",
        ) from e

    # 4. Extract text and parse structured profile sections
    try:
        raw_text, structured_profile = parse_resume_document(raw_content, original_filename)
    except DocumentLimitExceededError as e:
        if target_storage_path.exists():
            target_storage_path.unlink(missing_ok=True)
        raise HTTPException(
            status_code=status.HTTP_413_CONTENT_TOO_LARGE,
            detail=str(e),
        ) from e
    except EncryptedDocumentError as e:
        if target_storage_path.exists():
            target_storage_path.unlink(missing_ok=True)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        ) from e
    except (CorruptDocumentError, UnsupportedFileTypeError) as e:
        if target_storage_path.exists():
            target_storage_path.unlink(missing_ok=True)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        ) from e
    except ParserError as e:
        if target_storage_path.exists():
            target_storage_path.unlink(missing_ok=True)
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=f"Document parsing failed: {str(e)}",
        ) from e
    except Exception as e:
        if target_storage_path.exists():
            target_storage_path.unlink(missing_ok=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Unexpected error occurred during document parsing.",
        ) from e

    # 5. Remove any existing resume record & old file for this session
    stmt = select(UploadedResume).where(UploadedResume.session_id == session.id)
    result = await db.execute(stmt)
    existing_resume = result.scalars().first()

    if existing_resume:
        old_file = uploads_dir / existing_resume.storage_filename
        if old_file.exists():
            old_file.unlink(missing_ok=True)
        await db.delete(existing_resume)
        await db.flush()

    # 6. Persist newly parsed resume record
    resume_record = UploadedResume(
        session_id=session.id,
        filename=original_filename,
        file_type="pdf" if ext == ".pdf" else "docx",
        file_size=total_size,
        storage_filename=server_filename,
        raw_text=raw_text,
        structured_data=structured_profile,
    )
    db.add(resume_record)
    await db.flush()
    await db.commit()
    await db.refresh(resume_record)

    return resume_record


@router.get(
    "",
    response_model=ResumeResponse,
    summary="Get active extracted resume profile for the current session",
)
async def get_active_resume(
    resumind_session: Optional[str] = Cookie(default=None, alias=settings.SESSION_COOKIE_NAME),
    db: AsyncSession = Depends(get_db),
):
    """Retrieves the active extracted resume profile for review."""
    if not resumind_session:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Session missing or expired.",
        )

    session = await get_session_by_token(db, resumind_session)
    if not session:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Session missing or expired.",
        )

    stmt = select(UploadedResume).where(UploadedResume.session_id == session.id)
    result = await db.execute(stmt)
    resume = result.scalars().first()

    if not resume:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No resume document found in the active session.",
        )

    return resume


@router.put(
    "",
    response_model=ResumeResponse,
    summary="Update and correct structured resume profile sections",
)
async def update_resume_sections(
    payload: ResumeUpdateRequest,
    resumind_session: Optional[str] = Cookie(default=None, alias=settings.SESSION_COOKIE_NAME),
    db: AsyncSession = Depends(get_db),
):
    """Updates user-corrected structured profile data within the active session."""
    if not resumind_session:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Session missing or expired.",
        )

    session = await get_session_by_token(db, resumind_session)
    if not session:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Session missing or expired.",
        )

    stmt = select(UploadedResume).where(UploadedResume.session_id == session.id)
    result = await db.execute(stmt)
    resume = result.scalars().first()

    if not resume:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No resume document found to update.",
        )

    # Update structured data
    resume.structured_data = payload.structured_data.model_dump()
    await db.commit()
    await db.refresh(resume)

    return resume


@router.delete(
    "",
    summary="Delete active resume document from session storage and database",
)
async def delete_active_resume(
    resumind_session: Optional[str] = Cookie(default=None, alias=settings.SESSION_COOKIE_NAME),
    db: AsyncSession = Depends(get_db),
):
    """Deletes the active resume document and expunges its uploaded file."""
    if not resumind_session:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Session missing or expired.",
        )

    session = await get_session_by_token(db, resumind_session)
    if not session:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Session missing or expired.",
        )

    stmt = select(UploadedResume).where(UploadedResume.session_id == session.id)
    result = await db.execute(stmt)
    resume = result.scalars().first()

    if resume:
        # Delete file
        dirs = get_session_storage_dirs(session.id)
        file_path = dirs["uploads"] / resume.storage_filename
        if file_path.exists():
            file_path.unlink(missing_ok=True)
        await db.delete(resume)
        await db.commit()

    return {"status": "deleted"}
