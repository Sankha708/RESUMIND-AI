"""Ollama Local LLM Provider Implementation.

Communicates asynchronously with a locally hosted Ollama instance (http://localhost:11434).
Handles timeouts, model presence validation, JSON structured output decoding,
bounded retry, and factual grounding checks.
"""

import json
import logging
from typing import Optional, List, Dict, Any
import httpx

from app.config import Settings
from app.providers.base import (
    LLMProvider,
    ProviderHealthStatus,
    RewritePromptInput,
    RewriteResult,
    OllamaUnavailableError,
    ModelNotFoundError,
    OllamaTimeoutError,
    OllamaGenerationError,
    LLMOutputValidationError,
)
from app.providers.prompts import build_rewrite_prompt, PROMPT_VERSION
from app.providers.grounding import inspect_grounding

logger = logging.getLogger(__name__)


class OllamaProvider(LLMProvider):
    """Local inference provider wrapping the Ollama HTTP REST API."""

    def __init__(
        self,
        base_url: str = "http://localhost:11434",
        model_name: str = "llama3.2",
        connect_timeout: float = 5.0,
        generate_timeout: float = 120.0,
        max_retries: int = 1,
        http_client: Optional[httpx.AsyncClient] = None,
    ):
        self.base_url = base_url.rstrip("/")
        self.model_name = model_name
        self.connect_timeout = connect_timeout
        self.generate_timeout = generate_timeout
        self.max_retries = max_retries
        self._client = http_client

    async def _get_client(self) -> httpx.AsyncClient:
        """Returns shared or transient httpx client."""
        if self._client is not None:
            return self._client
        return httpx.AsyncClient(timeout=httpx.Timeout(self.generate_timeout, connect=self.connect_timeout))

    async def check_health(self) -> ProviderHealthStatus:
        """Query Ollama daemon for operational readiness and model presence."""
        client = await self._get_client()
        should_close = self._client is None

        try:
            resp = await client.get(
                f"{self.base_url}/api/tags",
                timeout=httpx.Timeout(self.connect_timeout, connect=self.connect_timeout),
            )
            if resp.status_code != 200:
                return ProviderHealthStatus(
                    available=False,
                    model=self.model_name,
                    status_message=f"Ollama returned HTTP {resp.status_code}: {resp.text[:100]}",
                )

            data = resp.json()
            models_list = data.get("models", [])
            installed = [m.get("name", "") for m in models_list if m.get("name")]

            # Model names can be tagged e.g. "llama3.2:latest" or "llama3.2"
            base_model_prefix = self.model_name.split(":")[0].lower()
            model_found = any(
                m.lower() == self.model_name.lower()
                or m.lower().startswith(f"{base_model_prefix}:")
                for m in installed
            )

            if model_found:
                return ProviderHealthStatus(
                    available=True,
                    model=self.model_name,
                    status_message=f"Local Ollama ready with model '{self.model_name}'.",
                    installed_models=installed,
                )
            else:
                return ProviderHealthStatus(
                    available=False,
                    model=self.model_name,
                    status_message=(
                        f"Ollama daemon is running, but model '{self.model_name}' is not installed. "
                        f"Run 'ollama run {self.model_name}' to install it."
                    ),
                    installed_models=installed,
                )

        except (httpx.ConnectError, httpx.ConnectTimeout) as err:
            logger.debug("Ollama connect error: %s", err)
            return ProviderHealthStatus(
                available=False,
                model=self.model_name,
                status_message="Ollama is offline or unreachable on http://localhost:11434.",
            )
        except Exception as err:
            logger.debug("Ollama health inspection error: %s", err)
            return ProviderHealthStatus(
                available=False,
                model=self.model_name,
                status_message=f"Could not connect to Ollama: {str(err)}",
            )
        finally:
            if should_close:
                await client.aclose()

    async def generate_rewrite(self, input_data: RewritePromptInput) -> RewriteResult:
        """Call Ollama /api/chat with strict JSON formatting and validate the output."""
        health = await self.check_health()
        if not health.available:
            if "not installed" in health.status_message.lower():
                raise ModelNotFoundError(health.status_message)
            raise OllamaUnavailableError(health.status_message)

        prompt_payload = build_rewrite_prompt(input_data)
        messages = [
            {"role": "system", "content": prompt_payload["system"]},
            {"role": "user", "content": prompt_payload["user"]},
        ]

        client = await self._get_client()
        should_close = self._client is None

        try:
            for attempt in range(self.max_retries + 1):
                try:
                    resp = await client.post(
                        f"{self.base_url}/api/chat",
                        json={
                            "model": self.model_name,
                            "messages": messages,
                            "stream": False,
                            "format": "json",
                            "options": {
                                "temperature": 0.2,
                                "top_p": 0.9,
                            },
                        },
                        timeout=httpx.Timeout(self.generate_timeout, connect=self.connect_timeout),
                    )

                    if resp.status_code != 200:
                        raise OllamaGenerationError(
                            f"Ollama generation failed with status {resp.status_code}: {resp.text[:200]}"
                        )

                    body = resp.json()
                    message_content = body.get("message", {}).get("content", "").strip()

                    if not message_content:
                        raise LLMOutputValidationError("Ollama returned an empty generation response.")

                    parsed_json = json.loads(message_content)
                    rewritten_text = parsed_json.get("rewritten_text", "").strip()
                    change_explanation = parsed_json.get("change_explanation", "").strip()
                    model_facts = parsed_json.get("preserved_facts", [])
                    model_claims = parsed_json.get("potential_new_claims", [])

                    if not rewritten_text:
                        raise LLMOutputValidationError("Model response JSON missing 'rewritten_text'.")

                    # Run strict grounding checks
                    grounding_report = inspect_grounding(
                        original_text=input_data.original_text,
                        rewritten_text=rewritten_text,
                        candidate_skills=input_data.candidate_skills,
                    )

                    combined_claims = list(
                        set(
                            (model_claims if isinstance(model_claims, list) else [])
                            + grounding_report.potential_new_claims
                        )
                    )
                    combined_facts = list(
                        set(
                            (model_facts if isinstance(model_facts, list) else [])
                            + grounding_report.preserved_facts
                        )
                    )

                    return RewriteResult(
                        rewritten_text=rewritten_text,
                        change_explanation=change_explanation or "Strengthened action verb and readability.",
                        preserved_facts=combined_facts,
                        potential_new_claims=combined_claims,
                        needs_user_verification=grounding_report.needs_user_verification,
                        model_name=self.model_name,
                        raw_prompt_version=PROMPT_VERSION,
                    )

                except json.JSONDecodeError as json_err:
                    if attempt < self.max_retries:
                        logger.warning("Malformed JSON from Ollama. Retrying bounded request...")
                        messages.append(
                            {
                                "role": "user",
                                "content": "Your previous response was not valid JSON. Output ONLY valid JSON adhering strictly to the schema.",
                            }
                        )
                        continue
                    raise LLMOutputValidationError(f"Model failed to produce valid JSON: {json_err}")

        except httpx.TimeoutException as timeout_err:
            raise OllamaTimeoutError(
                f"Ollama generation timed out after {self.generate_timeout}s: {timeout_err}"
            )
        except (OllamaUnavailableError, ModelNotFoundError, OllamaTimeoutError, OllamaGenerationError, LLMOutputValidationError):
            raise
        except Exception as unexpected:
            raise OllamaGenerationError(f"Unexpected generation failure: {unexpected}")
        finally:
            if should_close:
                await client.aclose()
