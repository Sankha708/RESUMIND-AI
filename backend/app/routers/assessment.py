"""ATS Assessment API router.

Provides endpoints to trigger deterministic ATS-readiness analysis and retrieve
persisted assessment reports strictly scoped to the active server-validated anonymous session.
"""

from typing import Optional
from fastapi import (
    APIRouter,
    Cookie,
    Depends,
    HTTPException,
    Query,
    status,
)
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database import get_db
from app.models.assessment import ATSAssessment
from app.models.resume import UploadedResume
from app.schemas.assessment import ATSAssessmentResponse
from app.services.scoring_service import calculate_ats_score
from app.services.session_service import get_session_by_token

router = APIRouter(prefix="/api/assessment", tags=["ATS Assessment"])


@router.post(
    "",
    response_model=ATSAssessmentResponse,
    status_code=status.HTTP_200_OK,
    summary="Compute and persist ATS-readiness assessment for active resume",
)
async def create_or_get_assessment(
    recalculate: bool = Query(
        default=False,
        description="Force recalculation even if an up-to-date assessment already exists.",
    ),
    resumind_session: Optional[str] = Cookie(default=None, alias=settings.SESSION_COOKIE_NAME),
    db: AsyncSession = Depends(get_db),
):
    """Computes transparent, deterministic ATS readiness score for the active resume.
    
    Idempotency Strategy:
      If an assessment already exists for the current resume and the resume has not been
      updated since the assessment was recorded (and recalculate=False), the existing
      assessment is returned to guarantee reproducibility. If recalculate=True or the
      resume profile was updated, a new assessment record is created and returned.
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

    # Resolve active resume within the authenticated session
    stmt = (
        select(UploadedResume)
        .where(UploadedResume.session_id == session.id)
        .order_by(desc(UploadedResume.created_at))
    )
    result = await db.execute(stmt)
    resume = result.scalars().first()

    if not resume:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No resume document found in the active session. Please upload a resume first.",
        )

    # Check for existing up-to-date assessment (idempotency check)
    if not recalculate:
        stmt_existing = (
            select(ATSAssessment)
            .where(
                ATSAssessment.session_id == session.id,
                ATSAssessment.resume_id == resume.id,
            )
            .order_by(desc(ATSAssessment.created_at))
        )
        existing_res = await db.execute(stmt_existing)
        existing_assessment = existing_res.scalars().first()

        if existing_assessment and existing_assessment.created_at >= resume.updated_at:
            return existing_assessment

    # Calculate ATS report deterministically
    report = calculate_ats_score(
        raw_text=resume.raw_text,
        structured_data=resume.structured_data,
        file_type=resume.file_type,
        file_size=resume.file_size,
    )

    # Extract dimension scores summary
    dimension_scores = {
        dim_key: {
            "score": dim_res.score,
            "weight": dim_res.weight,
            "weighted_score": dim_res.weighted_score,
        }
        for dim_key, dim_res in report.subscores.items()
    }

    # Persist assessment record scoped to session and resume
    assessment = ATSAssessment(
        session_id=session.id,
        resume_id=resume.id,
        overall_score=report.overall_score,
        dimension_scores=dimension_scores,
        report_data=report.model_dump(),
    )
    db.add(assessment)
    await db.commit()
    await db.refresh(assessment)

    return assessment


@router.get(
    "",
    response_model=ATSAssessmentResponse,
    summary="Get latest ATS-readiness assessment for active resume",
)
async def get_latest_assessment(
    resumind_session: Optional[str] = Cookie(default=None, alias=settings.SESSION_COOKIE_NAME),
    db: AsyncSession = Depends(get_db),
):
    """Retrieves the most recent ATS readiness assessment for the active session's resume."""
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

    # Resolve active resume
    stmt = (
        select(UploadedResume)
        .where(UploadedResume.session_id == session.id)
        .order_by(desc(UploadedResume.created_at))
    )
    result = await db.execute(stmt)
    resume = result.scalars().first()

    if not resume:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No resume document found in the active session.",
        )

    stmt_assessment = (
        select(ATSAssessment)
        .where(
            ATSAssessment.session_id == session.id,
            ATSAssessment.resume_id == resume.id,
        )
        .order_by(desc(ATSAssessment.created_at))
    )
    res_assessment = await db.execute(stmt_assessment)
    assessment = res_assessment.scalars().first()

    if not assessment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No ATS assessment has been calculated for the current resume yet.",
        )

    return assessment
