"""Pydantic schemas for Improvement Studio API requests and responses."""

from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, ConfigDict, Field, field_validator


class ImprovementSuggestionSchema(BaseModel):
    """Public representation of an improvement suggestion item."""
    id: str
    section: str
    item_index: Optional[int] = None
    category: str
    original_text: str
    proposed_text: str
    user_edited_text: Optional[str] = None
    status: str
    explanation: str
    is_ai_generated: bool = False
    ai_model: Optional[str] = None
    preserved_facts: List[str] = Field(default_factory=list)
    potential_new_claims: List[str] = Field(default_factory=list)
    needs_user_verification: bool = False
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)

    @field_validator("preserved_facts", "potential_new_claims", mode="before")
    @classmethod
    def coerce_json_list(cls, val):
        if val is None:
            return []
        if isinstance(val, str):
            import json as _json
            try:
                parsed = _json.loads(val)
                if isinstance(parsed, list):
                    return parsed
                return []
            except Exception:
                return []
        if isinstance(val, list):
            return val
        return []

    @classmethod
    def model_validate(cls, obj, **kwargs):
        """Custom validation to deserialize JSON-encoded list columns from ORM objects."""
        import json as _json
        data = obj
        if hasattr(obj, "__dict__"):
            # ORM object - extract into a dict
            data = {c.key: getattr(obj, c.key) for c in obj.__mapper__.column_attrs}
        if isinstance(data, dict):
            for field_name in ("preserved_facts", "potential_new_claims"):
                val = data.get(field_name)
                if isinstance(val, str):
                    try:
                        data[field_name] = _json.loads(val)
                    except (_json.JSONDecodeError, ValueError):
                        data[field_name] = []
                elif val is None:
                    data[field_name] = []
        return super().model_validate(data, **kwargs)


class UpdateSuggestionRequest(BaseModel):
    """Payload to accept, reject, or edit an improvement suggestion."""
    action: str = Field(..., description="'accept', 'reject', 'edit'")
    user_edited_text: Optional[str] = Field(
        default=None,
        max_length=2000,
        description="Custom revision made by user before or when accepting",
    )


class AIRewriteRequest(BaseModel):
    """Optional parameters when triggering an AI rewrite for a suggestion."""
    custom_instruction: Optional[str] = Field(
        default=None,
        max_length=500,
        description="Optional candidate directive to steer rewrite focus",
    )


class AIProviderStatusResponse(BaseModel):
    """Operational capability and model presence for local AI provider."""
    available: bool
    provider: str = "ollama"
    model: str
    status_message: str
    installed_models: List[str] = Field(default_factory=list)


class ImprovementSummaryResponse(BaseModel):
    """Full list of improvement suggestions with aggregate counts."""
    total_count: int
    accepted_count: int
    rejected_count: int
    pending_count: int
    suggestions: List[ImprovementSuggestionSchema]
    disclaimer: str


class BatchAcceptRequest(BaseModel):
    """Payload to batch accept high-confidence recommendations."""
    category: Optional[str] = Field(
        default=None,
        description="Filter by category e.g. 'action_verb', 'brevity_readability', or None for all",
    )
    only_without_placeholders: bool = Field(
        default=True,
        description="When true, skips suggestions that contain metric or domain placeholders ([...])",
    )


class BatchAcceptResponse(BaseModel):
    """Result of batch accepting suggestions."""
    accepted_count: int
    skipped_count: int
    suggestions: List[ImprovementSuggestionSchema]
    message: str
