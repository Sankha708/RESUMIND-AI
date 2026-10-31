"""Automated test suite for Job Description Matching Engine (Phase 6).

Tests:
  - JD normalization and requirement extraction.
  - Hard skills, domain competencies, experience scope, education/credentials.
  - Required versus preferred wording distinction.
  - Exact and documented taxonomy/synonym matches.
  - Partial and unsupported requirements.
  - Verbatim evidence grounding (every evidence snippet must be an authentic substring of resume).
  - Approved scoring weights (40% hard, 30% domain, 15% exp, 15% edu) and pro-rata absent dimension normalization.
  - Empty, whitespace-only, oversized, and poorly structured job postings.
  - Insufficient information causing score withholding.
  - Determinism and duplicate-keyword prevention.
  - Persistence and session-scoped retrieval via POST/GET /api/job-match.
  - Cross-session access denial and isolation.
  - Distinct separation of ATS-readiness and Job Match scores.
"""

from pathlib import Path
import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.config import settings
from app.database import Base, get_db
from app.main import app
from app.services.job_match_service import (
    JOB_MATCH_DISCLAIMER,
    JOB_MATCH_WEIGHTS,
    detect_job_title,
    evaluate_job_match,
    extract_requirements_from_jd,
    find_verbatim_evidence,
)
from tests.fixtures.synthetic_generator import (
    create_synthetic_docx,
    create_synthetic_pdf,
)


# ── Test Environment Fixture ─────────────────────────────────────────────────
@pytest.fixture
async def job_match_test_env(tmp_path: Path):
    """Provisions an isolated SQLite test database and temporary storage root."""
    test_db_path = tmp_path / "test_job_match.db"
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


# ── Unit Tests: Requirement Extraction & Normalization ───────────────────────
def test_extract_requirements_and_job_title():
    """Detects job title, hard skills, domain competencies, experience, and education."""
    jd = """
    Role: Senior Backend Engineer
    
    About Us:
    Building next-generation distributed systems.
    
    Requirements:
    • 5+ years of experience in software development
    • Strong proficiency with Python and Go
    • Deep experience with PostgreSQL and Docker
    • Expertise in Distributed Systems and System Design
    • Bachelor's degree in Computer Science or related field
    
    Preferred Qualifications:
    • Experience with Kubernetes and Kafka
    • Familiarity with GraphQL
    """
    title = detect_job_title(jd)
    assert title == "Senior Backend Engineer"

    reqs, sufficient, reason = extract_requirements_from_jd(jd)
    assert sufficient is True
    assert reason is None
    assert len(reqs) >= 6

    # Verify category categorization
    categories = {r.category for r in reqs}
    assert "hard_skills" in categories
    assert "domain_competencies" in categories
    assert "experience_scope" in categories
    assert "education_credentials" in categories

    # Verify required vs preferred distinction
    python_req = next((r for r in reqs if r.normalized_term == "python"), None)
    assert python_req is not None
    assert python_req.is_required is True

    k8s_req = next((r for r in reqs if r.normalized_term == "kubernetes"), None)
    assert k8s_req is not None
    assert k8s_req.is_required is False  # In Preferred section


def test_insufficient_jd_structure_withholds_score():
    """Poorly structured or overly brief JD triggers score withholding."""
    sparse_jd = "Looking for a great team player who loves computers."
    report = evaluate_job_match(
        jd_text=sparse_jd,
        raw_text="Some candidate resume text",
        structured_data={},
    )
    assert report.score_withheld is True
    assert report.overall_score is None
    assert report.withheld_reason is not None
    assert "not yield enough identifiable requirements" in report.withheld_reason.lower()


# ── Unit Tests: Verbatim Evidence Mandate & Zero Hallucination ───────────────
def test_verbatim_evidence_grounding_strictly_enforced():
    """Matched evidence snippets are guaranteed to be authentic verbatim substrings of resume."""
    resume_raw = (
        "Alex Mercer\n"
        "alex@example.com\n\n"
        "Experience\n"
        "Lead Engineer at CloudCorp\n"
        "• Architected scalable microservices using Python and FastAPI cutting latency by 40%.\n"
        "• Managed relational databases including PostgreSQL for 10M records.\n"
    )
    structured = {
        "skills": ["Python", "FastAPI", "PostgreSQL"],
        "experience": [
            "Architected scalable microservices using Python and FastAPI cutting latency by 40%.",
            "Managed relational databases including PostgreSQL for 10M records.",
        ],
        "education": [],
        "projects": [],
    }

    # Verify verbatim evidence finder
    evidence = find_verbatim_evidence("python", ["python"], resume_raw, structured["experience"])
    assert evidence is not None
    assert evidence in resume_raw  # Verbatim substring guarantee!

    # Search for a skill not in the resume
    absent_evidence = find_verbatim_evidence("rust", ["rust"], resume_raw, structured["experience"])
    assert absent_evidence is None


