"""Export Center API Router (Phase 10 — Screen 7).

Provides authenticated, session-scoped endpoints to download ATS-compliant
resume PDFs, editable DOCX documents, and comprehensive diagnostic improvement reports.
"""

from datetime import datetime
import re
from typing import Any, Dict, Optional
from fastapi import (
    APIRouter,
    Cookie,
    Depends,
    HTTPException,
    Query,
    Response,
    status,
)
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database import get_db
from app.models.assessment import ATSAssessment
from app.models.builder import ResumeBuilderDocument
from app.models.improvement import ImprovementSuggestion
from app.models.job_match import JobMatchAssessment
from app.models.resume import UploadedResume
from app.services.audit_report_service import generate_diagnostic_audit_report
from app.services.docx_export_service import generate_resume_docx
from app.services.pdf_export_service import generate_resume_pdf
from app.services.session_service import get_session_by_token

router = APIRouter(prefix="/api/export", tags=["Export Center"])



def _has_exportable_content(content: Dict[str, Any]) -> bool:
    """Return True only when the saved builder document contains candidate content.

    Prevents returning a technically valid but completely blank resume PDF/DOCX.
    Schema labels and layout settings do not count as resume content.
    """
    contact = content.get("contact") or {}
    if any(str(contact.get(key) or "").strip() for key in (
        "name", "headline", "email", "phone", "location", "website", "linkedin", "github"
    )):
        return True

    if str(content.get("summary") or "").strip():
        return True

    for section in ("experience", "projects", "skills", "education", "certifications", "additional"):
        items = content.get(section) or []
        for item in items:
            if not isinstance(item, dict):
                continue
            # Ignore placeholder-only empty records; count actual candidate text.
            text_fields = {
                "experience": ("company", "role", "location", "start_date", "end_date"),
                "projects": ("title", "role", "url", "start_date", "end_date"),
                # A default category label or custom-section title alone is not candidate content.
                "skills": (),
                "education": ("institution", "degree", "field_of_study", "start_date", "end_date", "gpa"),
                "certifications": ("name", "issuer", "issue_date", "url"),
                "additional": (),
            }.get(section, ())
            if any(str(item.get(key) or "").strip() for key in text_fields):
                return True
            for list_key in ("bullets", "skills", "tech_stack", "highlights"):
                values = item.get(list_key) or []
                if any(str(value or "").strip() for value in values):
                    return True
    return False

def sanitize_filename_token(raw_name: str, fallback: str = "Candidate") -> str:
    """Sanitizes user input for inclusion in Content-Disposition filename headers.
    
    Prevents HTTP header injection, path traversal, and illegal characters.
    """
    if not raw_name or not raw_name.strip():
        return fallback
    clean = re.sub(r"[^a-zA-Z0-9_\- ]", "", raw_name).strip()
    clean = re.sub(r"\s+", "_", clean)
    return clean[:50] if clean else fallback


async def _resolve_session_doc(
    session_token: Optional[str],
    db: AsyncSession,
    expected_version: Optional[int] = None,
) -> ResumeBuilderDocument:
    """Helper to validate active session and retrieve the active builder document."""
    if not session_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Session missing or expired.",
        )

    session = await get_session_by_token(db, session_token)
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
            detail="No saved resume builder document found in current session. Please create or save a resume in the Builder first.",
        )

    if expected_version is not None and doc.version != expected_version:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Stale export request (document is at version {doc.version}, requested version {expected_version}). Please refresh.",
        )

    return doc


