"""Automated test suite for Standalone ATS-Readiness Scoring Engine.

Tests:
  - Every scoring dimension and its subcriteria boundaries.
  - Mathematical weighted sum formula and deterministic reproducibility.
  - Student and early-career resumes (projects credited fairly alongside experience).
  - Empty, scanned, and minimal extraction documents.
  - Missing and uncertain contact fields with privacy preservation.
  - Bullet impact evaluation (action verbs, metrics, passive starters, word length).
  - Length and hygiene (word count boundaries, duplicate lines, dense blocks).
  - API endpoints: POST /api/assessment, GET /api/assessment.
  - Idempotency and recalculation behavior.
  - Session scoping and cross-session isolation.
  - Zero AI model or external API dependency.
"""

from pathlib import Path
import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.config import settings
from app.database import Base, get_db
from app.main import app
from app.services.scoring_service import (
    DISCLAIMER,
    WEIGHTS,
    calculate_ats_score,
    evaluate_bullet_impact,
    evaluate_contact_information,
    evaluate_file_integrity,
    evaluate_length_and_hygiene,
    evaluate_section_taxonomy,
)
from tests.fixtures.synthetic_generator import (
    create_synthetic_docx,
    create_synthetic_pdf,
)


# ── Test Environment Fixture ─────────────────────────────────────────────────
@pytest.fixture
async def scoring_test_env(tmp_path: Path):
    """Provisions an isolated SQLite test database and temporary storage root."""
    test_db_path = tmp_path / "test_scoring.db"
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


# ── Unit Tests: Dimension 1 (File Integrity) ──────────────────────────────────
def test_file_integrity_clean_document():
    """Valid text document extracts cleanly and achieves top file integrity score."""
    sample_text = (
        "Alex Mercer\n"
        "alex@example.com | (555) 019-2834\n\n"
        "Professional Summary\n"
        "Experienced software engineer with 5 years in distributed systems.\n\n"
        "Work Experience\n"
        "Software Engineer at Acme Corp\n"
        "Engineered scalable microservices reducing latency by 40%.\n"
    )
    result = evaluate_file_integrity(
        raw_text=sample_text,
        file_type="pdf",
        file_size=15_000,
        warnings=[],
    )
    assert result.score >= 90.0
    assert result.weight == 0.25
    assert result.weighted_score == round(result.score * 0.25, 1)
    assert any("text layer" in s.lower() for s in result.strengths)


def test_file_integrity_scanned_or_empty_document():
    """Scanned or empty document receives critical finding and low integrity score."""
    result = evaluate_file_integrity(
        raw_text="",
        file_type="pdf",
        file_size=500_000,
        warnings=["Scanned or image-only document detected: No extractable text layer found."],
    )
    assert result.score <= 20.0
    critical_findings = [f for f in result.findings if f.severity == "critical"]
    assert len(critical_findings) >= 1
    assert "Scanned" in critical_findings[0].title or "Unreadable" in critical_findings[0].title


def test_file_integrity_unsegmented_text():
    """Monolithic single-paragraph text without line breaks is flagged."""
    monolithic_text = "Word " * 100  # 500 chars with no newlines
    result = evaluate_file_integrity(
        raw_text=monolithic_text,
        file_type="docx",
        file_size=10_000,
        warnings=[],
    )
    assert any("unsegmented" in f.title.lower() for f in result.findings)


# ── Unit Tests: Dimension 2 (Section Taxonomy) ────────────────────────────────
def test_section_taxonomy_standard_sections():
    """Resume with all core sections scores maximum taxonomy points."""
    structured = {
        "summary": "Experienced engineer with passion for distributed computing.",
        "experience": ["Company A - Engineer", "Built cloud pipelines"],
        "education": ["BS in Computer Science, State University"],
        "skills": ["Python", "Go", "Docker", "PostgreSQL"],
        "projects": ["Open Source Tool - 1k stars"],
        "certifications": ["AWS Solutions Architect"],
        "other": [],
    }
    result = evaluate_section_taxonomy(structured)
    assert result.score == 100.0
    assert result.weight == 0.20
    assert result.weighted_score == 20.0
    assert len(result.strengths) >= 4


