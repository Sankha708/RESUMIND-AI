"""Job Match Assessment ORM Model.

Stores persisted job-match evaluation results, requirements alignment,
and diagnostic recommendations associated strictly with an active anonymous session
and resume document.
"""

import uuid
from datetime import datetime, timezone
from typing import Any, Dict, Optional
from sqlalchemy import Boolean, DateTime, Float, ForeignKey, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database import Base


def utc_now() -> datetime:
    """Returns the current timezone-aware UTC datetime."""
    return datetime.now(timezone.utc)


class JobMatchAssessment(Base):
    """Job Match Assessment entity storing grounded alignment results."""

    __tablename__ = "job_match_assessments"

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

    job_title: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True,
    )

    job_description_raw: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )

    overall_score: Mapped[Optional[float]] = mapped_column(
        Float,
        nullable=True,
    )

    score_withheld: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
    )

    category_scores: Mapped[Dict[str, Any]] = mapped_column(
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
        back_populates="job_matches",
    )

    resume: Mapped["UploadedResume"] = relationship(
        "UploadedResume",
        back_populates="job_matches",
    )

    def __repr__(self) -> str:
        return f"<JobMatchAssessment id={self.id} resume_id={self.resume_id} overall_score={self.overall_score}>"
