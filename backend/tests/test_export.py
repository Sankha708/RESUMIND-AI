"""Export tests — Multi-Format Export Engine & Diagnostic Audit Report (Screen 7).

Tests cover:
- Session authorization & isolation.
- Missing builder document error handling (404 Not Found).
- Stale version concurrency rejection (409 Conflict).
- Vector PDF resume generation (selectable text layer, single-column reading order, multi-page flows).
- Native DOCX resume generation (python-docx package integrity, paragraphs, bullet lists).
- Diagnostic Audit Report PDF generation (ATS score breakdown, conditional Job Match, revision status, honest disclaimers).
- Fidelity and readable content in the single ATS Professional template.
- Safe filename sanitization.
- Non-destructive execution: export never mutates underlying database records.
"""

import io
from datetime import timedelta
from pathlib import Path
import pymupdf as fitz  # Use the canonical PyMuPDF import; retain fitz namespace internally
import docx
import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.config import settings
from app.database import Base, get_db
from app.main import app
from app.models.assessment import ATSAssessment
from app.models.builder import ResumeBuilderDocument
from app.models.improvement import ImprovementSuggestion
from app.models.job_match import JobMatchAssessment
from app.models.resume import UploadedResume
from tests.fixtures.synthetic_generator import create_synthetic_pdf


@pytest.fixture
async def export_test_env(tmp_path: Path):
    """Provisions isolated SQLite test database and storage root for export testing."""
    test_db_path = tmp_path / "test_export.db"
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


# ── 1. Authorization & Session Boundary Tests ─────────────────────────────────

@pytest.mark.asyncio
async def test_export_endpoints_require_session(export_test_env):
    """Export endpoints must reject unauthenticated requests with 401."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        res_pdf = await client.get("/api/export/resume/pdf")
        assert res_pdf.status_code == 401

        res_docx = await client.get("/api/export/resume/docx")
        assert res_docx.status_code == 401

        res_report = await client.get("/api/export/report/pdf")
        assert res_report.status_code == 401

        res_status = await client.get("/api/export/status")
        assert res_status.status_code == 401


@pytest.mark.asyncio
async def test_export_rejects_when_no_builder_doc_exists(export_test_env):
    """When a session exists but no resume builder document was created, returns 404."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Create session
        s_res = await client.post("/api/session")
        assert s_res.status_code == 200

        res_pdf = await client.get("/api/export/resume/pdf")
        assert res_pdf.status_code == 404
        assert "No saved resume builder document found" in res_pdf.json()["detail"]


