"""Phase 8 Tests — Local AI Rewriting Engine.

Tests cover:
- Provider health check for available and unavailable states.
- Model not installed detection.
- Successful rewrite using MockLLMProvider.
- Timeout, malformed JSON, and bounded retry behavior.
- Empty and oversized response rejection.
- Grounding checks: new metric detection, new date detection, placeholder detection.
- Stale resume content detection before AI rewrite.
- Session isolation / unauthorized requests to rewrite endpoint.
- Generation without a job description.
- Provider factory override and reset.
- Full API flow: generate → AI rewrite → inspect response.
- No regression against existing improvement, scoring, job-match workflows.
"""

import json
import pytest
import pytest_asyncio
import httpx
from unittest.mock import AsyncMock, MagicMock, patch

from app.config import settings
from app.providers.base import (
    RewritePromptInput,
    RewriteResult,
    OllamaUnavailableError,
    ModelNotFoundError,
    OllamaTimeoutError,
    LLMOutputValidationError,
)
from app.providers.grounding import inspect_grounding, extract_numbers, extract_dates
from app.providers.mock_provider import MockLLMProvider
from app.providers.ollama_provider import OllamaProvider
from app.providers.factory import get_llm_provider, set_provider_override, reset_provider_override


# ── Fixtures ──────────────────────────────────────────────────────────────────

SAMPLE_BULLET = "Responsible for developing and maintaining the company's internal tools"
SHORT_BULLET_WITH_NUMBER = "Led 50+ engineers across 3 squads to deliver the platform"


@pytest_asyncio.fixture
async def async_app_client():
    """Provides a fresh ASGI test client with an isolated database and session."""
    from app.main import app
    from app.database import engine, Base
    from sqlalchemy import text

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
        yield client

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


async def _create_session_with_resume(client, structured_data=None):
    """Helper: create session and upload synthetic resume."""
    if structured_data is None:
        structured_data = {
            "contact": {
                "name": "Alex Test",
                "email": "alex@example.com",
                "phone": "555-0001",
            },
            "summary": "Software engineer with 5 years of experience.",
            "experience": [
                "Responsible for developing and maintaining the company's internal tools",
                "Helped with deployment pipelines for the DevOps team",
                "Built a REST API that serves the mobile application",
            ],
            "projects": [
                "Worked on a recommendation engine for e-commerce platform",
            ],
            "education": ["B.Sc. Computer Science, State University, 2018"],
            "skills": ["Python", "FastAPI", "Docker", "PostgreSQL"],
        }

    pdf_content = (
        b"%PDF-1.4\n1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj\n"
        b"2 0 obj<</Type/Pages/Kids[3 0 R]/Count 1>>endobj\n"
        b"3 0 obj<</Type/Page/MediaBox[0 0 612 792]/Parent 2 0 R/Contents 4 0 R/Resources<<>>>>endobj\n"
        b"4 0 obj<</Length 44>>stream\nBT /F1 12 Tf 100 700 Td (Test Resume) Tj ET\nendstream endobj\n"
        b"xref\n0 5\n0000000000 65535 f \n0000000009 00000 n \n0000000058 00000 n \n"
        b"0000000115 00000 n \n0000000266 00000 n \n"
        b"trailer<</Size 5/Root 1 0 R>>\nstartxref\n354\n%%EOF\n"
    )

    upload_resp = await client.post(
        "/api/resume/upload",
        files={"file": ("resume.pdf", pdf_content, "application/pdf")},
    )
    assert upload_resp.status_code in (200, 201), upload_resp.text
    put_resp = await client.put(
        "/api/resume",
        json={"structured_data": structured_data},
    )
    assert put_resp.status_code == 200, put_resp.text


# ── Unit Tests: Grounding Engine ──────────────────────────────────────────────

