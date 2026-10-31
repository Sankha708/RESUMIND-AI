"""ATS Assessment ORM Model.

Stores persisted ATS readiness evaluation results, scores, findings,
and diagnostic recommendations associated strictly with an active anonymous session
and resume document.
"""

import uuid
from datetime import datetime, timezone
from typing import Any, Dict
from sqlalchemy import DateTime, Float, ForeignKey, JSON, String
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database import Base


def utc_now() -> datetime:
    """Returns the current timezone-aware UTC datetime."""
    return datetime.now(timezone.utc)


class ATSAssessment(Base):
    """ATS Assessment entity storing scoring results and diagnostic findings."""

    __tablename__ = "ats_assessments"

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
        nullable=False,
    )

    session_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("anonymous_sessions.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )

    resume_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("uploaded_resumes.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )

    overall_score: Mapped[float] = mapped_column(
        Float,
        nullable=False,
    )

    dimension_scores: Mapped[Dict[str, Any]] = mapped_column(
        JSON,
        default=dict,
        nullable=False,
    )

    report_data: Mapped[Dict[str, Any]] = mapped_column(
        JSON,
        default=dict,
        nullable=False,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        nullable=False,
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        onupdate=utc_now,
        nullable=False,
    )

    # Relationships
    session: Mapped["AnonymousSession"] = relationship(
        "AnonymousSession",
        back_populates="assessments",
    )

    resume: Mapped["UploadedResume"] = relationship(
        "UploadedResume",
        back_populates="assessments",
    )

    def __repr__(self) -> str:
        return f"<ATSAssessment id={self.id} resume_id={self.resume_id} overall_score={self.overall_score}>"
