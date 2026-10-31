"""Anonymous Session ORM Model.

Stores cryptographically hashed session tokens and lifecycle timestamps.
Raw tokens are never persisted in the database.
"""

from typing import List
import uuid
from datetime import datetime, timezone
from sqlalchemy import Boolean, DateTime, String
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database import Base


def utc_now() -> datetime:
    """Returns the current timezone-aware UTC datetime."""
    return datetime.now(timezone.utc)


class AnonymousSession(Base):
    """Anonymous Session entity.
    
    Identifies a transient, no-login user session via a SHA-256 hash
    of their client-side HttpOnly cookie token.
    """

    __tablename__ = "anonymous_sessions"

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
        nullable=False,
    )

    token_hash: Mapped[str] = mapped_column(
        String(64),
        unique=True,
        index=True,
        nullable=False,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        nullable=False,
    )

    last_seen_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        nullable=False,
    )

    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        index=True,
        nullable=False,
    )

    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
    )

    # Cascading relationship to uploaded resumes
    resumes: Mapped[List["UploadedResume"]] = relationship(
        "UploadedResume",
        back_populates="session",
        cascade="all, delete-orphan",
    )

    # Cascading relationship to ATS assessments
    assessments: Mapped[List["ATSAssessment"]] = relationship(
        "ATSAssessment",
        back_populates="session",
        cascade="all, delete-orphan",
    )

    # Cascading relationship to Job Match assessments
    job_matches: Mapped[List["JobMatchAssessment"]] = relationship(
        "JobMatchAssessment",
        back_populates="session",
        cascade="all, delete-orphan",
    )

    # Cascading relationship to Improvement suggestions
    improvements: Mapped[List["ImprovementSuggestion"]] = relationship(
        "ImprovementSuggestion",
        back_populates="session",
        cascade="all, delete-orphan",
    )

    # Cascading relationship to Resume builder documents
    builder_documents: Mapped[List["ResumeBuilderDocument"]] = relationship(
        "ResumeBuilderDocument",
        back_populates="session",
        cascade="all, delete-orphan",
    )

    def is_expired(self, current_time: datetime | None = None) -> bool:
        """Determines whether this session has expired."""
        now = current_time or utc_now()
        # Normalizes comparison to UTC
        if self.expires_at.tzinfo is None:
            comp_expires = self.expires_at.replace(tzinfo=timezone.utc)
        else:
            comp_expires = self.expires_at
        return not self.is_active or now >= comp_expires

    def __repr__(self) -> str:
        return f"<AnonymousSession id={self.id} is_active={self.is_active}>"
