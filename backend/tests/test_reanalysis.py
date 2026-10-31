"""Regression coverage for authentic, session-scoped differential comparisons."""

from pathlib import Path

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.config import settings
from app.database import Base, get_db
from app.main import app
from app.models.assessment import ATSAssessment
from tests.fixtures.synthetic_generator import create_synthetic_pdf


@pytest.fixture
async def reanalysis_test_env(tmp_path: Path):
    """Use a fresh SQLite database and isolated temporary upload directory."""
    engine = create_async_engine(
        f"sqlite+aiosqlite:///{tmp_path / 'reanalysis.db'}",
        connect_args={"check_same_thread": False},
    )
    session_factory = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)

    previous_storage_root = settings.STORAGE_ROOT
    settings.STORAGE_ROOT = str(tmp_path / "storage")
    Path(settings.STORAGE_ROOT).mkdir(parents=True, exist_ok=True)

    async def override_get_db():
        async with session_factory() as db:
            yield db

    app.dependency_overrides[get_db] = override_get_db
    yield {"engine": engine, "session_factory": session_factory}
    app.dependency_overrides.clear()
    settings.STORAGE_ROOT = previous_storage_root
    await engine.dispose()


async def _upload_and_assess(client: AsyncClient) -> tuple[dict, dict, dict]:
    uploaded = await client.post(
        "/api/resume/upload",
        files={"file": ("synthetic_resume.pdf", create_synthetic_pdf(name="Riley Example", pages=1), "application/pdf")},
    )
    assert uploaded.status_code == 201
    assessment = await client.post("/api/assessment")
    assert assessment.status_code == 200
    builder = await client.get("/api/builder")
    assert builder.status_code == 200
    return uploaded.json(), assessment.json(), builder.json()


@pytest.mark.asyncio
async def test_reanalysis_locked_without_saved_baseline(reanalysis_test_env):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        uploaded = await client.post(
            "/api/resume/upload",
            files={"file": ("synthetic_resume.pdf", create_synthetic_pdf(name="Riley Example", pages=1), "application/pdf")},
        )
        assert uploaded.status_code == 201
        assert (await client.get("/api/builder")).status_code == 200

        response = await client.get("/api/reanalysis")
        assert response.status_code == 200
        assert response.json()["available"] is False
        assert "Run ATS Readiness first" in response.json()["reason"]
        assert response.json()["ats"] is None


@pytest.mark.asyncio
async def test_template_only_changes_do_not_unlock_comparison(reanalysis_test_env):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        _, _, builder = await _upload_and_assess(client)
        response = await client.put(
            "/api/builder",
            json={
                "version": builder["version"],
                "template_id": "ats_professional",
                "template_config": {**builder["template_config"], "font_size": "spacious"},
                "section_order": list(reversed(builder["section_order"])),
            },
        )
        assert response.status_code == 200

        comparison = await client.get("/api/reanalysis")
        assert comparison.status_code == 200
        assert comparison.json()["available"] is False
        assert "Typography and template settings do not count" in comparison.json()["reason"]


@pytest.mark.asyncio
async def test_reanalysis_scores_saved_builder_pdf_without_mutating_baseline(reanalysis_test_env):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        _, baseline, builder = await _upload_and_assess(client)
        job_match = await client.post(
            "/api/job-match",
            json={
                "job_description": """
                Senior Backend Developer
                Requirements:
                - Python programming
                - PostgreSQL database design
                - Docker containerization
                - Kubernetes orchestration
                - Agile and Scrum methodologies
                - 5+ years of experience
                - Bachelor's degree in Computer Science
                """
            },
        )
        assert job_match.status_code == 200
        assert job_match.json()["score_withheld"] is False
        modified_content = builder["content"]
        modified_content["summary"] = (
            (modified_content.get("summary") or "")
            + " Revised synthetic summary describes documented API reliability work."
        )
        update = await client.put(
            "/api/builder",
            json={
                "version": builder["version"],
                "content": modified_content,
                "template_id": "ats_professional",
            },
        )
        assert update.status_code == 200

        response = await client.get("/api/reanalysis")
        assert response.status_code == 200
        result = response.json()
        assert result["available"] is True
        assert result["ats"]["baseline_assessment_id"] == baseline["id"]
        assert result["ats"]["baseline_score"] == baseline["overall_score"]
        assert result["ats"]["delta"] == round(
            result["ats"]["revised_score"] - result["ats"]["baseline_score"], 1
        )
        assert set(result["ats"]["dimensions"]) == {
            "file_integrity", "section_taxonomy", "contact", "bullet_impact", "length_hygiene"
        }
        assert any(section["key"] == "summary" for section in result["changed_sections"])
        assert result["job_match"]["baseline_score"] == job_match.json()["overall_score"]
        assert result["job_match"]["delta"] == round(
            result["job_match"]["revised_score"] - result["job_match"]["baseline_score"], 1
        )
        assert "not independently verified" in result["limitations"][-1]

        async with reanalysis_test_env["session_factory"]() as db:
            records = (await db.execute(select(ATSAssessment))).scalars().all()
            assert len(records) == 1
            assert records[0].id == baseline["id"]
            assert records[0].overall_score == baseline["overall_score"]


@pytest.mark.asyncio
async def test_reanalysis_isolated_between_anonymous_sessions(reanalysis_test_env):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as first_client:
        _, _, builder = await _upload_and_assess(first_client)
        changed = dict(builder["content"])
        changed["summary"] = (changed.get("summary") or "") + " A documented synthetic revision."
        assert (await first_client.put(
            "/api/builder",
            json={"version": builder["version"], "content": changed},
        )).status_code == 200
        first = (await first_client.get("/api/reanalysis")).json()
        assert first["available"] is True

    async with AsyncClient(transport=transport, base_url="http://test") as second_client:
        other_upload = await second_client.post(
            "/api/resume/upload",
            files={"file": ("other_synthetic_resume.pdf", create_synthetic_pdf(name="Casey Sample", pages=1), "application/pdf")},
        )
        assert other_upload.status_code == 201
        second = await second_client.get("/api/reanalysis")
        assert second.status_code == 200
        assert second.json()["available"] is False
        assert second.json()["baseline_resume_id"] != first["baseline_resume_id"]
        assert second.json()["ats"] is None