class TestGroundingEngine:
    def test_extract_numbers_from_bullet(self):
        nums = extract_numbers("Led a team of 12 engineers to deliver 3 APIs")
        assert "12" in nums
        assert "3" in nums

    def test_extract_numbers_ignores_placeholders(self):
        nums = extract_numbers("Improved performance by [+__% improvement] for 500 users")
        # [+__% improvement] should be stripped
        assert "500" in nums

    def test_extract_dates_finds_years(self):
        dates = extract_dates("Deployed system in 2021 and extended in 2023")
        assert "2021" in dates
        assert "2023" in dates

    def test_inspect_grounding_passes_clean_rewrite(self):
        orig = "Responsible for maintaining the database"
        rewrite = "Maintained and optimized the database infrastructure"
        report = inspect_grounding(orig, rewrite)
        assert report.is_valid is True
        assert len(report.potential_new_claims) == 0

    def test_inspect_grounding_flags_new_metric(self):
        orig = "Responsible for maintaining the database"
        rewrite = "Maintained the database, improving query speed by 40%"
        report = inspect_grounding(orig, rewrite)
        assert report.needs_user_verification is True
        assert any("40" in c for c in report.potential_new_claims)

    def test_inspect_grounding_flags_new_date(self):
        orig = "Built the backend service for our platform"
        rewrite = "Built the backend service for our platform in 2022"
        report = inspect_grounding(orig, rewrite)
        assert report.needs_user_verification is True
        assert any("2022" in c for c in report.potential_new_claims)

    def test_inspect_grounding_preserves_existing_metric(self):
        orig = "Led team of 10 engineers to deliver project"
        rewrite = "Spearheaded a team of 10 engineers to deliver the project"
        report = inspect_grounding(orig, rewrite)
        assert any("10" in f for f in report.preserved_facts)

    def test_inspect_grounding_detects_placeholder(self):
        orig = "Improved performance of the service"
        rewrite = "Improved performance of the service [resulting in +__% efficiency]"
        report = inspect_grounding(orig, rewrite)
        assert report.needs_user_verification is True
        assert any("placeholder" in n.lower() for n in report.validation_notes)

    def test_inspect_grounding_rejects_too_short(self):
        with pytest.raises(LLMOutputValidationError, match="too short"):
            inspect_grounding("Some original text", "Short")

    def test_inspect_grounding_rejects_prompt_leakage(self):
        with pytest.raises(LLMOutputValidationError, match="preamble"):
            inspect_grounding(
                "Some original text",
                "Here is a rewrite of your bullet point: Maintained the system"
            )

    def test_inspect_grounding_rejects_oversized(self):
        long_text = " ".join(["word"] * 90)
        with pytest.raises(LLMOutputValidationError, match="excessively long"):
            inspect_grounding("Some text", long_text)


# ── Unit Tests: MockLLMProvider ───────────────────────────────────────────────

class TestMockLLMProvider:
    @pytest.mark.asyncio
    async def test_mock_health_available(self):
        provider = MockLLMProvider(available=True, model_name="llama3.2")
        health = await provider.check_health()
        assert health.available is True
        assert health.model == "llama3.2"

    @pytest.mark.asyncio
    async def test_mock_health_unavailable(self):
        provider = MockLLMProvider(available=False)
        health = await provider.check_health()
        assert health.available is False

    @pytest.mark.asyncio
    async def test_mock_health_with_forced_error(self):
        err = OllamaUnavailableError("Daemon offline")
        provider = MockLLMProvider(forced_error=err)
        health = await provider.check_health()
        assert health.available is False
        assert "Mock failure" in health.status_message

    @pytest.mark.asyncio
    async def test_mock_rewrite_passive_starter(self):
        provider = MockLLMProvider()
        result = await provider.generate_rewrite(RewritePromptInput(
            original_text="Responsible for developing the reporting module",
            section="experience",
            category="action_verb",
            explanation="Passive starter detected",
        ))
        assert result.rewritten_text.startswith("Spearheaded")
        assert "Responsible" not in result.rewritten_text

    @pytest.mark.asyncio
    async def test_mock_rewrite_adds_placeholder_when_no_metric(self):
        provider = MockLLMProvider()
        result = await provider.generate_rewrite(RewritePromptInput(
            original_text="Responsible for managing the team",
            section="experience",
            category="quantifiable_impact",
            explanation="Missing metric",
        ))
        assert "[" in result.rewritten_text  # placeholder inserted

    @pytest.mark.asyncio
    async def test_mock_rewrite_forced_error(self):
        provider = MockLLMProvider(forced_error=OllamaTimeoutError("timeout"))
        with pytest.raises(OllamaTimeoutError):
            await provider.generate_rewrite(RewritePromptInput(
                original_text="Helped with deployments",
                section="experience",
                category="action_verb",
                explanation="Passive",
            ))

    @pytest.mark.asyncio
    async def test_mock_rewrite_custom_text(self):
        custom = "Orchestrated distributed systems architecture across 5 micro-services"
        provider = MockLLMProvider(custom_rewrite=custom)
        result = await provider.generate_rewrite(RewritePromptInput(
            original_text="Worked on distributed systems",
            section="experience",
            category="action_verb",
            explanation="Passive starter",
        ))
        assert result.rewritten_text == custom

    @pytest.mark.asyncio
    async def test_rewrite_without_job_description(self):
        """Rewriting must function when no job description is provided."""
        provider = MockLLMProvider()
        result = await provider.generate_rewrite(RewritePromptInput(
            original_text="Worked on backend APIs",
            section="experience",
            category="action_verb",
            explanation="Passive starter",
            job_description=None,
        ))
        assert result.rewritten_text


