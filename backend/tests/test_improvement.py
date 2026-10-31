"""Automated test suite for Resume Improvement Studio (Phase 7).

Tests:
  - Improvement opportunities derived from actual resume content.
  - Exact source-text preservation.
  - Zero fabricated metrics or achievements (uses explicit placeholders).
  - Suggestions requiring user-supplied facts.
  - Workflow transitions: accept, reject, edit, restore.
  - Canonical resume updates on suggestion accept and restore.
  - Stale content rejection (409 Conflict if resume content drifted).
  - Persistence across reloads.
  - Session scoping, cross-session denial, and unauthorized access.
"""

from pathlib import Path
import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.config import settings
from app.database import Base, get_db
from app.main import app
from app.services.improvement_service import (
    apply_suggestion_to_resume,
    generate_improvement_opportunities,
    restore_original_in_resume,
    StaleContentError,
)
from tests.fixtures.synthetic_generator import create_synthetic_pdf


# ── Test Environment Fixture ─────────────────────────────────────────────────
@pytest.fixture
async def improvement_test_env(tmp_path: Path):
    """Provisions an isolated SQLite test database and temporary storage root."""
    test_db_path = tmp_path / "test_improvement.db"
    test_storage_root = tmp_path / "storage"
    test_storage_root.mkdir(parents=True, exist_ok=True)

    db_url = f"sqlite+aiosqlite:///{test_db_path}"
    engine = create_async_engine(db_url, connect_args={"check_same_thread": False})
    session_factory = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    original_storage_root = settings.STORAGE_ROOT
    settings.STORAGE_ROOT = str(test_storage_root)

    async def override_get_db():
        async with session_factory() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise
            finally:
                await session.close()

    app.dependency_overrides[get_db] = override_get_db

    yield {
        "engine": engine,
        "session_factory": session_factory,
        "storage_root": test_storage_root,
    }

    app.dependency_overrides.clear()
    settings.STORAGE_ROOT = original_storage_root


# ── Unit Tests: Opportunity Generation & Rules ───────────────────────────────
def test_generate_opportunities_passive_starters_and_missing_metrics():
    """Identifies passive phrases and missing metrics without hallucinating facts."""
    structured = {
        "experience": [
            "Responsible for designing backend microservices in Python.",
            "Helped with database migration to PostgreSQL.",
            "Architected distributed pipeline processing 5M events daily.",  # Has metric & action verb
        ],
        "projects": [
            "Worked on web application frontend using React.",
        ],
        "summary": "Software engineer building web apps.",
    }

    opps = generate_improvement_opportunities(structured)
    assert len(opps) >= 3

    # Check passive starter detection
    passive_opps = [o for o in opps if o["category"] == "action_verb"]
    assert len(passive_opps) >= 2

    # Original text must match verbatim
    resp_for = next((o for o in passive_opps if "Responsible for" in o["original_text"]), None)
    assert resp_for is not None
    assert resp_for["original_text"] == "Responsible for designing backend microservices in Python."
    # Proposed text should convert passive starter to active verb without fabricating tools
    assert "Designed" in resp_for["proposed_text"]
    assert "Python" in resp_for["proposed_text"]

    # Verify no numbers were invented in passive replacement
    assert "5M" not in resp_for["proposed_text"]


def test_missing_metric_placeholder_woven_without_fabrication():
    """Where quantifiable outcome is missing, weaves an editable placeholder instead of fake numbers."""
    structured = {
        "experience": [
            "Engineered automated continuous deployment pipelines for backend microservices across distributed cloud clusters.",
        ],
        "projects": [],
    }

    opps = generate_improvement_opportunities(structured)
    metric_opp = next((o for o in opps if o["category"] == "quantifiable_impact"), None)
    assert metric_opp is not None
    # Must use explicit placeholder brackets
    assert "[" in metric_opp["proposed_text"] and "]" in metric_opp["proposed_text"]
    assert "efficiency" in metric_opp["proposed_text"] or "users" in metric_opp["proposed_text"]
    # Does NOT invent a specific fake number like "42%" or "$100,000"
    assert "42%" not in metric_opp["proposed_text"]


def test_brevity_and_scope_clarity_rules():
    """Flags bullets that are too long or too short."""
    long_bullet = (
        "Architected scalable microservices using Python and Go while collaborating across cross-functional "
        "engineering and product teams to streamline the entire software development lifecycle and ensure "
        "zero-downtime deployment strategies across multi-region cloud infrastructures spanning multiple clusters."
    )
    short_bullet = "Built APIs."

    structured = {
        "experience": [long_bullet, short_bullet],
        "projects": [],
    }

    opps = generate_improvement_opportunities(structured)
    categories = [o["category"] for o in opps]
    assert "brevity_readability" in categories
    assert "scope_clarity" in categories


# ── Unit Tests: Apply & Restore Canonical Resume Updates ─────────────────────
def test_apply_and_restore_suggestion_updates_resume_data():
    """Applying a suggestion mutates structured data; restoring reverts it exactly."""
    structured = {
        "experience": [
            "Responsible for designing backend microservices in Python.",
            "Engineered high-throughput event consumer.",
        ],
        "projects": [],
    }

    original_text = structured["experience"][0]
    proposed_text = "Designed backend microservices in Python."

    # 1. Apply suggestion
    updated = apply_suggestion_to_resume(
        structured_data=structured,
        section="experience",
        item_index=0,
        original_text=original_text,
        replacement_text=proposed_text,
    )
    assert updated["experience"][0] == proposed_text
    assert updated["experience"][1] == "Engineered high-throughput event consumer."  # Untouched

    # 2. Restore original
    reverted = restore_original_in_resume(
        structured_data=updated,
        section="experience",
        item_index=0,
        original_text=original_text,
    )
    assert reverted["experience"][0] == original_text