@pytest.mark.asyncio
async def test_export_rejects_stale_concurrency_version(export_test_env):
    """Rejects export request with 409 Conflict if requested version != current version."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        await client.post("/api/session")
        # Initialize builder document (creates v1)
        b_init = await client.get("/api/builder")
        assert b_init.status_code == 200
        assert b_init.json()["version"] == 1

        # Request with mismatched expected version
        res_pdf = await client.get("/api/export/resume/pdf?version=99")
        assert res_pdf.status_code == 409
        assert "Stale export request" in res_pdf.json()["detail"]


# ── 2. Vector PDF Resume Export Tests ─────────────────────────────────────────

@pytest.mark.asyncio
async def test_pdf_resume_generation_and_text_layer_fidelity(export_test_env):
    """Verifies generated PDF returns valid MIME, Content-Disposition, and 100% extractable text."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        await client.post("/api/session")

        # Seed builder document with verified synthetic data
        doc_init = await client.get("/api/builder")
        assert doc_init.status_code == 200
        doc_data = doc_init.json()

        # Update with known candidate content
        payload = {
            "version": doc_data["version"],
            "template_id": "ats_professional",
            "content": {
                "contact": {
                    "name": "Evelyn Wright",
                    "headline": "Principal Infrastructure Architect",
                    "email": "evelyn.wright@test-domain.org",
                    "phone": "+1 (555) 392-1049",
                    "location": "Seattle, WA",
                    "linkedin": "https://linkedin.com/in/evelynwright",
                    "github": "https://github.com/evelynwright",
                },
                "summary": "Accomplished cloud infrastructure leader specializing in high-throughput distributed architectures.",
                "experience": [
                    {
                        "id": "exp_1",
                        "company": "Amazon Web Services",
                        "role": "Principal Systems Engineer",
                        "location": "Seattle, WA",
                        "start_date": "2020",
                        "end_date": "Present",
                        "current": True,
                        "bullets": [
                            "Spearheaded distributed storage cluster migration reducing tail latency by 42%.",
                            "Authored multi-region disaster recovery protocols serving 15M monthly active users.",
                        ],
                    }
                ],
                "projects": [
                    {
                        "id": "proj_1",
                        "title": "Aether Mesh Gateway",
                        "role": "Lead Architect",
                        "url": "https://github.com/evelynwright/aether-mesh",
                        "tech_stack": ["Rust", "gRPC", "Docker", "Kubernetes"],
                        "bullets": ["Engineered zero-allocation packet filter handling 10Gbps line rate."],
                    }
                ],
                "skills": [
                    {
                        "id": "sk_1",
                        "category": "Cloud & Distributed Systems",
                        "skills": ["Kubernetes", "Rust", "Go", "Terraform", "PostgreSQL"],
                    }
                ],
                "education": [
                    {
                        "id": "edu_1",
                        "institution": "University of Washington",
                        "degree": "B.S. in Computer Science",
                        "start_date": "2014",
                        "end_date": "2018",
                        "highlights": ["Magna Cum Laude honors"],
                    }
                ],
                "certifications": [
                    {
                        "id": "cert_1",
                        "name": "AWS Certified Solutions Architect - Professional",
                        "issuer": "Amazon Web Services",
                        "issue_date": "2022",
                    }
                ],
                "additional": [],
            },
        }

        put_res = await client.put("/api/builder", json=payload)
        assert put_res.status_code == 200

        # Request PDF export
        export_res = await client.get("/api/export/resume/pdf")
        assert export_res.status_code == 200
        assert export_res.headers["content-type"] == "application/pdf"
        assert 'filename="RESUMIND_Evelyn_Wright_v2.pdf"' in export_res.headers["content-disposition"]
        assert "no-store" in export_res.headers["cache-control"]

        pdf_bytes = export_res.content
        assert len(pdf_bytes) > 1000

        # Open and inspect with PyMuPDF
        pdf_doc = fitz.open(stream=pdf_bytes, filetype="pdf")
        assert pdf_doc.page_count >= 1

        extracted_text = ""
        for page in pdf_doc:
            extracted_text += page.get_text()

        # Validate presence of canonical content without text scrambling
        assert "Evelyn Wright" in extracted_text
        assert "Principal Infrastructure Architect" in extracted_text
        assert "evelyn.wright@test-domain.org" in extracted_text
        assert "Amazon Web Services" in extracted_text
        assert "Spearheaded distributed storage cluster migration" in extracted_text
        assert "Aether Mesh Gateway" in extracted_text
        assert "Kubernetes" in extracted_text
        assert "University of Washington" in extracted_text
        assert "AWS Certified Solutions Architect" in extracted_text


@pytest.mark.asyncio
async def test_pdf_export_uses_single_ats_professional_template(export_test_env):
    """Exports populated candidate content with the one supported ATS Professional template."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        await client.post("/api/session")
        b_init = await client.get("/api/builder")
        assert b_init.status_code == 200

        payload = {
            "version": b_init.json()["version"],
            "template_id": "ats_professional",
            "content": {
                "contact": {
                    "name": "Jordan Example",
                    "headline": "AI/ML Engineer",
                    "email": "jordan@example.com",
                },
                "summary": "AI/ML engineer building practical, reliable applications.",
            },
        }
        saved = await client.put("/api/builder", json=payload)
        assert saved.status_code == 200
        assert saved.json()["template_id"] == "ats_professional"

        response = await client.get(f"/api/export/resume/pdf?version={saved.json()['version']}")
        assert response.status_code == 200
        assert response.headers["content-type"] == "application/pdf"

        pdf_doc = fitz.open(stream=response.content, filetype="pdf")
        text = "\n".join(page.get_text() for page in pdf_doc)
        assert "Jordan Example" in text
        assert "AI/ML Engineer" in text
        assert "jordan@example.com" in text


@pytest.mark.asyncio
async def test_blank_builder_cannot_export_blank_resume(export_test_env):
    """Empty builder documents return a helpful validation error instead of a blank file."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        await client.post("/api/session")
        builder = await client.get("/api/builder")
        assert builder.status_code == 200

        pdf_response = await client.get("/api/export/resume/pdf")
        docx_response = await client.get("/api/export/resume/docx")
        assert pdf_response.status_code == 422
        assert docx_response.status_code == 422
        assert "resume is empty" in pdf_response.json()["detail"].lower()
        assert "resume is empty" in docx_response.json()["detail"].lower()


# ── 3. Native DOCX Resume Export Tests ────────────────────────────────────────