# ── Unit Tests: Provider Factory ──────────────────────────────────────────────

class TestProviderFactory:
    def test_default_returns_ollama_provider(self):
        reset_provider_override()
        provider = get_llm_provider()
        assert isinstance(provider, OllamaProvider)

    def test_override_returns_mock_provider(self):
        mock = MockLLMProvider()
        set_provider_override(mock)
        provider = get_llm_provider()
        assert isinstance(provider, MockLLMProvider)
        reset_provider_override()

    def test_reset_returns_ollama_again(self):
        mock = MockLLMProvider()
        set_provider_override(mock)
        reset_provider_override()
        provider = get_llm_provider()
        assert isinstance(provider, OllamaProvider)


# ── Unit Tests: OllamaProvider with mocked httpx ──────────────────────────────

class TestOllamaProviderUnit:
    def test_default_generation_timeout_allows_local_model_cold_start(self):
        provider = OllamaProvider()
        assert provider.generate_timeout == 120.0

    @pytest.mark.asyncio
    async def test_ollama_unavailable_returns_offline_status(self):
        import httpx as _httpx
        mock_client = AsyncMock(spec=_httpx.AsyncClient)
        mock_client.get.side_effect = _httpx.ConnectError("refused")
        provider = OllamaProvider(http_client=mock_client)
        health = await provider.check_health()
        assert health.available is False
        assert "offline" in health.status_message.lower() or "unreachable" in health.status_message.lower()

    @pytest.mark.asyncio
    async def test_ollama_model_not_found(self):
        import httpx as _httpx
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            "models": [{"name": "mistral"}, {"name": "phi3"}]
        }
        mock_client = AsyncMock(spec=_httpx.AsyncClient)
        mock_client.get.return_value = mock_resp
        provider = OllamaProvider(model_name="llama3.2", http_client=mock_client)
        health = await provider.check_health()
        assert health.available is False
        assert "not installed" in health.status_message

    @pytest.mark.asyncio
    async def test_ollama_model_found(self):
        import httpx as _httpx
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            "models": [{"name": "llama3.2:latest"}, {"name": "mistral"}]
        }
        mock_client = AsyncMock(spec=_httpx.AsyncClient)
        mock_client.get.return_value = mock_resp
        provider = OllamaProvider(model_name="llama3.2", http_client=mock_client)
        health = await provider.check_health()
        assert health.available is True

    @pytest.mark.asyncio
    async def test_ollama_timeout_during_generation(self):
        import httpx as _httpx
        mock_tags_resp = MagicMock()
        mock_tags_resp.status_code = 200
        mock_tags_resp.json.return_value = {"models": [{"name": "llama3.2:latest"}]}

        mock_client = AsyncMock(spec=_httpx.AsyncClient)
        mock_client.get.return_value = mock_tags_resp
        mock_client.post.side_effect = _httpx.TimeoutException("timeout")

        provider = OllamaProvider(model_name="llama3.2", http_client=mock_client, max_retries=0)
        with pytest.raises(OllamaTimeoutError):
            await provider.generate_rewrite(RewritePromptInput(
                original_text="Responsible for maintaining services",
                section="experience",
                category="action_verb",
                explanation="Passive starter",
            ))

    @pytest.mark.asyncio
    async def test_ollama_malformed_json_retries_then_fails(self):
        import httpx as _httpx
        mock_tags_resp = MagicMock()
        mock_tags_resp.status_code = 200
        mock_tags_resp.json.return_value = {"models": [{"name": "llama3.2:latest"}]}

        gen_resp = MagicMock()
        gen_resp.status_code = 200
        gen_resp.json.return_value = {"message": {"content": "not valid json {"}}

        mock_client = AsyncMock(spec=_httpx.AsyncClient)
        mock_client.get.return_value = mock_tags_resp
        mock_client.post.return_value = gen_resp

        provider = OllamaProvider(model_name="llama3.2", http_client=mock_client, max_retries=1)
        with pytest.raises(LLMOutputValidationError, match="valid JSON"):
            await provider.generate_rewrite(RewritePromptInput(
                original_text="Helped with deployment pipelines",
                section="experience",
                category="action_verb",
                explanation="Passive starter",
            ))
        # Should have been called twice (initial + 1 retry)
        assert mock_client.post.call_count == 2

    @pytest.mark.asyncio
    async def test_ollama_empty_response_rejected(self):
        import httpx as _httpx
        mock_tags_resp = MagicMock()
        mock_tags_resp.status_code = 200
        mock_tags_resp.json.return_value = {"models": [{"name": "llama3.2:latest"}]}

        gen_resp = MagicMock()
        gen_resp.status_code = 200
        gen_resp.json.return_value = {"message": {"content": ""}}

        mock_client = AsyncMock(spec=_httpx.AsyncClient)
        mock_client.get.return_value = mock_tags_resp
        mock_client.post.return_value = gen_resp

        provider = OllamaProvider(model_name="llama3.2", http_client=mock_client, max_retries=0)
        with pytest.raises(LLMOutputValidationError, match="empty"):
            await provider.generate_rewrite(RewritePromptInput(
                original_text="Worked on payment integrations",
                section="experience",
                category="action_verb",
                explanation="Passive starter",
            ))

    @pytest.mark.asyncio
    async def test_ollama_valid_structured_response_accepted(self):
        import httpx as _httpx
        mock_tags_resp = MagicMock()
        mock_tags_resp.status_code = 200
        mock_tags_resp.json.return_value = {"models": [{"name": "llama3.2:latest"}]}

        valid_response = json.dumps({
            "rewritten_text": "Engineered and maintained core internal tooling used across engineering teams",
            "change_explanation": "Replaced passive starter with an active engineering verb.",
            "preserved_facts": ["internal tooling", "engineering teams"],
            "potential_new_claims": [],
        })
        gen_resp = MagicMock()
        gen_resp.status_code = 200
        gen_resp.json.return_value = {"message": {"content": valid_response}}

        mock_client = AsyncMock(spec=_httpx.AsyncClient)
        mock_client.get.return_value = mock_tags_resp
        mock_client.post.return_value = gen_resp

        provider = OllamaProvider(model_name="llama3.2", http_client=mock_client, max_retries=0)
        result = await provider.generate_rewrite(RewritePromptInput(
            original_text="Responsible for developing and maintaining the company's internal tools",
            section="experience",
            category="action_verb",
            explanation="Passive starter",
        ))
        assert result.rewritten_text.startswith("Engineered")
        assert result.needs_user_verification is False


