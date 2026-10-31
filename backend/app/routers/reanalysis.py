"""Session-scoped differential ATS reanalysis endpoint."""

from typing import Optional
from fastapi import APIRouter, Cookie, Depends, HTTPException, status
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database import get_db
from app.models.assessment import ATSAssessment
from app.models.builder import ResumeBuilderDocument
from app.models.job_match import JobMatchAssessment
from app.models.resume import UploadedResume
from app.schemas.reanalysis import ReanalysisResponse
from app.services.reanalysis_service import build_reanalysis
from app.services.session_service import get_session_by_token

router = APIRouter(prefix="/api/reanalysis", tags=["Differential Reanalysis"])


@router.get("", response_model=ReanalysisResponse, summary="Compare saved resume baseline with Builder revision")
async def get_reanalysis(
    resumind_session: Optional[str] = Cookie(default=None, alias=settings.SESSION_COOKIE_NAME),
    db: AsyncSession = Depends(get_db),
):
    if not resumind_session:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Session missing or expired.")
    session = await get_session_by_token(db, resumind_session)
    if not session:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Session missing or expired.")

    resume_result = await db.execute(
        select(UploadedResume)
        .where(UploadedResume.session_id == session.id)
        .order_by(desc(UploadedResume.created_at))
    )
    resume = resume_result.scalars().first()
    baseline = None
    builder = None
    job_baseline = None
    if resume:
        assessment_result = await db.execute(
            select(ATSAssessment)
            .where(ATSAssessment.session_id == session.id, ATSAssessment.resume_id == resume.id)
            .order_by(desc(ATSAssessment.created_at))
        )
        baseline = assessment_result.scalars().first()
        builder_result = await db.execute(
            select(ResumeBuilderDocument)
            .where(ResumeBuilderDocument.session_id == session.id)
            .order_by(desc(ResumeBuilderDocument.updated_at))
        )
        builder = builder_result.scalars().first()
        job_result = await db.execute(
            select(JobMatchAssessment)
            .where(JobMatchAssessment.session_id == session.id, JobMatchAssessment.resume_id == resume.id)
            .order_by(desc(JobMatchAssessment.created_at))
        )
        job_baseline = job_result.scalars().first()

    return build_reanalysis(resume, baseline, builder, job_baseline)
