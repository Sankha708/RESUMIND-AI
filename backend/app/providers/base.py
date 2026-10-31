"""Abstract LLM Provider Base Interface.

Defines the pluggable LLM interface, typed data models, and exception hierarchy
for local inference providers in RESUMIND AI.
"""

from abc import ABC, abstractmethod
from typing import List, Optional
from pydantic import BaseModel, Field


# ── Exceptions ───────────────────────────────────────────────────────────────

class LLMProviderError(Exception):
    """Base exception for all LLM provider failures."""
    pass


class OllamaUnavailableError(LLMProviderError):
    """Raised when the Ollama daemon is unreachable or port is closed."""
    pass


class ModelNotFoundError(LLMProviderError):
    """Raised when the requested model is not installed/pulled locally."""
    pass


class OllamaTimeoutError(LLMProviderError):
    """Raised when connection or inference exceeds the configured deadline."""
    pass


class OllamaGenerationError(LLMProviderError):
    """Raised when generation fails or returns an unrecoverable error."""
    pass


class LLMOutputValidationError(LLMProviderError):
    """Raised when model output fails defensive JSON schema or grounding checks."""
    pass


# ── Data Contracts ────────────────────────────────────────────────────────────

class ProviderHealthStatus(BaseModel):
    """Health and capability telemetry for the active LLM provider."""
    available: bool
    provider: str = "ollama"
    model: str
    status_message: str
    installed_models: List[str] = Field(default_factory=list)


class RewritePromptInput(BaseModel):
    """Contextual input parameters for a targeted resume rewrite."""
    original_text: str
    section: str
    category: str
    explanation: str
    surrounding_bullets: List[str] = Field(default_factory=list)
    job_description: Optional[str] = None
    candidate_skills: List[str] = Field(default_factory=list)


class RewriteResult(BaseModel):
    """Validated structured rewrite output with grounding metadata."""
    rewritten_text: str
    change_explanation: str
    preserved_facts: List[str] = Field(default_factory=list)
    potential_new_claims: List[str] = Field(default_factory=list)
    needs_user_verification: bool = False
    model_name: str
    raw_prompt_version: str = "1.0.0"


# ── Abstract Provider ────────────────────────────────────────────────────────

class LLMProvider(ABC):
    """Abstract base class for local and synthetic LLM providers."""

    @abstractmethod
    async def check_health(self) -> ProviderHealthStatus:
        """Inspect provider reachability and verify whether the configured model is ready."""
        pass

    @abstractmethod
    async def generate_rewrite(self, input_data: RewritePromptInput) -> RewriteResult:
        """Generate a constrained, groundable resume rewrite."""
        pass
