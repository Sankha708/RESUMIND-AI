"""Mock Deterministic LLM Provider for Testing and CI/CD.

Provides predictable, zero-dependency behavior for automated test suites
without requiring an actual Ollama daemon.
"""

from typing import List, Optional
from app.providers.base import (
    LLMProvider,
    ProviderHealthStatus,
    RewritePromptInput,
    RewriteResult,
    LLMProviderError,
)
from app.providers.grounding import inspect_grounding
from app.providers.prompts import PROMPT_VERSION


class MockLLMProvider(LLMProvider):
    """Deterministic in-memory provider for testing."""

    def __init__(
        self,
        available: bool = True,
        model_name: str = "llama3.2",
        installed_models: Optional[List[str]] = None,
        forced_error: Optional[LLMProviderError] = None,
        custom_rewrite: Optional[str] = None,
    ):
        self.available = available
        self.model_name = model_name
        self.installed_models = installed_models or ["llama3.2", "mistral"]
        self.forced_error = forced_error
        self.custom_rewrite = custom_rewrite

    async def check_health(self) -> ProviderHealthStatus:
        if self.forced_error:
            return ProviderHealthStatus(
                available=False,
                model=self.model_name,
                status_message=f"Mock failure: {str(self.forced_error)}",
                installed_models=self.installed_models,
            )
        return ProviderHealthStatus(
            available=self.available,
            model=self.model_name,
            status_message="Mock provider ready." if self.available else "Mock provider unavailable.",
            installed_models=self.installed_models,
        )

    async def generate_rewrite(self, input_data: RewritePromptInput) -> RewriteResult:
        if self.forced_error:
            raise self.forced_error

        if not self.available:
            raise LLMProviderError("Mock provider is marked unavailable.")

        if self.custom_rewrite:
            rewritten_text = self.custom_rewrite
        else:
            # Deterministic, grounded transformation: front-load active verb
            orig = input_data.original_text.strip()
            # Replace common passive starters
            if orig.lower().startswith("responsible for"):
                rewritten_text = "Spearheaded and executed" + orig[15:]
            elif orig.lower().startswith("helped with"):
                rewritten_text = "Collaborated on" + orig[11:]
            elif orig.lower().startswith("worked on"):
                rewritten_text = "Engineered and deployed" + orig[9:]
            else:
                rewritten_text = f"Orchestrated {orig}"

            # If no metric exists, add placeholder
            if not any(char.isdigit() for char in orig):
                rewritten_text += " [resulting in +__% performance / supporting __ users]"

        grounding = inspect_grounding(
            original_text=input_data.original_text,
            rewritten_text=rewritten_text,
            candidate_skills=input_data.candidate_skills,
        )

        return RewriteResult(
            rewritten_text=rewritten_text,
            change_explanation="Strengthened front-loaded action verb and clarified impact.",
            preserved_facts=["Preserved core technical role and scope from original bullet."],
            potential_new_claims=grounding.potential_new_claims,
            needs_user_verification=grounding.needs_user_verification,
            model_name=self.model_name,
            raw_prompt_version=PROMPT_VERSION,
        )
