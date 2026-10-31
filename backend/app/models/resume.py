"""Uploaded Resume ORM Model.

Stores parsed text, normalized structured profile sections, and metadata
associated strictly with an active anonymous session.
Storage paths and tokens are never exposed.
"""

import uuid
from datetime import datetime, timezone
from typing import Any, Dict, Optional
from sqlalchemy import DateTime, ForeignKey, Integer, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database import Base


def utc_now() -> datetime:
    """Returns the current timezone-aware UTC datetime."""
    return datetime.now(timezone.utc)


class UploadedResume(Base):
    """Resume entity storing extracted and user-verified resume profile content."""

    __tablename__ = "uploaded_resumes"

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

    filename: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    file_type: Mapped[str] = mapped_column(
        String(10),
        nullable=False,
    )

    file_size: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )

    storage_filename: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    raw_text: Mapped[str] = mapped_column(
        Text,
        default="",
        nullable=False,
    )

    structured_data: Mapped[Dict[str, Any]] = mapped_column(
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

    # Relationship to session
    session: Mapped["AnonymousSession"] = relationship(
        "AnonymousSession",
        back_populates="resumes",
    )

    # Cascading relationship to ATS assessments
    assessments: Mapped[list["ATSAssessment"]] = relationship(
        "ATSAssessment",
        back_populates="resume",
        cascade="all, delete-orphan",
    )

    # Cascading relationship to Job Match assessments
    job_matches: Mapped[list["JobMatchAssessment"]] = relationship(
        "JobMatchAssessment",
        back_populates="resume",
        cascade="all, delete-orphan",
    )

    # Cascading relationship to Improvement suggestions
    improvements: Mapped[list["ImprovementSuggestion"]] = relationship(
        "ImprovementSuggestion",
        back_populates="resume",
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return f"<UploadedResume id={self.id} session_id={self.session_id} filename='{self.filename}'>"