@router.get("/status", summary="Get export readiness metadata and document summary")
async def get_export_status(
    resumind_session: Optional[str] = Cookie(default=None, alias=settings.SESSION_COOKIE_NAME),
    db: AsyncSession = Depends(get_db),
):
    """Returns active document version, template selection, and assessment presence."""
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

    # 1. Builder Document
    stmt_b = select(ResumeBuilderDocument).where(ResumeBuilderDocument.session_id == session.id)
    res_b = await db.execute(stmt_b)
    builder_doc = res_b.scalars().first()

    # 2. ATS Assessment
    stmt_ats = (
        select(ATSAssessment)
        .where(ATSAssessment.session_id == session.id)
        .order_by(desc(ATSAssessment.created_at))
    )
    res_ats = await db.execute(stmt_ats)
    ats_doc = res_ats.scalars().first()

    # 3. Job Match Assessment
    stmt_jm = (
        select(JobMatchAssessment)
        .where(JobMatchAssessment.session_id == session.id)
        .order_by(desc(JobMatchAssessment.created_at))
    )
    res_jm = await db.execute(stmt_jm)
    jm_doc = res_jm.scalars().first()

    # 4. Improvement Suggestions
    stmt_sug = select(ImprovementSuggestion).where(ImprovementSuggestion.session_id == session.id)
    res_sug = await db.execute(stmt_sug)
    suggestions = res_sug.scalars().all()

    accepted_cnt = sum(1 for s in suggestions if s.status == "accepted")

    name = ""
    template_id = "ats_professional"
    version = 1
    updated_at = None

    if builder_doc:
        name = builder_doc.content.get("contact", {}).get("name", "")
        template_id = "ats_professional"
        version = builder_doc.version
        updated_at = builder_doc.updated_at.isoformat() if builder_doc.updated_at else None

    return {
        "has_builder_document": builder_doc is not None,
        "candidate_name": name,
        "builder_version": version,
        "template_id": template_id,
        "builder_updated_at": updated_at,
        "has_ats_assessment": ats_doc is not None,
        "ats_score": ats_doc.overall_score if ats_doc else None,
        "has_job_match": jm_doc is not None,
        "job_match_title": jm_doc.job_title if jm_doc else None,
        "job_match_score": jm_doc.overall_score if jm_doc else None,
        "suggestions_count": len(suggestions),
        "accepted_suggestions_count": accepted_cnt,
    }


@router.get("/resume/pdf", summary="Download resume as ATS-compliant vector PDF")
async def download_resume_pdf(
    version: Optional[int] = Query(default=None, description="Expected builder document version"),
    resumind_session: Optional[str] = Cookie(default=None, alias=settings.SESSION_COOKIE_NAME),
    db: AsyncSession = Depends(get_db),
):
    """Generates and streams an ATS-parseable single-column vector PDF."""
    doc = await _resolve_session_doc(resumind_session, db, expected_version=version)
    if not _has_exportable_content(doc.content or {}):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="The resume is empty. Add candidate details in the Resume Builder and save before exporting.",
        )

    doc_dict = {
        "content": doc.content,
        "template_id": "ats_professional",
        "template_config": doc.template_config,
        "section_order": doc.section_order,
        "section_visibility": doc.section_visibility,
    }

    try:
        pdf_bytes = generate_resume_pdf(doc_dict)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error generating PDF resume artifact.",
        )

    candidate_name = doc.content.get("contact", {}).get("name", "")
    safe_name = sanitize_filename_token(candidate_name, fallback="Resume")
    filename = f"RESUMIND_{safe_name}_v{doc.version}.pdf"

    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
            "Cache-Control": "no-store, no-cache, must-revalidate",
            "Content-Length": str(len(pdf_bytes)),
        },
    )


@router.get("/resume/docx", summary="Download resume as editable Microsoft Word DOCX")
async def download_resume_docx(
    version: Optional[int] = Query(default=None, description="Expected builder document version"),
    resumind_session: Optional[str] = Cookie(default=None, alias=settings.SESSION_COOKIE_NAME),
    db: AsyncSession = Depends(get_db),
):
    """Generates and streams an editable OpenXML DOCX document."""
    doc = await _resolve_session_doc(resumind_session, db, expected_version=version)
    if not _has_exportable_content(doc.content or {}):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="The resume is empty. Add candidate details in the Resume Builder and save before exporting.",
        )

    doc_dict = {
        "content": doc.content,
        "template_id": "ats_professional",
        "template_config": doc.template_config,
        "section_order": doc.section_order,
        "section_visibility": doc.section_visibility,
    }

    try:
        docx_bytes = generate_resume_docx(doc_dict)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error generating DOCX resume artifact.",
        )

    candidate_name = doc.content.get("contact", {}).get("name", "")
    safe_name = sanitize_filename_token(candidate_name, fallback="Resume")
    filename = f"RESUMIND_{safe_name}_v{doc.version}.docx"

    return Response(
        content=docx_bytes,
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
            "Cache-Control": "no-store, no-cache, must-revalidate",
            "Content-Length": str(len(docx_bytes)),
        },
    )