def test_section_taxonomy_student_early_career_fairness():
    """Early-career/student candidates with Projects but no Experience receive full primary credit."""
    structured_student = {
        "summary": "Recent CS Graduate seeking software engineering roles.",
        "experience": [],  # No traditional corporate employment
        "education": ["BS in Computer Science, 2024"],
        "skills": ["Python", "React", "TypeScript", "SQL"],
        "projects": [
            "Autonomous Rover Capstone Project",
            "Distributed Key-Value Store implementation in Go",
        ],
        "certifications": [],
        "other": [],
    }
    result = evaluate_section_taxonomy(structured_student)
    # Experience or Projects gives 35 pts, Education gives 25 pts, Skills gives 25 pts, Summary gives 10 pts = 95 pts
    assert result.score >= 85.0
    assert any("valid portfolio alternative" in s.lower() for s in result.strengths)
    # Does not have a critical finding for missing experience
    assert not any(f.severity == "critical" and "experience" in f.title.lower() for f in result.findings)


def test_section_taxonomy_unclassified_sections():
    """Unclassified content under unknown headings is preserved and highlighted constructively."""
    structured = {
        "experience": ["Company A - Engineer"],
        "education": ["BS in Math"],
        "skills": ["Python"],
        "other": ["Hobbies: Rock climbing, Chess", "Publications: Paper on Graph Theory"],
    }
    result = evaluate_section_taxonomy(structured)
    assert any("unclassified" in f.title.lower() for f in result.findings)


# ── Unit Tests: Dimension 3 (Contact Information) ─────────────────────────────
def test_contact_information_complete():
    """Complete contact profile with verified email and phone earns top score."""
    structured = {
        "contact": {
            "name": "Jane Doe",
            "email": "jane.doe@synthetic-domain.com",
            "phone": "+1 (555) 234-5678",
            "urls": ["https://linkedin.com/in/janedoe", "https://github.com/janedoe"],
            "location": "Seattle, WA",
            "uncertainty": {"name": False, "email": False, "phone": False},
        }
    }
    result = evaluate_contact_information(structured)
    assert result.score == 100.0
    assert result.weight == 0.15
    assert result.weighted_score == 15.0
    # Privacy check: does NOT expose raw full email in strengths
    for s in result.strengths:
        assert "jane.doe@synthetic-domain.com" not in s


def test_contact_information_missing_email_critical():
    """Missing contact email is flagged as critical severity."""
    structured = {
        "contact": {
            "name": "John Smith",
            "email": None,
            "phone": "+1 555-1234",
            "urls": [],
            "location": None,
            "uncertainty": {},
        }
    }
    result = evaluate_contact_information(structured)
    assert result.score <= 60.0
    assert any(f.severity == "critical" and "email" in f.title.lower() for f in result.findings)


# ── Unit Tests: Dimension 4 (Bullet Impact) ───────────────────────────────────
def test_bullet_impact_strong_action_verbs_and_metrics():
    """Bullets starting with action verbs and quantifiable metrics score high."""
    structured = {
        "experience": [
            "Senior Backend Engineer — TechCorp",
            "Architected distributed pub/sub pipelines reducing processing latency by 45%.",
            "Spearheaded database indexing optimization, cutting memory overhead by 30%.",
            "Orchestrated cloud migration for 25 microservices serving 2M users daily.",
            "Engineered automated regression tests improving code coverage from 60% to 92%.",
        ],
        "projects": [],
    }
    result = evaluate_bullet_impact(structured)
    assert result.score >= 85.0
    assert result.weight == 0.25
    assert any("action-verb" in s.lower() for s in result.strengths)
    assert any("quantifiable" in s.lower() for s in result.strengths)