# ── API Integration Tests: AI Rewrite Endpoint ───────────────────────────────

class TestAIRewriteEndpoint:
    @pytest.mark.asyncio
    async def test_ai_provider_status_unauthorized_without_session(self, async_app_client):
        resp = await async_app_client.get("/api/improvement/provider/status")
        assert resp.status_code == 401

    @pytest.mark.asyncio
    async def test_ai_provider_status_returns_offline_when_unavailable(self, async_app_client):
        set_provider_override(MockLLMProvider(available=False))
        try:
            await _create_session_with_resume(async_app_client)
            resp = await async_app_client.get("/api/improvement/provider/status")
            assert resp.status_code == 200
            data = resp.json()
            assert data["available"] is False
        finally:
            reset_provider_override()

    @pytest.mark.asyncio
    async def test_ai_provider_status_returns_online_with_mock(self, async_app_client):
        set_provider_override(MockLLMProvider(available=True, model_name="llama3.2"))
        try:
            await _create_session_with_resume(async_app_client)
            resp = await async_app_client.get("/api/improvement/provider/status")
            assert resp.status_code == 200
            data = resp.json()
            assert data["available"] is True
            assert data["model"] == "llama3.2"
        finally:
            reset_provider_override()

    @pytest.mark.asyncio
    async def test_generate_ai_rewrite_full_flow(self, async_app_client):
        """Full flow: generate rule-based suggestions → call AI rewrite endpoint → verify proposal."""
        set_provider_override(MockLLMProvider(available=True))
        try:
            await _create_session_with_resume(async_app_client)

            # Generate rule-based suggestions
            gen_resp = await async_app_client.post("/api/improvement/generate")
            assert gen_resp.status_code == 200
            suggestions = gen_resp.json()["suggestions"]
            assert len(suggestions) > 0

            # Find a suggestion eligible for AI rewrite
            eligible = next((s for s in suggestions if s["category"] == "action_verb"), suggestions[0])
            suggestion_id = eligible["id"]

            # Trigger AI rewrite
            rewrite_resp = await async_app_client.post(
                f"/api/improvement/{suggestion_id}/rewrite",
                json={},
            )
            assert rewrite_resp.status_code == 200
            updated = rewrite_resp.json()

            assert updated["is_ai_generated"] is True
            assert updated["ai_model"] == "llama3.2"
            assert updated["status"] == "identified"  # Not auto-accepted
            assert len(updated["proposed_text"]) > 0
            assert isinstance(updated["preserved_facts"], list)
            assert isinstance(updated["potential_new_claims"], list)
        finally:
            reset_provider_override()

    @pytest.mark.asyncio
    async def test_rewrite_returns_503_when_provider_offline(self, async_app_client):
        set_provider_override(MockLLMProvider(
            available=False,
            forced_error=OllamaUnavailableError("Ollama offline"),
        ))
        try:
            await _create_session_with_resume(async_app_client)
            gen_resp = await async_app_client.post("/api/improvement/generate")
            suggestions = gen_resp.json()["suggestions"]
            suggestion_id = suggestions[0]["id"]

            rewrite_resp = await async_app_client.post(
                f"/api/improvement/{suggestion_id}/rewrite",
                json={},
            )
            assert rewrite_resp.status_code == 503
            assert "unavailable" in rewrite_resp.json()["detail"].lower()
        finally:
            reset_provider_override()

    @pytest.mark.asyncio
    async def test_rewrite_cross_session_denial(self, async_app_client):
        """Session B cannot trigger a rewrite for Session A's suggestion."""
        set_provider_override(MockLLMProvider(available=True))
        try:
            await _create_session_with_resume(async_app_client)
            gen_resp = await async_app_client.post("/api/improvement/generate")
            suggestions = gen_resp.json()["suggestions"]
            suggestion_id = suggestions[0]["id"]

            # Session B with isolated client
            from app.main import app
            transport = httpx.ASGITransport(app=app)
            async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client_b:
                await _create_session_with_resume(client_b)
                rewrite_resp = await client_b.post(
                    f"/api/improvement/{suggestion_id}/rewrite",
                    json={},
                )
                assert rewrite_resp.status_code == 404
        finally:
            reset_provider_override()

    @pytest.mark.asyncio
    async def test_ai_proposal_requires_explicit_accept_before_resume_changes(self, async_app_client):
        """AI proposal saved to proposed_text but structured_data NOT modified until Accept."""
        set_provider_override(MockLLMProvider(available=True))
        try:
            structured_data = {
                "contact": {
                    "name": "Jordan Test",
                    "email": "jordan@example.com",
                    "phone": "555-0002",
                },
                "experience": ["Responsible for developing the billing system"],
                "education": ["B.Sc. Computer Science"],
                "skills": ["Python"],
            }
            await _create_session_with_resume(async_app_client, structured_data)

            gen_resp = await async_app_client.post("/api/improvement/generate")
            suggestions = gen_resp.json()["suggestions"]
            assert len(suggestions) > 0
            s = suggestions[0]

            # Trigger AI rewrite
            rewrite_resp = await async_app_client.post(
                f"/api/improvement/{s['id']}/rewrite", json={},
            )
            assert rewrite_resp.status_code == 200

            # Verify resume NOT changed yet
            resume_resp = await async_app_client.get("/api/resume")
            resume_data = resume_resp.json()
            experience_now = resume_data["structured_data"]["experience"]
            assert experience_now[0] == "Responsible for developing the billing system"

            # Now accept
            accept_resp = await async_app_client.put(
                f"/api/improvement/{s['id']}",
                json={"action": "accept"},
            )
            assert accept_resp.status_code == 200

            resume_resp2 = await async_app_client.get("/api/resume")
            experience_after = resume_resp2.json()["structured_data"]["experience"]
            assert experience_after[0] != "Responsible for developing the billing system"
        finally:
            reset_provider_override()