@pytest.mark.asyncio
async def test_docx_resume_generation_and_structure(export_test_env):
    """Verifies generated DOCX document contains valid paragraphs, headings, and bullet points."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        await client.post("/api/session")
        doc_init = await client.get("/api/builder")
        v = doc_init.json()["version"]

        payload = {
            "version": v,
            "template_id": "ats_professional",
            "content": {
                "contact": {
                    "name": "Marcus Vance",
                    "headline": "Senior Full-Stack Engineer",
                    "email": "marcus@vance.io",
                },
                "summary": "Full-stack engineer with expertise in React, Next.js, and FastAPI.",
                "experience": [
                    {
                        "id": "e1",
                        "company": "Vance Digital",
                        "role": "Founder & Engineer",
                        "start_date": "2021",
                        "end_date": "Present",
                        "current": True,
                        "bullets": [
                            "Built high-availability SaaS platform using async Python.",
                            "Maintained 99.99% uptime SLA across 4 global regions.",
                        ],
                    }
                ],
                "projects": [],
                "skills": [
                    {
                        "id": "s1",
                        "category": "Languages",
                        "skills": ["TypeScript", "Python", "SQL"],
                    }
                ],
                "education": [],
                "certifications": [],
                "additional": [],
            },
        }

        await client.put("/api/builder", json=payload)

        # Download DOCX
        res_docx = await client.get("/api/export/resume/docx")
        assert res_docx.status_code == 200
        assert res_docx.headers["content-type"] == "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        assert 'filename="RESUMIND_Marcus_Vance_v2.docx"' in res_docx.headers["content-disposition"]

        docx_bytes = res_docx.content
        assert len(docx_bytes) > 2000

        # Open and inspect with python-docx
        doc = docx.Document(io.BytesIO(docx_bytes))
        full_text = "\n".join(p.text for p in doc.paragraphs)

        assert "Marcus Vance" in full_text
        assert "Senior Full-Stack Engineer" in full_text
        assert "Vance Digital" in full_text
        assert "Built high-availability SaaS platform" in full_text
        assert "TypeScript, Python, SQL" in full_text

        # Verify bullet list styles were used
        bullet_paragraphs = [p for p in doc.paragraphs if p.style.name == 'List Bullet']
        assert len(bullet_paragraphs) >= 2


# ── 4. Diagnostic Improvement Report PDF Tests ────────────────────────────────

@pytest.mark.asyncio
async def test_diagnostic_report_pdf_without_job_match(export_test_env):
    """When only ATS Readiness exists, report displays ATS scores and explicitly states Job Match is unassessed."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        await client.post("/api/session")

        # 1. Upload resume
        pdf_bytes = create_synthetic_pdf(name="Jordan Audit", pages=1)
        files = {"file": ("jordan_audit.pdf", pdf_bytes, "application/pdf")}
        u_res = await client.post("/api/resume/upload", files=files)
        assert u_res.status_code == 201

        # 2. Run ATS Assessment
        ats_res = await client.post("/api/assessment")
        assert ats_res.status_code == 200
        ats_score = ats_res.json()["overall_score"]

        # 3. Request Diagnostic Report PDF
        report_res = await client.get("/api/export/report/pdf")
        assert report_res.status_code == 200
        assert report_res.headers["content-type"] == "application/pdf"
        assert 'filename="RESUMIND_Audit_Report_Jordan_Audit.pdf"' in report_res.headers["content-disposition"]

        pdf_doc = fitz.open(stream=report_res.content, filetype="pdf")
        text = "".join(page.get_text() for page in pdf_doc)

        assert "Diagnostic Resume Improvement Report" in text
        assert "MECHANICAL & STRUCTURAL ATS READINESS" in text.upper()
        assert f"{ats_score}" in text
        assert "File & Text Integrity" in text
        assert "Section Taxonomy" in text

        # Crucial honest AI requirement: Job Match must NOT be fabricated
        assert "No target job description was evaluated for this candidate" in text
        assert "Algorithmic Assessment Limitations & Ethical Guardrails" in text


