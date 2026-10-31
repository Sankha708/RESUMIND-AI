"""Improvement Suggestion ORM Model.

Stores persisted, session-scoped resume improvement suggestions, user edits,
and accept/reject decision lifecycle records.
"""

import uuid
from datetime import datetime, timezone
from typing import Optional
from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database import Base


def utc_now() -> datetime:
    """Returns the current timezone-aware UTC datetime."""
    return datetime.now(timezone.utc)


class ImprovementSuggestion(Base):
    """Resume improvement opportunity with user review status and revision history."""

    __tablename__ = "improvement_suggestions"

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

    section: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        comment="experience, projects, summary, skills",
    )

    item_index: Mapped[Optional[int]] = mapped_column(
        Integer,
        nullable=True,
        comment="Index in section item list if applicable",
    )

    category: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        comment="action_verb, quantifiable_impact, brevity_readability, scope_clarity, repetition",
    )

    original_text: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )

    proposed_text: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )

    user_edited_text: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
    )

    status: Mapped[str] = mapped_column(
        String(20),
        default="identified",
        nullable=False,
        comment="identified, accepted, rejected, edited",
    )

    explanation: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )

    # AI Provenance & Grounding Metadata (Phase 8)
    is_ai_generated: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
    )

    ai_model: Mapped[Optional[str]] = mapped_column(
        String(50),
        nullable=True,
    )

    preserved_facts: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="JSON-encoded list of verified retained facts",
    )

    potential_new_claims: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="JSON-encoded list of potential new claims requiring candidate review",
    )

    needs_user_verification: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
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
        back_populates="improvements",
    )

    resume: Mapped["UploadedResume"] = relationship(
        "UploadedResume",
        back_populates="improvements",
    )

    def __repr__(self) -> str:
        return f"<ImprovementSuggestion id={self.id} section={self.section} status={self.status}>"
