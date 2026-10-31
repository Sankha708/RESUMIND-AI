"""Schemas for session-scoped before/after resume reanalysis."""

from datetime import datetime
from typing import Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field


class ReanalysisSectionDiff(BaseModel):
    key: str
    label: str
    before: str
    after: str
    change: str
    visible_before: bool = True
    visible_after: bool = True


class ReanalysisDimensionDelta(BaseModel):
    label: str
    weight: float
    baseline_score: float = Field(..., ge=0, le=100)
    revised_score: float = Field(..., ge=0, le=100)
    delta: float


class ATSReanalysisDelta(BaseModel):
    baseline_assessment_id: str
    baseline_assessment_at: datetime
    baseline_score: float = Field(..., ge=0, le=100)
    revised_score: float = Field(..., ge=0, le=100)
    delta: float
    dimensions: Dict[str, ReanalysisDimensionDelta]


class JobMatchReanalysisDelta(BaseModel):
    job_title: Optional[str] = None
    baseline_score: Optional[float] = Field(default=None, ge=0, le=100)
    revised_score: Optional[float] = Field(default=None, ge=0, le=100)
    delta: Optional[float] = None
    unavailable_reason: Optional[str] = None
    matched_before: int = 0
    matched_after: int = 0
    partially_supported_before: int = 0
    partially_supported_after: int = 0
    not_demonstrated_before: int = 0
    not_demonstrated_after: int = 0


class ReanalysisResponse(BaseModel):
    available: bool
    reason: Optional[str] = None
    builder_version: Optional[int] = None
    baseline_resume_id: Optional[str] = None
    revised_at: Optional[datetime] = None
    ats: Optional[ATSReanalysisDelta] = None
    job_match: Optional[JobMatchReanalysisDelta] = None
    changed_sections: List[ReanalysisSectionDiff] = Field(default_factory=list)
    resolved_findings: List[str] = Field(default_factory=list)
    limitations: List[str] = Field(default_factory=list)

    model_config = ConfigDict(from_attributes=True)
