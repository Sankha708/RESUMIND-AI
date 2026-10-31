"""Factory for obtaining the active LLM Provider instance.

Supports runtime dependency injection and clean test mocking.
"""

from typing import Optional
from app.config import Settings
from app.providers.base import LLMProvider
from app.providers.ollama_provider import OllamaProvider

_provider_override: Optional[LLMProvider] = None


def get_llm_provider(settings: Optional[Settings] = None) -> LLMProvider:
    """Returns the globally configured or overridden LLM provider."""
    global _provider_override
    if _provider_override is not None:
        return _provider_override

    cfg = settings or Settings()
    return OllamaProvider(
        base_url=cfg.OLLAMA_BASE_URL,
        model_name=cfg.OLLAMA_MODEL,
        connect_timeout=cfg.OLLAMA_CONNECT_TIMEOUT_SEC,
        generate_timeout=cfg.OLLAMA_GENERATE_TIMEOUT_SEC,
        max_retries=cfg.OLLAMA_MAX_RETRIES,
    )


def set_provider_override(provider: Optional[LLMProvider]) -> None:
    """Overrides the active LLM provider (primarily for automated tests)."""
    global _provider_override
    _provider_override = provider


def reset_provider_override() -> None:
    """Clears any active provider override."""
    global _provider_override
    _provider_override = None
