"""Resume Builder Document ORM Model.

Stores session-isolated, interactive builder documents containing structured resume
sections, section reordering, visibility flags, template selection, and layout settings.
Decoupled from canonical uploaded resume and historical assessments.
"""

import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from sqlalchemy import DateTime, ForeignKey, Integer, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database import Base


def utc_now() -> datetime:
    """Returns the current timezone-aware UTC datetime."""
    return datetime.now(timezone.utc)


class ResumeBuilderDocument(Base):
    """Builder document entity storing customizable resume content and layout settings."""

    __tablename__ = "resume_builder_documents"

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

    source_resume_id: Mapped[Optional[str]] = mapped_column(
        String(36),
        ForeignKey("uploaded_resumes.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    version: Mapped[int] = mapped_column(
        Integer,
        default=1,
        nullable=False,
        comment="Monotonic version for optimistic concurrency control",
    )

    template_id: Mapped[str] = mapped_column(
        String(50),
        default="ats_professional",
        nullable=False,
        comment="Canonical single-column ATS Professional template",
    )

    template_config: Mapped[Dict[str, Any]] = mapped_column(
        JSON,
        default=lambda: {
            "font_family": "inter",
            "font_size": "medium",
            "margin_size": "standard",
            "line_spacing": "normal",
            "accent_color": "#254B78",
        },
        nullable=False,
    )

    section_order: Mapped[List[str]] = mapped_column(
        JSON,
        default=lambda: [
            "contact",
            "summary",
            "experience",
            "projects",
            "skills",
            "education",
            "certifications",
            "additional",
        ],
        nullable=False,
    )

    section_visibility: Mapped[Dict[str, bool]] = mapped_column(
        JSON,
        default=lambda: {
            "contact": True,
            "summary": True,
            "experience": True,
            "projects": True,
            "skills": True,
            "education": True,
            "certifications": True,
            "additional": True,
        },
        nullable=False,
    )

    content: Mapped[Dict[str, Any]] = mapped_column(
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
        back_populates="builder_documents",
    )

    # Optional relationship to source uploaded resume
    source_resume: Mapped[Optional["UploadedResume"]] = relationship(
        "UploadedResume",
        foreign_keys=[source_resume_id],
    )

    def __repr__(self) -> str:
        return f"<ResumeBuilderDocument id={self.id} session_id={self.session_id} template={self.template_id} v={self.version}>"
