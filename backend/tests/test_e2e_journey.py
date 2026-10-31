"""Phase 10 E2E Journey Integration Test.

Executes the complete 10-step end-to-end user workflow:
1. Ingest: Upload resume document.
2. Review: Retrieve & correct extracted structured profile.
3. Readiness: Execute algorithmic ATS assessment.
4. Match: Evaluate semantic overlap against target job description.
5. Improve: Generate suggestions and accept an active revision.
6. Build: Auto-initialize resume builder document from verified profile.
7. Refine: Customize template typography, layout, and entries.
8. Export PDF: Download ATS-compliant vector PDF and verify text extraction with PyMuPDF.
9. Export DOCX: Download native Microsoft Word DOCX and verify paragraph structure with python-docx.
10. Export Diagnostic Report: Download diagnostic audit PDF and verify combined scores, breakdown, and provenance.
"""

import io
from pathlib import Path
import pymupdf as fitz  # Use the canonical PyMuPDF import; retain fitz namespace internally
import docx
import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.config import settings
from app.database import Base, get_db
from app.main import app
from tests.fixtures.synthetic_generator import create_synthetic_pdf


@pytest.fixture
async def e2e_test_env(tmp_path: Path):
    """Provisions isolated SQLite test database and temporary storage root."""
    test_db_path = tmp_path / "test_e2e.db"
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


@pytest.mark.asyncio
async def test_complete_10_step_user_journey(e2e_test_env):
    """Executes the full 10-step platform workflow and validates all generated artifacts."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Step 0: Ephemeral Session Initialization
        s_res = await client.post("/api/session")
        assert s_res.status_code == 200
        session_cookie = s_res.cookies.get(settings.SESSION_COOKIE_NAME)
        assert session_cookie is not None
        client.cookies.set(settings.SESSION_COOKIE_NAME, session_cookie)

        # Step 1: Ingest (Upload Resume)
        raw_pdf = create_synthetic_pdf(
            name="Samantha Reed",
            email="samantha.reed@example-domain.com",
            phone="+1 (555) 849-2041",
            pages=1,
        )
        upload_res = await client.post(
            "/api/resume/upload",
            files={"file": ("samantha_reed.pdf", raw_pdf, "application/pdf")},
        )
        assert upload_res.status_code == 201
        resume_data = upload_res.json()
        assert resume_data["structured_data"]["contact"]["name"] == "Samantha Reed"

        # Step 2: Review & Correct Extracted Profile
        updated_profile = dict(resume_data["structured_data"])
        updated_profile["contact"]["headline"] = "Lead Distributed Systems Architect"
        put_profile_res = await client.put(
            "/api/resume",
            json={"structured_data": updated_profile},
        )
        assert put_profile_res.status_code == 200

        # Step 3: Run ATS Readiness Assessment
        ats_res = await client.post("/api/assessment")
        assert ats_res.status_code == 200
        ats_json = ats_res.json()
        assert ats_json["overall_score"] > 50
        assert "dimension_scores" in ats_json

        # Step 4: Evaluate Target Job Description Match
        target_jd = """
        Lead Distributed Systems Engineer
        Requirements:
        - 6+ years designing scalable microservices in Python, FastAPI, and Kubernetes.
        - Proven experience with asynchronous event-driven pipelines and PostgreSQL.
        - Experience with automated CI/CD and zero-trust authentication.
        """
        match_res = await client.post(
            "/api/job-match",
            json={"job_description": target_jd, "recalculate": True},
        )
        assert match_res.status_code == 200
        match_json = match_res.json()
        assert match_json["overall_score"] > 40

        # Step 5: Improvement Studio Suggestion Review
        gen_sug_res = await client.post("/api/improvement/generate")
        assert gen_sug_res.status_code == 200
        suggestions = gen_sug_res.json().get("suggestions", [])
        if suggestions:
            # User edits and accepts a suggestion
            s_id = suggestions[0]["id"]
            accept_res = await client.put(
                f"/api/improvement/{s_id}",
                json={
                    "action": "accept",
                    "user_edited_text": "Architected event-driven microservices cutting API latency by 45%.",
                },
            )
            assert accept_res.status_code == 200
            assert accept_res.json()["status"] == "accepted"

        # Step 6 & 7: Auto-Initialize & Refine Resume Builder
        b_init = await client.get("/api/builder")
        assert b_init.status_code == 200
        builder_doc = b_init.json()
        assert builder_doc["version"] == 1

        # Customize builder typography while retaining the single canonical template
        refine_payload = {
            "version": 1,
            "template_id": "ats_professional",
            "template_config": {
                "font_family": "merriweather",
                "font_size": "medium",
                "margin_size": "standard",
                "line_spacing": "normal",
                "accent_color": "#181A1D",
            },
        }
        b_save_res = await client.put("/api/builder", json=refine_payload)
        assert b_save_res.status_code == 200
        assert b_save_res.json()["version"] == 2
        assert b_save_res.json()["template_id"] == "ats_professional"

        # Step 8: Download Resume PDF & Verify Text Layer
        pdf_res = await client.get("/api/export/resume/pdf?version=2")
        assert pdf_res.status_code == 200
        assert pdf_res.headers["content-type"] == "application/pdf"
        assert 'filename="RESUMIND_Samantha_Reed_v2.pdf"' in pdf_res.headers["content-disposition"]

        extracted_pdf = fitz.open(stream=pdf_res.content, filetype="pdf")
        assert extracted_pdf.page_count >= 1
        pdf_text = "".join(page.get_text() for page in extracted_pdf)
        assert "Samantha Reed" in pdf_text
        assert "Lead Distributed Systems Architect" in pdf_text
        assert "samantha.reed@example-domain.com" in pdf_text

        # Step 9: Download Resume DOCX & Verify OpenXML Structure
        docx_res = await client.get("/api/export/resume/docx?version=2")
        assert docx_res.status_code == 200
        assert docx_res.headers["content-type"] == "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        assert 'filename="RESUMIND_Samantha_Reed_v2.docx"' in docx_res.headers["content-disposition"]

        word_doc = docx.Document(io.BytesIO(docx_res.content))
        docx_text = "\n".join(p.text for p in word_doc.paragraphs)
        assert "Samantha Reed" in docx_text
        assert "Lead Distributed Systems Architect" in docx_text

        # Step 10: Download Diagnostic Audit Report PDF
        report_res = await client.get("/api/export/report/pdf")
        assert report_res.status_code == 200
        assert report_res.headers["content-type"] == "application/pdf"
        assert 'filename="RESUMIND_Audit_Report_Samantha_Reed.pdf"' in report_res.headers["content-disposition"]

        rep_pdf = fitz.open(stream=report_res.content, filetype="pdf")
        assert rep_pdf.page_count >= 1
        rep_text = "".join(page.get_text() for page in rep_pdf)

        assert "Diagnostic Resume Improvement Report" in rep_text
        assert "Samantha Reed" in rep_text
        assert "MECHANICAL & STRUCTURAL ATS READINESS" in rep_text.upper()
        assert "Target Role: Lead Distributed Systems Engineer" in rep_text
        assert "IMPROVEMENT STUDIO REVISIONS & PROVENANCE" in rep_text.upper()
        assert "Algorithmic Assessment Limitations & Ethical Guardrails" in rep_text
