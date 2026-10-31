"""Pydantic schemas for Job Match API requests and responses."""

from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field


class JobMatchRequest(BaseModel):
    """Payload to request job description matching against active resume."""
    job_description: str = Field(
        ...,
        min_length=1,
        max_length=50000,
        description="Raw text of the target job posting.",
    )
    recalculate: bool = Field(
        default=False,
        description="Force recalculation even if an up-to-date assessment exists.",
    )


class ExtractedRequirementSchema(BaseModel):
    """Extracted job description requirement item and match verdict."""
    id: str
    category: str
    original_text: str
    normalized_term: str
    is_required: bool
    match_status: str
    explanation: str
    evidence_snippet: Optional[str] = None
    recommendation: Optional[str] = None


class CategoryScoreSchema(BaseModel):
    """Score and weight evaluation for a specific job-match dimension."""
    category: str
    label: str
    base_weight: float
    normalized_weight: float
    score: float
    is_applicable: bool
    total_requirements: int
    matched_count: int
    partial_count: int
    gap_count: int


class JobMatchReportSchema(BaseModel):
    """Complete grounded job-match report."""
    job_title: Optional[str] = None
    overall_score: Optional[float] = None
    score_withheld: bool = False
    withheld_reason: Optional[str] = None
    category_scores: Dict[str, CategoryScoreSchema]
    requirements: List[ExtractedRequirementSchema] = Field(default_factory=list)
    matched_count: int = 0
    partial_count: int = 0
    gap_count: int = 0
    top_recommendations: List[str] = Field(default_factory=list)
    limitations: List[str] = Field(default_factory=list)
    disclaimer: str


class JobMatchResponse(BaseModel):
    """Public representation of a persisted Job Match assessment."""
    id: str
    session_id: str
    resume_id: str
    job_title: Optional[str] = None
    overall_score: Optional[float] = None
    score_withheld: bool = False
    category_scores: Dict[str, Any]
    report_data: JobMatchReportSchema
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