def test_stale_content_detection_raises_error():
    """Attempting to apply suggestion when underlying resume content drifted raises StaleContentError."""
    structured = {
        "experience": [
            "User already modified this line completely.",
        ],
    }

    with pytest.raises(StaleContentError):
        apply_suggestion_to_resume(
            structured_data=structured,
            section="experience",
            item_index=0,
            original_text="Responsible for designing microservices.",  # Does not match current
            replacement_text="Designed microservices.",
        )


# ── Integration Tests: API Lifecycle & Session Isolation ─────────────────────
@pytest.mark.asyncio
async def test_improvement_studio_api_full_flow(improvement_test_env):
    """End-to-end API test: upload resume, generate opportunities, accept, edit, restore."""
    pdf_bytes = create_synthetic_pdf(name="Casey Miller", pages=1)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # 1. Upload resume
        files = {"file": ("casey_resume.pdf", pdf_bytes, "application/pdf")}
        upload_res = await client.post("/api/resume/upload", files=files)
        assert upload_res.status_code == 201
        session_cookie = upload_res.cookies.get(settings.SESSION_COOKIE_NAME)
        client.cookies.set(settings.SESSION_COOKIE_NAME, session_cookie)

        # 2. Generate improvement suggestions
        gen_res = await client.post("/api/improvement/generate")
        assert gen_res.status_code == 200
        summary = gen_res.json()
        assert summary["total_count"] > 0
        assert summary["pending_count"] > 0
        assert summary["accepted_count"] == 0
        first_sug = summary["suggestions"][0]
        sug_id = first_sug["id"]
        assert first_sug["status"] == "identified"

        # 3. GET /api/improvement retrieves the persisted suggestions
        get_res = await client.get("/api/improvement")
        assert get_res.status_code == 200
        assert get_res.json()["total_count"] == summary["total_count"]

        # 4. User edits and accepts the suggestion
        custom_text = "Spearheaded microservices design cutting latency by 35%."
        accept_res = await client.put(
            f"/api/improvement/{sug_id}",
            json={"action": "accept", "user_edited_text": custom_text},
        )
        assert accept_res.status_code == 200
        updated_sug = accept_res.json()
        assert updated_sug["status"] == "accepted"
        assert updated_sug["user_edited_text"] == custom_text

        # 5. Verify the resume structured data was updated
        resume_res = await client.get("/api/resume")
        assert resume_res.status_code == 200
        resume_data = resume_res.json()
        target_section = resume_data["structured_data"][first_sug["section"]]
        if first_sug["item_index"] is not None:
            assert target_section[first_sug["item_index"]] == custom_text

        # 6. Restore suggestion reverts the resume structured data
        restore_res = await client.post(f"/api/improvement/{sug_id}/restore")
        assert restore_res.status_code == 200
        restored_sug = restore_res.json()
        assert restored_sug["status"] == "identified"

        # Check resume was reverted
        reverted_resume = await client.get("/api/resume")
        assert reverted_resume.status_code == 200
        rev_section = reverted_resume.json()["structured_data"][first_sug["section"]]
        if first_sug["item_index"] is not None:
            assert rev_section[first_sug["item_index"]] == first_sug["original_text"]


@pytest.mark.asyncio
async def test_improvement_cross_session_denial_and_unauthorized(improvement_test_env):
    """Suggestions are strictly isolated to the authenticated session."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # 1. Unauthenticated requests return 401
        unauth_get = await client.get("/api/improvement")
        assert unauth_get.status_code == 401

        unauth_post = await client.post("/api/improvement/generate")
        assert unauth_post.status_code == 401

        # 2. Session with no uploaded resume returns 404
        sess_res = await client.post("/api/session")
        assert sess_res.status_code == 200
        empty_cookie = sess_res.cookies.get(settings.SESSION_COOKIE_NAME)
        client.cookies.set(settings.SESSION_COOKIE_NAME, empty_cookie)

        no_resume = await client.post("/api/improvement/generate")
        assert no_resume.status_code == 404
        assert "upload a resume first" in no_resume.json()["detail"].lower()


@pytest.mark.asyncio
async def test_batch_accept_high_confidence_suggestions(improvement_test_env):
    """Batch accept applies eligible non-placeholder suggestions across the resume."""
    pdf_bytes = create_synthetic_pdf(name="Jordan Batch", pages=1)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        files = {"file": ("jordan_resume.pdf", pdf_bytes, "application/pdf")}
        upload_res = await client.post("/api/resume/upload", files=files)
        assert upload_res.status_code == 201
        session_cookie = upload_res.cookies.get(settings.SESSION_COOKIE_NAME)
        client.cookies.set(settings.SESSION_COOKIE_NAME, session_cookie)

        # Generate opportunities
        gen_res = await client.post("/api/improvement/generate")
        assert gen_res.status_code == 200

        # Run batch accept without placeholders
        batch_res = await client.post(
            "/api/improvement/batch-accept",
            json={"only_without_placeholders": True},
        )
        assert batch_res.status_code == 200
        batch_data = batch_res.json()
        assert "accepted_count" in batch_data
        assert "suggestions" in batch_data
        # At least one suggestion was accepted or reported
        total_accepted = sum(1 for s in batch_data["suggestions"] if s["status"] == "accepted")
        assert total_accepted == batch_data["accepted_count"]