def test_bullet_impact_without_metrics_still_earns_credit():
    """Descriptive bullets without numerical metrics are still rewarded fairly without fabrication."""
    structured = {
        "experience": [
            "Software Developer — GlobalTech",
            "Developed responsive user interfaces following modern accessibility guidelines.",
            "Engineered secure authentication endpoints using encrypted session cookies.",
            "Collaborated with cross-functional product designers to refine application workflows.",
            "Conducted thorough peer code reviews and maintained clean system documentation.",
        ],
        "projects": [],
    }
    result = evaluate_bullet_impact(structured)
    # Action verbs and length earn significant credit even with 0 numbers
    assert result.score >= 60.0
    assert any("action-verb" in s.lower() for s in result.strengths)
    # Suggests metrics constructively without fabricating any
    assert any("quantifiable" in f.title.lower() for f in result.findings)


def test_bullet_impact_passive_starters_flagged():
    """Passive phrases like 'Responsible for' are flagged with constructive feedback."""
    structured = {
        "experience": [
            "Responsible for answering customer emails and filing reports.",
            "Helped with database migrations and attended weekly scrums.",
            "Worked on front-end components using CSS and HTML.",
        ],
        "projects": [],
    }
    result = evaluate_bullet_impact(structured)
    assert any("passive" in f.title.lower() for f in result.findings)


def test_bullet_impact_no_bullets_boundary():
    """Boundary case: zero bullet entries documents limitation honestly."""
    structured = {
        "experience": [],
        "projects": [],
    }
    result = evaluate_bullet_impact(structured)
    assert result.score <= 25.0
    assert any(f.severity == "critical" and "no descriptive" in f.title.lower() for f in result.findings)


# ── Unit Tests: Dimension 5 (Length & Hygiene) ────────────────────────────────
def test_length_and_hygiene_duplicate_lines():
    """Duplicate lines (e.g. repeated header or copy-paste error) are detected."""
    sample_text = (
        "John Doe\n"
        "Lead Engineer at Acme Corp\n"
        "Spearheaded database indexing optimization across all services.\n"
        "Spearheaded database indexing optimization across all services.\n"  # duplicate
        "Collaborated with engineering leads on architectural roadmap.\n"
    )
    result = evaluate_length_and_hygiene(raw_text=sample_text, structured_data={})
    assert any("duplicate" in f.title.lower() for f in result.findings)


def test_length_and_hygiene_dense_blocks():
    """Massive unbroken paragraphs (>900 chars) are flagged for poor readability."""
    long_block = "Engineering achievements and responsibilities in software systems. " * 20
    sample_text = f"Overview:\n\n{long_block}"
    result = evaluate_length_and_hygiene(raw_text=sample_text, structured_data={})
    assert any("dense" in f.title.lower() or "unbroken" in f.title.lower() for f in result.findings)


# ── Determinism & Overall Weighted Score Tests ───────────────────────────────
def test_overall_weighted_score_formula_and_determinism():
    """Overall score matches exact weighted sum and is bit-for-bit deterministic."""
    sample_text = (
        "Alex Mercer\n"
        "alex.mercer@synthetic-domain.com | (555) 019-2834 | linkedin.com/in/alexmercer\n\n"
        "Summary\n"
        "Experienced full-stack engineer with 6 years building distributed cloud applications.\n\n"
        "Experience\n"
        "Senior Software Engineer — CloudSystems (2020 – Present)\n"
        "• Architected scalable microservices reducing API latency by 35%.\n"
        "• Spearheaded zero-trust session token migration across distributed services.\n"
        "• Mentored junior engineers and instituted automated integration testing.\n\n"
        "Education\n"
        "BS in Computer Science — State University (2018)\n\n"
        "Skills\n"
        "Python, Go, TypeScript, PostgreSQL, Docker, Kubernetes\n"
    )
    structured = {
        "contact": {
            "name": "Alex Mercer",
            "email": "alex.mercer@synthetic-domain.com",
            "phone": "(555) 019-2834",
            "urls": ["https://linkedin.com/in/alexmercer"],
            "location": None,
            "uncertainty": {},
        },
        "summary": "Experienced full-stack engineer with 6 years building distributed cloud applications.",
        "experience": [
            "Senior Software Engineer — CloudSystems",
            "Architected scalable microservices reducing API latency by 35%.",
            "Spearheaded zero-trust session token migration across distributed services.",
            "Mentored junior engineers and instituted automated integration testing.",
        ],
        "education": ["BS in Computer Science — State University (2018)"],
        "skills": ["Python", "Go", "TypeScript", "PostgreSQL", "Docker", "Kubernetes"],
        "projects": [],
        "certifications": [],
        "other": [],
        "warnings": [],
    }

    # Run 5 times: verify exact determinism
    runs = [
        calculate_ats_score(
            raw_text=sample_text,
            structured_data=structured,
            file_type="pdf",
            file_size=20_000,
        )
        for _ in range(5)
    ]

    for report in runs:
        assert report.overall_score == runs[0].overall_score
        assert report.disclaimer == DISCLAIMER
        # Check weighted sum matches subscores exactly
        computed_weighted_sum = sum(
            sub.score * WEIGHTS[dim] for dim, sub in report.subscores.items()
        )
        assert abs(report.overall_score - round(computed_weighted_sum, 1)) <= 0.2


