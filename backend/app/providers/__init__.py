"""LLM Provider Subsystem.

Exports the base interfaces, providers, and resolution factory.
"""

from app.providers.base import (
    LLMProvider,
    LLMProviderError,
    OllamaUnavailableError,
    ModelNotFoundError,
    OllamaTimeoutError,
    OllamaGenerationError,
    LLMOutputValidationError,
    ProviderHealthStatus,
    RewritePromptInput,
    RewriteResult,
)
from app.providers.ollama_provider import OllamaProvider
from app.providers.mock_provider import MockLLMProvider
from app.providers.factory import get_llm_provider, set_provider_override, reset_provider_override

__all__ = [
    "LLMProvider",
    "LLMProviderError",
    "OllamaUnavailableError",
    "ModelNotFoundError",
    "OllamaTimeoutError",
    "OllamaGenerationError",
    "LLMOutputValidationError",
    "ProviderHealthStatus",
    "RewritePromptInput",
    "RewriteResult",
    "OllamaProvider",
    "MockLLMProvider",
    "get_llm_provider",
    "set_provider_override",
    "reset_provider_override",
]
