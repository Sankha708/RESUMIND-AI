"""Pydantic schemas for Resume Builder & Template Studio (Screen 6 / Phase 9).

Validates structured resume builder documents, repeatable section items,
template choices, section reordering, and layout configurations.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field


class ContactInfo(BaseModel):
    """Candidate contact information and professional headline."""
    name: str = Field(default="", max_length=200)
    headline: Optional[str] = Field(default="", max_length=250)
    email: Optional[str] = Field(default="", max_length=250)
    phone: Optional[str] = Field(default="", max_length=100)
    location: Optional[str] = Field(default="", max_length=200)
    website: Optional[str] = Field(default="", max_length=500)
    linkedin: Optional[str] = Field(default="", max_length=500)
    github: Optional[str] = Field(default="", max_length=500)


class ExperienceItem(BaseModel):
    """Single repeatable work experience entry."""
    id: str = Field(..., description="Unique entry ID within experience section")
    company: str = Field(default="", max_length=250)
    role: str = Field(default="", max_length=250)
    location: Optional[str] = Field(default="", max_length=200)
    start_date: Optional[str] = Field(default="", max_length=50)
    end_date: Optional[str] = Field(default="", max_length=50)
    current: bool = Field(default=False)
    bullets: List[str] = Field(default_factory=list)


class ProjectItem(BaseModel):
    """Single repeatable portfolio/technical project entry."""
    id: str = Field(..., description="Unique entry ID within projects section")
    title: str = Field(default="", max_length=250)
    role: Optional[str] = Field(default="", max_length=200)
    url: Optional[str] = Field(default="", max_length=500)
    start_date: Optional[str] = Field(default="", max_length=50)
    end_date: Optional[str] = Field(default="", max_length=50)
    bullets: List[str] = Field(default_factory=list)
    tech_stack: List[str] = Field(default_factory=list)


class EducationItem(BaseModel):
    """Single repeatable education credential entry."""
    id: str = Field(..., description="Unique entry ID within education section")
    institution: str = Field(default="", max_length=250)
    degree: Optional[str] = Field(default="", max_length=250)
    field_of_study: Optional[str] = Field(default="", max_length=250)
    start_date: Optional[str] = Field(default="", max_length=50)
    end_date: Optional[str] = Field(default="", max_length=50)
    gpa: Optional[str] = Field(default="", max_length=50)
    highlights: List[str] = Field(default_factory=list)


class SkillCategory(BaseModel):
    """Categorized or grouped skills collection."""
    id: str = Field(..., description="Unique entry ID within skills section")
    category: str = Field(default="Technical Skills", max_length=100)
    skills: List[str] = Field(default_factory=list)


class CertificationItem(BaseModel):
    """Single verified license or certification entry."""
    id: str = Field(..., description="Unique entry ID within certifications section")
    name: str = Field(default="", max_length=250)
    issuer: Optional[str] = Field(default="", max_length=250)
    issue_date: Optional[str] = Field(default="", max_length=50)
    expiry_date: Optional[str] = Field(default="", max_length=50)
    url: Optional[str] = Field(default="", max_length=500)


class AdditionalSectionItem(BaseModel):
    """Custom repeatable section for publications, awards, or volunteer history."""
    id: str = Field(..., description="Unique entry ID within custom section")
    section_title: str = Field(default="Honors & Achievements", max_length=200)
    bullets: List[str] = Field(default_factory=list)


class BuilderContent(BaseModel):
    """Canonical structured content model for the Resume Builder."""
    contact: ContactInfo = Field(default_factory=ContactInfo)
    summary: Optional[str] = Field(default="")
    experience: List[ExperienceItem] = Field(default_factory=list)
    projects: List[ProjectItem] = Field(default_factory=list)
    skills: List[SkillCategory] = Field(default_factory=list)
    education: List[EducationItem] = Field(default_factory=list)
    certifications: List[CertificationItem] = Field(default_factory=list)
    additional: List[AdditionalSectionItem] = Field(default_factory=list)


class TemplateConfig(BaseModel):
    """Aesthetic and typographic tuning parameters for templates."""
    font_family: str = Field(default="inter", description="'inter', 'merriweather', 'roboto_mono'")
    font_size: str = Field(default="medium", description="'compact', 'medium', 'spacious'")
    margin_size: str = Field(default="standard", description="'compact', 'standard', 'wide'")
    line_spacing: str = Field(default="normal", description="'tight', 'normal', 'relaxed'")
    accent_color: str = Field(default="#254B78", description="Hex color code for title accents")


class ResumeBuilderDocumentSchema(BaseModel):
    """Full representation of a persisted resume builder document."""
    id: str
    session_id: str
    source_resume_id: Optional[str] = None
    version: int
    template_id: str
    template_config: TemplateConfig
    section_order: List[str]
    section_visibility: Dict[str, bool]
    content: BuilderContent
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class BuilderDocumentUpdateRequest(BaseModel):
    """Payload to update builder content, template, order, and layout."""
    version: int = Field(..., description="Expected current version for optimistic concurrency control")
    template_id: Optional[str] = Field(default=None, description="Canonical template: ats_professional (legacy IDs are normalized)")
    template_config: Optional[TemplateConfig] = None
    section_order: Optional[List[str]] = None
    section_visibility: Optional[Dict[str, bool]] = None
    content: Optional[BuilderContent] = None


class BuilderResetRequest(BaseModel):
    """Payload to reset builder working document."""
    source: str = Field(
        default="reviewed_resume",
        description="'reviewed_resume' to re-import from uploaded document, or 'empty' for blank starter",
    )