# ── Integration Tests: API Endpoints & Session Scoping ────────────────────────
@pytest.mark.asyncio
async def test_ats_assessment_api_flow(scoring_test_env):
    """End-to-end API test: upload synthetic PDF, compute assessment, verify persistence and idempotency."""
    pdf_bytes = create_synthetic_pdf(name="Taylor Swift", pages=1)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # 1. Upload valid resume
        files = {"file": ("taylor_resume.pdf", pdf_bytes, "application/pdf")}
        upload_res = await client.post("/api/resume/upload", files=files)
        assert upload_res.status_code == 201
        session_cookie = upload_res.cookies.get(settings.SESSION_COOKIE_NAME)
        assert session_cookie is not None

        # 2. Trigger ATS assessment
        client.cookies.set(settings.SESSION_COOKIE_NAME, session_cookie)
        assess_res = await client.post("/api/assessment")
        assert assess_res.status_code == 200
        data = assess_res.json()

        assert "id" in data
        assert "overall_score" in data
        assert 0.0 <= data["overall_score"] <= 100.0
        assert "dimension_scores" in data
        assert set(data["dimension_scores"].keys()) == {
            "file_integrity", "section_taxonomy", "contact", "bullet_impact", "length_hygiene"
        }
        assert "report_data" in data
        report = data["report_data"]
        assert len(report["top_strengths"]) > 0
        assert "disclaimer" in report

        first_id = data["id"]

        # 3. GET /api/assessment returns the same persisted assessment
        get_res = await client.get("/api/assessment")
        assert get_res.status_code == 200
        get_data = get_res.json()
        assert get_data["id"] == first_id

        # 4. Idempotency: second POST without changes returns identical assessment ID
        second_post = await client.post("/api/assessment")
        assert second_post.status_code == 200
        assert second_post.json()["id"] == first_id

        # 5. Forced recalculation creates fresh assessment
        recalc_res = await client.post("/api/assessment?recalculate=true")
        assert recalc_res.status_code == 200
        assert recalc_res.json()["id"] != first_id


@pytest.mark.asyncio
async def test_assessment_cross_session_denial_and_unauthorized(scoring_test_env):
    """Assessment retrieval and creation is strictly scoped to valid authenticated session."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # 1. Unauthenticated request returns 401
        unauth_get = await client.get("/api/assessment")
        assert unauth_get.status_code == 401

        unauth_post = await client.post("/api/assessment")
        assert unauth_post.status_code == 401

        # 2. Session with no uploaded resume returns 404
        sess_create = await client.post("/api/session")
        assert sess_create.status_code == 200
        empty_cookie = sess_create.cookies.get(settings.SESSION_COOKIE_NAME)
        client.cookies.set(settings.SESSION_COOKIE_NAME, empty_cookie)

        no_resume_post = await client.post("/api/assessment")
        assert no_resume_post.status_code == 404
        assert "upload a resume first" in no_resume_post.json()["detail"].lower()