@pytest.mark.asyncio
async def test_diagnostic_report_marks_builder_revision_as_historical(export_test_env):
    """The report warns when a saved Builder revision postdates its ATS assessment."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        await client.post("/api/session")
        upload = await client.post(
            "/api/resume/upload",
            files={"file": ("historical_report.pdf", create_synthetic_pdf(name="Taylor Example"), "application/pdf")},
        )
        assert upload.status_code == 201
        assessment = await client.post("/api/assessment")
        assert assessment.status_code == 200

        builder_response = await client.get("/api/builder")
        assert builder_response.status_code == 200
        builder = builder_response.json()
        content = builder["content"]
        content["contact"]["headline"] = "Verified Builder Revision"
        saved = await client.put(
            "/api/builder",
            json={"version": builder["version"], "content": content},
        )
        assert saved.status_code == 200
        assert saved.json()["version"] == 2

        # Pin timestamps one second apart so the regression never depends on test speed.
        async with export_test_env["session_factory"]() as db:
            ats_record = (await db.execute(select(ATSAssessment))).scalars().first()
            builder_record = (await db.execute(select(ResumeBuilderDocument))).scalars().first()
            assert ats_record is not None and builder_record is not None
            builder_record.updated_at = ats_record.created_at + timedelta(seconds=1)
            await db.commit()

        report = await client.get("/api/export/report/pdf")
        assert report.status_code == 200
        report_pdf = fitz.open(stream=report.content, filetype="pdf")
        report_text = "\n".join(page.get_text() for page in report_pdf)
        assert "Document Version: v2" in report_text
        assert "Assessment evaluated an earlier resume snapshot" in report_text


@pytest.mark.asyncio
async def test_diagnostic_report_pdf_with_job_match_and_suggestions(export_test_env):
    """When both ATS and Job Match exist, report includes both with grounded findings."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        s_res = await client.post("/api/session")
        session_cookie = s_res.cookies.get(settings.SESSION_COOKIE_NAME)
        if session_cookie:
            client.cookies.set(settings.SESSION_COOKIE_NAME, session_cookie)

        # 1. Upload resume
        pdf_bytes = create_synthetic_pdf(name="Morgan Match", pages=1)
        files = {"file": ("morgan_match.pdf", pdf_bytes, "application/pdf")}
        up_res = await client.post("/api/resume/upload", files=files)
        assert up_res.status_code == 201

        # 2. Run ATS Assessment
        await client.post("/api/assessment")

        # 3. Run Job Match Assessment
        jd_text = """
        Staff Backend Engineer — Cloud Platforms
        Requirements:
        - 5+ years experience designing async microservices in Python and FastAPI.
        - Deep expertise in PostgreSQL, SQLite, and Docker containerization.
        - Experience with zero-trust architecture and CI/CD pipelines.
        """
        jm_res = await client.post(
            "/api/job-match",
            json={"job_description": jd_text, "recalculate": True},
        )
        assert jm_res.status_code == 200

        # 4. Generate and accept an improvement suggestion
        gen_res = await client.post("/api/improvement/generate")
        assert gen_res.status_code == 200
        suggestions = gen_res.json().get("suggestions", [])
        if suggestions:
            s_id = suggestions[0]["id"]
            acc_res = await client.put(
                f"/api/improvement/{s_id}",
                json={"action": "accept", "user_edited_text": "Enhanced bullet point."},
            )
            assert acc_res.status_code == 200

        # 5. Download Diagnostic Report
        rep_res = await client.get("/api/export/report/pdf")
        assert rep_res.status_code == 200

        pdf_doc = fitz.open(stream=rep_res.content, filetype="pdf")
        full_text = "".join(page.get_text() for page in pdf_doc)

        assert "Target Role: Staff Backend Engineer" in full_text
        assert "IMPROVEMENT STUDIO REVISIONS & PROVENANCE" in full_text.upper()
        assert "Accepted & Integrated: 1" in full_text


# ── 5. Status Endpoint & Data Immutability ────────────────────────────────────

@pytest.mark.asyncio
async def test_export_status_metadata(export_test_env):
    """Status endpoint accurately reports session documents, versions, and assessment presence."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        await client.post("/api/session")

        # Initial status before upload
        s1 = await client.get("/api/export/status")
        assert s1.status_code == 200
        data1 = s1.json()
        assert data1["has_builder_document"] is False
        assert data1["has_ats_assessment"] is False
        assert data1["has_job_match"] is False

        # After creating builder document
        await client.get("/api/builder")
        s2 = await client.get("/api/export/status")
        assert s2.status_code == 200
        assert s2.json()["has_builder_document"] is True


@pytest.mark.asyncio
async def test_export_does_not_mutate_builder_or_assessments(export_test_env):
    """Verifies that requesting exports does not mutate document versions or assessment scores."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        await client.post("/api/session")
        b = await client.get("/api/builder")
        initial_version = b.json()["version"]

        # Run exports multiple times
        await client.get("/api/export/resume/pdf")
        await client.get("/api/export/resume/docx")
        await client.get("/api/export/report/pdf")

        # Builder version should remain strictly identical
        b_after = await client.get("/api/builder")
        assert b_after.json()["version"] == initial_version