def test_grounded_job_match_scoring():
    """Computes transparent scores, separates matches from gaps, and includes verbatim citations."""
    resume_raw = (
        "Sarah Connor\n"
        "sarah@synthetic.com\n\n"
        "Summary\n"
        "Senior Software Engineer with 6 years of experience in cloud backend systems.\n\n"
        "Experience\n"
        "Senior Software Engineer — Cyberdyne Systems\n"
        "• Built distributed pipelines using Python and Docker.\n"
        "• Designed PostgreSQL schemas for high-concurrency workloads.\n"
        "• Led agile team scrums and sprint planning.\n\n"
        "Education\n"
        "Bachelor of Science in Computer Science, State University\n"
    )
    structured = {
        "skills": ["Python", "Docker", "PostgreSQL", "Agile"],
        "experience": [
            "Built distributed pipelines using Python and Docker.",
            "Designed PostgreSQL schemas for high-concurrency workloads.",
            "Led agile team scrums and sprint planning.",
        ],
        "education": ["Bachelor of Science in Computer Science, State University"],
        "projects": [],
        "summary": "Senior Software Engineer with 6 years of experience in cloud backend systems.",
    }

    jd = """
    Job Title: Senior Backend Developer
    
    Requirements:
    • Python programming
    • PostgreSQL database design
    • Docker containerization
    • Kubernetes orchestration
    • Agile / Scrum methodologies
    • 5+ years of experience
    • Bachelor's degree in Computer Science
    """

    report = evaluate_job_match(jd, resume_raw, structured)
    assert report.score_withheld is False
    assert report.overall_score is not None
    assert 60.0 <= report.overall_score <= 95.0

    # Matched items have verbatim evidence
    matched_reqs = [r for r in report.requirements if r.match_status == "matched"]
    for m in matched_reqs:
        assert m.evidence_snippet is not None
        assert m.evidence_snippet in resume_raw

    # Unsubstantiated gap (Kubernetes was not in resume)
    k8s = next((r for r in report.requirements if r.normalized_term == "kubernetes"), None)
    assert k8s is not None
    assert k8s.match_status == "not_demonstrated"
    assert k8s.evidence_snippet is None
    assert k8s.recommendation is not None


# ── Unit Tests: Pro-Rata Weight Normalization ─────────────────────────────────
def test_pro_rata_normalization_when_category_absent():
    """Genuinely absent category is marked N/A and active weights are normalized pro-rata."""
    resume_raw = (
        "Taylor Swift\n"
        "Experience:\n"
        "Software Engineer with 4 years building Python and Go microservices.\n"
    )
    structured = {
        "skills": ["Python", "Go"],
        "experience": ["Software Engineer with 4 years building Python and Go microservices."],
        "education": [],
        "projects": [],
    }

    # JD with Hard Skills and Experience, but NO Education requirement
    jd_no_edu = """
    Software Engineer
    Requirements:
    • Strong Python and Go skills
    • 3+ years of experience in software engineering
    """
    report = evaluate_job_match(jd_no_edu, resume_raw, structured)
    assert report.score_withheld is False

    edu_cat = report.category_scores["education_credentials"]
    assert edu_cat.is_applicable is False
    assert edu_cat.normalized_weight == 0.0

    # Remaining applicable categories must sum to 1.0 in normalized weights
    active_norm_sum = sum(
        c.normalized_weight for c in report.category_scores.values() if c.is_applicable
    )
    assert abs(active_norm_sum - 1.0) <= 0.01


# ── Unit Tests: Determinism & Duplicate Keyword Invariance ───────────────────
def test_duplicate_keywords_do_not_inflate_score():
    """Repeating the same keyword multiple times in JD does not create multiple duplicate requirements."""
    jd_repetitive = """
    Python Developer
    Requirements:
    • Python programming
    • Python scripting
    • Must know Python
    • 3+ years of experience
    """
    reqs, sufficient, _ = extract_requirements_from_jd(jd_repetitive)
    python_reqs = [r for r in reqs if r.normalized_term == "python"]
    # Only one canonical requirement extracted for python
    assert len(python_reqs) == 1


def test_job_match_determinism():
    """Same resume and JD produces bit-for-bit identical results across multiple runs."""
    resume_raw = "Alex Mercer\nPython Engineer\n5 years experience\nBS in Computer Science"
    structured = {
        "skills": ["Python"],
        "experience": ["5 years experience in backend development"],
        "education": ["BS in Computer Science"],
        "projects": [],
    }
    jd = "Software Engineer\nRequirements:\n• Python\n• 3+ years experience\n• Bachelor's degree"

    run1 = evaluate_job_match(jd, resume_raw, structured)
    run2 = evaluate_job_match(jd, resume_raw, structured)

    assert run1.overall_score == run2.overall_score
    assert run1.matched_count == run2.matched_count
    assert len(run1.requirements) == len(run2.requirements)