@router.get("/report/pdf", summary="Download diagnostic improvement report as PDF")
async def download_diagnostic_report_pdf(
    resumind_session: Optional[str] = Cookie(default=None, alias=settings.SESSION_COOKIE_NAME),
    db: AsyncSession = Depends(get_db),
):
    """Generates and streams the PDF Diagnostic Improvement Report."""
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

    # 1. Fetch builder document (for name and version)
    stmt_b = select(ResumeBuilderDocument).where(ResumeBuilderDocument.session_id == session.id)
    res_b = await db.execute(stmt_b)
    builder_doc = res_b.scalars().first()

    candidate_name = "Candidate"
    builder_version = 1
    builder_updated_at = None

    if builder_doc:
        candidate_name = builder_doc.content.get("contact", {}).get("name", "") or "Candidate"
        builder_version = builder_doc.version
        builder_updated_at = builder_doc.updated_at
    else:
        # Fall back to uploaded resume name if present
        stmt_res = (
            select(UploadedResume)
            .where(UploadedResume.session_id == session.id)
            .order_by(desc(UploadedResume.created_at))
        )
        res_res = await db.execute(stmt_res)
        resume_record = res_res.scalars().first()
        if resume_record:
            candidate_name = resume_record.structured_data.get("contact", {}).get("name", "") or "Candidate"

    # 2. Fetch ATS Assessment
    stmt_ats = (
        select(ATSAssessment)
        .where(ATSAssessment.session_id == session.id)
        .order_by(desc(ATSAssessment.created_at))
    )
    res_ats = await db.execute(stmt_ats)
    ats_record = res_ats.scalars().first()
    ats_dict = None
    if ats_record:
        ats_dict = {
            "overall_score": ats_record.overall_score,
            "dimension_scores": ats_record.dimension_scores,
            "report_data": ats_record.report_data,
            "created_at": ats_record.created_at.isoformat() if ats_record.created_at else None,
            "updated_at": ats_record.updated_at.isoformat() if ats_record.updated_at else None,
        }

    # 3. Fetch Job Match Assessment
    stmt_jm = (
        select(JobMatchAssessment)
        .where(JobMatchAssessment.session_id == session.id)
        .order_by(desc(JobMatchAssessment.created_at))
    )
    res_jm = await db.execute(stmt_jm)
    jm_record = res_jm.scalars().first()
    jm_dict = None
    if jm_record:
        jm_dict = {
            "job_title": jm_record.job_title,
            "overall_score": jm_record.overall_score,
            "report_data": jm_record.report_data,
            "created_at": jm_record.created_at.isoformat() if jm_record.created_at else None,
        }

    # 4. Fetch Improvement Suggestions
    stmt_sug = select(ImprovementSuggestion).where(ImprovementSuggestion.session_id == session.id)
    res_sug = await db.execute(stmt_sug)
    suggestions_records = res_sug.scalars().all()
    suggestions_list = [
        {
            "id": s.id,
            "category": s.category,
            "status": s.status,
            "original_text": s.original_text,
            "suggested_text": s.user_edited_text or s.proposed_text,
        }
        for s in suggestions_records
    ]

    try:
        report_bytes = generate_diagnostic_audit_report(
            candidate_name=candidate_name,
            session_id=session.id,
            builder_version=builder_version,
            ats_assessment=ats_dict,
            job_match_assessment=jm_dict,
            improvement_suggestions=suggestions_list,
            builder_updated_at=builder_updated_at,
        )
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error generating diagnostic audit report artifact.",
        )

    safe_name = sanitize_filename_token(candidate_name, fallback="Candidate")
    filename = f"RESUMIND_Audit_Report_{safe_name}.pdf"

    return Response(
        content=report_bytes,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
            "Cache-Control": "no-store, no-cache, must-revalidate",
            "Content-Length": str(len(report_bytes)),
        },
    )
