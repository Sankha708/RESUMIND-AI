"""Job Match API router.

Provides endpoints to submit a job description, evaluate grounded requirement alignment
against the active session's resume, and retrieve persisted match reports.
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
from app.models.job_match import JobMatchAssessment
from app.models.resume import UploadedResume
from app.schemas.job_match import JobMatchRequest, JobMatchResponse
from app.services.job_match_service import evaluate_job_match
from app.services.session_service import get_session_by_token

router = APIRouter(prefix="/api/job-match", tags=["Job Match"])


@router.post(
    "",
    response_model=JobMatchResponse,
    status_code=status.HTTP_200_OK,
    summary="Evaluate job description match against active resume",
)
async def create_or_get_job_match(
    payload: JobMatchRequest,
    resumind_session: Optional[str] = Cookie(default=None, alias=settings.SESSION_COOKIE_NAME),
    db: AsyncSession = Depends(get_db),
):
    """Evaluates grounded, non-hallucinatory requirement alignment against the active resume.
    
    Idempotency:
      If a match assessment already exists for the same job description text and the resume
      has not been updated since the assessment (and recalculate=False), the existing
      assessment is returned to guarantee reproducible results.
    """
    # 1. Validate non-empty / non-whitespace job description
    cleaned_jd = payload.job_description.strip()
    if not cleaned_jd:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Job description text cannot be empty or whitespace-only.",
        )

    # 2. Authenticate session
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

    # 3. Resolve active resume
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

    # 4. Idempotency check: if same JD evaluated on unchanged resume
    if not payload.recalculate:
        stmt_existing = (
            select(JobMatchAssessment)
            .where(
                JobMatchAssessment.session_id == session.id,
                JobMatchAssessment.resume_id == resume.id,
                JobMatchAssessment.job_description_raw == cleaned_jd,
            )
            .order_by(desc(JobMatchAssessment.created_at))
        )
        existing_res = await db.execute(stmt_existing)
        existing_assessment = existing_res.scalars().first()

        if existing_assessment and existing_assessment.created_at >= resume.updated_at:
            return existing_assessment

    # 5. Execute deterministic grounded job match evaluation
    report = evaluate_job_match(
        jd_text=cleaned_jd,
        raw_text=resume.raw_text,
        structured_data=resume.structured_data,
    )

    # Extract category scores summary dict
    category_scores_dict = {
        cat_key: cat_obj.model_dump()
        for cat_key, cat_obj in report.category_scores.items()
    }

    # 6. Persist assessment entity scoped to session and resume
    assessment = JobMatchAssessment(
        session_id=session.id,
        resume_id=resume.id,
        job_title=report.job_title,
        job_description_raw=cleaned_jd,
        overall_score=report.overall_score,
        score_withheld=report.score_withheld,
        category_scores=category_scores_dict,
        report_data=report.model_dump(),
    )
    db.add(assessment)
    await db.commit()
    await db.refresh(assessment)

    return assessment


@router.get(
    "",
    response_model=JobMatchResponse,
    summary="Get latest Job Match assessment for active resume",
)
async def get_latest_job_match(
    resumind_session: Optional[str] = Cookie(default=None, alias=settings.SESSION_COOKIE_NAME),
    db: AsyncSession = Depends(get_db),
):
    """Retrieves the most recent Job Match assessment for the active session's resume."""
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
        select(JobMatchAssessment)
        .where(
            JobMatchAssessment.session_id == session.id,
            JobMatchAssessment.resume_id == resume.id,
        )
        .order_by(desc(JobMatchAssessment.created_at))
    )
    res_assessment = await db.execute(stmt_assessment)
    assessment = res_assessment.scalars().first()

    if not assessment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No Job Match assessment found for the active resume. Run job matching first.",
        )

    return assessment