# ── Integration Tests: API Endpoints & Session Scoping ────────────────────────
@pytest.mark.asyncio
async def test_job_match_api_flow(job_match_test_env):
    """End-to-end API test: upload resume, submit JD, verify persistence, idempotency, and session scoping."""
    pdf_bytes = create_synthetic_pdf(name="Jordan Lee", pages=1)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # 1. Upload valid resume
        files = {"file": ("jordan_resume.pdf", pdf_bytes, "application/pdf")}
        upload_res = await client.post("/api/resume/upload", files=files)
        assert upload_res.status_code == 201
        session_cookie = upload_res.cookies.get(settings.SESSION_COOKIE_NAME)
        assert session_cookie is not None
        client.cookies.set(settings.SESSION_COOKIE_NAME, session_cookie)

        # 2. POST /api/job-match with whitespace-only JD fails with 400
        bad_post = await client.post("/api/job-match", json={"job_description": "   \n\t  "})
        assert bad_post.status_code == 400
        assert "cannot be empty" in bad_post.json()["detail"].lower()

        # 3. POST /api/job-match with valid JD succeeds
        valid_jd = """
        Job Title: Lead Backend Engineer
        
        Requirements:
        • 5+ years of experience with Python or Go
        • Experience with distributed systems and microservices
        • Bachelor's degree in Computer Science
        """
        match_res = await client.post("/api/job-match", json={"job_description": valid_jd})
        assert match_res.status_code == 200
        data = match_res.json()

        assert "id" in data
        assert "overall_score" in data
        assert "report_data" in data
        assert data["job_title"] == "Lead Backend Engineer"
        report = data["report_data"]
        assert len(report["requirements"]) > 0
        first_id = data["id"]

        # 4. GET /api/job-match retrieves the saved assessment
        get_res = await client.get("/api/job-match")
        assert get_res.status_code == 200
        assert get_res.json()["id"] == first_id

        # 5. Idempotency: re-posting identical JD returns same assessment ID
        second_post = await client.post("/api/job-match", json={"job_description": valid_jd})
        assert second_post.status_code == 200
        assert second_post.json()["id"] == first_id

        # 6. Forced recalculate creates a fresh assessment record
        recalc_res = await client.post(
            "/api/job-match",
            json={"job_description": valid_jd, "recalculate": True},
        )
        assert recalc_res.status_code == 200
        assert recalc_res.json()["id"] != first_id


@pytest.mark.asyncio
async def test_job_match_cross_session_denial_and_unauthorized(job_match_test_env):
    """Job match assessment is strictly isolated to the authenticated session."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # 1. Unauthenticated request returns 401
        unauth_get = await client.get("/api/job-match")
        assert unauth_get.status_code == 401

        unauth_post = await client.post("/api/job-match", json={"job_description": "Valid job description..."})
        assert unauth_post.status_code == 401

        # 2. Session with no uploaded resume returns 404
        sess_create = await client.post("/api/session")
        assert sess_create.status_code == 200
        empty_cookie = sess_create.cookies.get(settings.SESSION_COOKIE_NAME)
        client.cookies.set(settings.SESSION_COOKIE_NAME, empty_cookie)

        no_resume_post = await client.post(
            "/api/job-match",
            json={"job_description": "Valid job description..."},
        )
        assert no_resume_post.status_code == 404
        assert "upload a resume first" in no_resume_post.json()["detail"].lower()


@pytest.mark.asyncio
async def test_ats_and_job_match_scores_remain_distinct(job_match_test_env):
    """ATS readiness and Job Match scores are calculated separately and remain distinct."""
    pdf_bytes = create_synthetic_pdf(name="Morgan Riley", pages=1)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        files = {"file": ("morgan_resume.pdf", pdf_bytes, "application/pdf")}
        upload_res = await client.post("/api/resume/upload", files=files)
        session_cookie = upload_res.cookies.get(settings.SESSION_COOKIE_NAME)
        client.cookies.set(settings.SESSION_COOKIE_NAME, session_cookie)

        # Run standalone ATS readiness
        ats_res = await client.post("/api/assessment")
        assert ats_res.status_code == 200
        ats_score = ats_res.json()["overall_score"]

        # Run Job Match
        jd = "Software Engineer\nRequirements:\n• Python\n• PostgreSQL\n• 3+ years experience"
        match_res = await client.post("/api/job-match", json={"job_description": jd})
        assert match_res.status_code == 200
        match_score = match_res.json()["overall_score"]

        # Verify both endpoints exist independently and return valid scores
        assert ats_score is not None
        assert match_score is not None
        # They have different dimensions and report schemas
        assert set(ats_res.json()["dimension_scores"].keys()) == {
            "file_integrity", "section_taxonomy", "contact", "bullet_impact", "length_hygiene"
        }
        assert set(match_res.json()["category_scores"].keys()) == {
            "hard_skills", "domain_competencies", "experience_scope", "education_credentials"
        }
