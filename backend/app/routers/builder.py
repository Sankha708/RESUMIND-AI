"""Resume Builder & Template Studio API Router.

Provides endpoints to retrieve, initialize, update, and reset session-scoped
builder documents with optimistic concurrency control and template styling.
"""

from typing import Optional
from fastapi import (
    APIRouter,
    Cookie,
    Depends,
    HTTPException,
    status,
)
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database import get_db
from app.models.builder import ResumeBuilderDocument
from app.models.resume import UploadedResume
from app.schemas.builder import (
    BuilderDocumentUpdateRequest,
    BuilderResetRequest,
    ResumeBuilderDocumentSchema,
)
from app.services.builder_service import (
    DEFAULT_SECTION_ORDER,
    DEFAULT_SECTION_VISIBILITY,
    convert_structured_profile_to_builder_content,
    create_blank_builder_content,
)
from app.services.session_service import get_session_by_token

router = APIRouter(prefix="/api/builder", tags=["Resume Builder"])


@router.get(
    "",
    response_model=ResumeBuilderDocumentSchema,
    summary="Get or initialize active resume builder document for current session",
)
async def get_builder_document(
    resumind_session: Optional[str] = Cookie(default=None, alias=settings.SESSION_COOKIE_NAME),
    db: AsyncSession = Depends(get_db),
):
    """Retrieves the active builder document for the session.
    
    If none exists, auto-initializes one using the session's verified resume
    (if present) or an empty starter profile.
    """
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

    # 1. Check for existing builder document
    stmt_builder = select(ResumeBuilderDocument).where(
        ResumeBuilderDocument.session_id == session.id
    )
    res_builder = await db.execute(stmt_builder)
    doc = res_builder.scalars().first()

    if doc:
        return doc

    # 2. Check for uploaded resume to seed the builder
    stmt_resume = (
        select(UploadedResume)
        .where(UploadedResume.session_id == session.id)
        .order_by(desc(UploadedResume.created_at))
    )
    res_resume = await db.execute(stmt_resume)
    resume = res_resume.scalars().first()

    if resume:
        content = convert_structured_profile_to_builder_content(resume.structured_data)
        source_id = resume.id
    else:
        content = create_blank_builder_content()
        source_id = None

    # 3. Create fresh builder document
    doc = ResumeBuilderDocument(
        session_id=session.id,
        source_resume_id=source_id,
        version=1,
        template_id="ats_professional",
        template_config={
            "font_family": "inter",
            "font_size": "medium",
            "margin_size": "standard",
            "line_spacing": "normal",
            "accent_color": "#254B78",
        },
        section_order=list(DEFAULT_SECTION_ORDER),
        section_visibility=dict(DEFAULT_SECTION_VISIBILITY),
        content=content.model_dump(),
    )
    db.add(doc)
    await db.commit()
    await db.refresh(doc)
    return doc


@router.put(
    "",
    response_model=ResumeBuilderDocumentSchema,
    summary="Update resume builder content, template, and layout settings",
)
async def update_builder_document(
    payload: BuilderDocumentUpdateRequest,
    resumind_session: Optional[str] = Cookie(default=None, alias=settings.SESSION_COOKIE_NAME),
    db: AsyncSession = Depends(get_db),
):
    """Updates content, template selection, section order, or typography.
    
    Protects against stale concurrent overwrites via optimistic concurrency version checks.
    """
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

    stmt = select(ResumeBuilderDocument).where(
        ResumeBuilderDocument.session_id == session.id
    )
    res = await db.execute(stmt)
    doc = res.scalars().first()

    if not doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Resume builder document not found in active session.",
        )

    # Optimistic concurrency check
    if payload.version != doc.version:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Document version mismatch (expected {doc.version}, received {payload.version}). The document may have been updated in another tab.",
        )

    # Apply updates
    if payload.template_id is not None:
        # Normalize legacy template IDs from older clients/documents into the one supported format.
        if payload.template_id not in {"ats_professional", "executive", "minimalist", "technical"}:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid template_id. The supported format is 'ats_professional'.",
            )
        doc.template_id = "ats_professional"

    if payload.template_config is not None:
        doc.template_config = payload.template_config.model_dump()

    if payload.section_order is not None:
        doc.section_order = payload.section_order

    if payload.section_visibility is not None:
        doc.section_visibility = payload.section_visibility

    if payload.content is not None:
        doc.content = payload.content.model_dump()

    # Advance monotonic version
    doc.version += 1

    await db.commit()
    await db.refresh(doc)
    return doc


@router.post(
    "/reset",
    response_model=ResumeBuilderDocumentSchema,
    summary="Reset builder document content from source resume or blank starter",
)
async def reset_builder_document(
    payload: BuilderResetRequest,
    resumind_session: Optional[str] = Cookie(default=None, alias=settings.SESSION_COOKIE_NAME),
    db: AsyncSession = Depends(get_db),
):
    """Resets builder document content to either the uploaded resume state or a blank starter."""
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

    stmt = select(ResumeBuilderDocument).where(
        ResumeBuilderDocument.session_id == session.id
    )
    res = await db.execute(stmt)
    doc = res.scalars().first()

    if not doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Resume builder document not found in active session.",
        )

    if payload.source == "empty":
        content = create_blank_builder_content()
    else:
        # Re-import from reviewed resume
        stmt_resume = (
            select(UploadedResume)
            .where(UploadedResume.session_id == session.id)
            .order_by(desc(UploadedResume.created_at))
        )
        res_resume = await db.execute(stmt_resume)
        resume = res_resume.scalars().first()
        if not resume:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No reviewed resume found in session to reset from. Use 'empty' to reset to a blank canvas.",
            )
        content = convert_structured_profile_to_builder_content(resume.structured_data)
        doc.source_resume_id = resume.id

    doc.content = content.model_dump()
    doc.template_id = "ats_professional"
    if not doc.template_config:
        doc.template_config = {
            "font_family": "inter",
            "font_size": "medium",
            "margin_size": "standard",
            "line_spacing": "normal",
            "accent_color": "#254B78",
        }
    doc.section_order = list(DEFAULT_SECTION_ORDER)
    doc.section_visibility = dict(DEFAULT_SECTION_VISIBILITY)
    doc.version += 1

    await db.commit()
    await db.refresh(doc)
    return doc
