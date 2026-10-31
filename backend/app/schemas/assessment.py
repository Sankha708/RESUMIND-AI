"""Pydantic schemas for ATS assessment API requests and responses."""

from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field


class FindingSchema(BaseModel):
    """Diagnostic finding item for an ATS assessment."""
    severity: str = Field(..., description="'critical', 'warning', or 'positive'")
    title: str
    message: str
    evidence: Optional[str] = None


class DimensionResultSchema(BaseModel):
    """Score, weight, strengths, and findings for a single dimension."""
    score: float = Field(..., ge=0.0, le=100.0)
    weight: float
    weighted_score: float
    strengths: List[str] = Field(default_factory=list)
    findings: List[FindingSchema] = Field(default_factory=list)


class ATSReportSchema(BaseModel):
    """Complete ATS readiness report content."""
    overall_score: float = Field(..., ge=0.0, le=100.0)
    subscores: Dict[str, DimensionResultSchema]
    top_strengths: List[str] = Field(default_factory=list)
    prioritized_findings: List[FindingSchema] = Field(default_factory=list)
    limitations: List[str] = Field(default_factory=list)
    disclaimer: str


class ATSAssessmentResponse(BaseModel):
    """Public API response representing a persisted ATS readiness assessment."""
    id: str
    session_id: str
    resume_id: str
    overall_score: float
    dimension_scores: Dict[str, Any]
    report_data: ATSReportSchema
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
