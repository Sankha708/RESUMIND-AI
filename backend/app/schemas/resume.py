"""Pydantic schemas for resume upload, extraction review, and user corrections."""

from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field


class ContactSchema(BaseModel):
    """Candidate contact information with uncertainty flags."""
    name: Optional[str] = None
    headline: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    urls: List[str] = Field(default_factory=list)
    location: Optional[str] = None
    uncertainty: Dict[str, bool] = Field(default_factory=dict)


class ParsedSkillCategory(BaseModel):
    """Skill category preserved from labeled skills sections when available."""
    category: str = Field(default="Technical Skills", max_length=100)
    skills: List[str] = Field(default_factory=list)


class StructuredProfileSchema(BaseModel):
    """Normalized structured resume profile sections."""
    contact: ContactSchema
    summary: Optional[str] = None
    experience: List[str] = Field(default_factory=list)
    education: List[str] = Field(default_factory=list)
    skills: List[str] = Field(default_factory=list)
    skill_categories: List[ParsedSkillCategory] = Field(default_factory=list)
    projects: List[str] = Field(default_factory=list)
    certifications: List[str] = Field(default_factory=list)
    other: List[str] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)

    model_config = ConfigDict(from_attributes=True)


class ResumeResponse(BaseModel):
    """Public representation of an extracted resume within an anonymous session."""
    id: str
    session_id: str
    filename: str
    file_type: str
    file_size: int
    raw_text: str
    structured_data: StructuredProfileSchema
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ResumeUpdateRequest(BaseModel):
    """User corrections to the structured profile sections."""
    structured_data: StructuredProfileSchema
