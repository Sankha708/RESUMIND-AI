"""Phase 9 Tests — Resume Builder & Template Studio (Screen 6).

Tests cover:
- Session authorization & isolation.
- Auto-initialization from reviewed resume (with accepted improvements).
- Auto-initialization with empty starter profile when no resume uploaded.
- Adding, editing, and deleting repeatable entries (experience, projects, education, etc.).
- Reordering sections and toggling section visibility.
- Single ATS Professional template and no loss of candidate data.
- Monotonic version increment and optimistic concurrency protection (409 Conflict).
- Reset to reviewed resume or empty canvas.
- Verification that original uploaded resume and historical assessments are preserved unchanged.
"""

from pathlib import Path
import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.config import settings
from app.database import Base, get_db
from app.main import app
from app.models.assessment import ATSAssessment
from app.models.builder import ResumeBuilderDocument
from app.models.resume import UploadedResume
from app.services.builder_service import (
    convert_structured_profile_to_builder_content,
    create_blank_builder_content,
)
from tests.fixtures.synthetic_generator import create_synthetic_pdf


@pytest.fixture
async def builder_test_env(tmp_path: Path):
    """Provisions an isolated SQLite test database and temporary storage root."""
    test_db_path = tmp_path / "test_builder.db"
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


# ── Unit Tests: Service Layer ─────────────────────────────────────────────────

def test_create_blank_builder_content():
    """Blank starter contains empty fields and zero fabricated claims or metrics."""
    content = create_blank_builder_content()
    assert content.contact.name == ""
    assert content.contact.email == ""
    assert len(content.experience) == 0
    assert len(content.projects) == 0
    assert len(content.education) == 0
    assert len(content.certifications) == 0


def test_convert_structured_profile_to_builder_content():
    """Converts reviewed profile into rich builder repeatable entries."""
    structured = {
        "contact": {
            "name": "Sam Taylor",
            "email": "sam@example.com",
            "phone": "555-1234",
            "location": "Boston, MA",
            "urls": ["https://linkedin.com/in/samtaylor", "https://github.com/samtaylor"],
        },
        "summary": "Experienced software architect specializing in distributed services.",
        "experience": [
            "Senior Engineer at Tech Corp\nDesigned event-driven backend servicing 10M requests daily.",
            "Helped migrate monolith to Kubernetes microservices.",
        ],
        "projects": [
            "Distributed Cache: Built Redis-compatible caching engine in Rust.",
        ],
        "skills": ["Rust", "Python", "Docker", "PostgreSQL"],
        "education": ["B.S. in Computer Science, MIT, 2019"],
        "certifications": ["AWS Certified Solutions Architect"],
        "other": ["Published whitepaper on consensus protocols."],
    }

    content = convert_structured_profile_to_builder_content(structured)
    assert content.contact.name == "Sam Taylor"
    assert content.contact.email == "sam@example.com"
    assert "linkedin.com/in/samtaylor" in content.contact.linkedin
    assert "github.com/samtaylor" in content.contact.github
    assert len(content.experience) == 1
    assert content.experience[0].company == "Tech Corp"
    assert content.experience[0].role == "Senior Engineer"
    assert len(content.experience[0].bullets) == 2
    assert "10M requests daily" in content.experience[0].bullets[0]
    assert "Kubernetes microservices" in content.experience[0].bullets[1]
    assert len(content.projects) == 1
    assert content.projects[0].title == "Distributed Cache"
    assert len(content.skills) == 1
    assert "Rust" in content.skills[0].skills
    assert len(content.education) == 1
    assert len(content.certifications) == 1
    assert len(content.additional) == 1


def test_convert_pdf_parser_experience_with_middle_dot_separators():
    """Preserves roles and dates when PDF extraction represents dashes as middle dots."""
    structured = {
        "contact": {"name": "Samantha Reed"},
        "experience": [
            "Lead Backend Engineer · Nexus Systems (Jan 2021 · Present)",
            "· Architected async microservices reducing API latency by 35%.",
            "· Spearheaded zero-trust session token migration across distributed services.",
            "Software Engineer · CoreLogic Inc (Jun 2018 · Dec 2020)",
            "· Designed automated ETL pipelines processing 2M+ synthetic records daily.",
        ],
        "education": [f"B.S. in Computer Science {chr(0x00b7)} Pacific Crest University (2014 {chr(0x00b7)} 2018)"],
    }

    content = convert_structured_profile_to_builder_content(structured)

    assert len(content.experience) == 2
    assert content.experience[0].role == "Lead Backend Engineer"
    assert content.experience[0].company == "Nexus Systems"
    assert content.experience[0].start_date == "Jan 2021"
    assert content.experience[0].current is True
    assert content.experience[0].bullets == [
        "Architected async microservices reducing API latency by 35%.",
        "Spearheaded zero-trust session token migration across distributed services.",
    ]
    assert content.experience[1].role == "Software Engineer"
    assert content.experience[1].company == "CoreLogic Inc"
    assert content.experience[1].start_date == "Jun 2018"
    assert content.experience[1].end_date == "Dec 2020"
    assert len(content.education) == 1
    assert content.education[0].degree == "B.S. in Computer Science"
    assert content.education[0].institution == "Pacific Crest University"
    assert content.education[0].start_date == "2014"
    assert content.education[0].end_date == "2018"


# ── Integration Tests: API Endpoints ──────────────────────────────────────────

@pytest.mark.asyncio
async def test_get_builder_requires_session(builder_test_env):
    """Accessing builder without session cookie returns 401 Unauthorized."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/api/builder")
        assert resp.status_code == 401


@pytest.mark.asyncio
async def test_get_builder_initializes_empty_starter_when_no_resume(builder_test_env):
    """When a session has no uploaded resume, initializes a clean blank builder document."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Create session
        sess_resp = await client.post("/api/session")
        assert sess_resp.status_code == 200

        # Get builder
        builder_resp = await client.get("/api/builder")
        assert builder_resp.status_code == 200
        data = builder_resp.json()
        assert data["version"] == 1
        assert data["template_id"] == "ats_professional"
        assert data["source_resume_id"] is None
        assert data["content"]["contact"]["name"] == ""
        assert len(data["content"]["experience"]) == 0


@pytest.mark.asyncio
async def test_get_builder_initializes_from_reviewed_resume(builder_test_env):
    """When a session has a reviewed resume, seeds the builder from its verified content."""
    pdf_bytes = create_synthetic_pdf(name="Morgan Lee", pages=1)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Upload resume
        upload_resp = await client.post(
            "/api/resume/upload",
            files={"file": ("morgan_resume.pdf", pdf_bytes, "application/pdf")},
        )
        assert upload_resp.status_code == 201

        # Get builder document
        builder_resp = await client.get("/api/builder")
        assert builder_resp.status_code == 200
        data = builder_resp.json()
        assert data["version"] == 1
        assert data["source_resume_id"] is not None
        assert "Morgan Lee" in data["content"]["contact"]["name"]
        assert len(data["section_order"]) == 8
        assert data["section_visibility"]["experience"] is True


@pytest.mark.asyncio
async def test_update_builder_document_and_concurrency_control(builder_test_env):
    """Updates content, template, and verifies optimistic concurrency protection."""
    pdf_bytes = create_synthetic_pdf(name="Alex Rivera", pages=1)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        await client.post(
            "/api/resume/upload",
            files={"file": ("alex_resume.pdf", pdf_bytes, "application/pdf")},
        )

        doc1 = (await client.get("/api/builder")).json()
        assert doc1["version"] == 1
        assert doc1["template_id"] == "ats_professional"

        initial_count = len(doc1["content"]["experience"])
        new_content = dict(doc1["content"])
        new_content["experience"] = list(doc1["content"]["experience"]) + [{
            "id": "exp-custom-1",
            "company": "NextGen Systems",
            "role": "Lead Cloud Architect",
            "location": "San Francisco, CA",
            "start_date": "2022",
            "end_date": "Present",
            "current": True,
            "bullets": ["Architected hybrid cloud platform reducing downtime by 40%."],
        }]

        update_resp = await client.put(
            "/api/builder",
            json={
                "version": 1,
                "template_id": "ats_professional",
                "content": new_content,
            },
        )
        assert update_resp.status_code == 200
        doc2 = update_resp.json()
        assert doc2["version"] == 2
        assert doc2["template_id"] == "ats_professional"
        assert len(doc2["content"]["experience"]) == initial_count + 1

        # 2. Concurrency Conflict: Attempting update with stale version 1 returns 409 Conflict
        stale_resp = await client.put(
            "/api/builder",
            json={
                "version": 1,
                "template_id": "ats_professional",
            },
        )
        assert stale_resp.status_code == 409
        assert "version mismatch" in stale_resp.json()["detail"].lower()

        # 3. Invalid template rejection
        bad_template_resp = await client.put(
            "/api/builder",
            json={
                "version": 2,
                "template_id": "fancy_gold_columns",
            },
        )
        assert bad_template_resp.status_code == 400
        assert "invalid template_id" in bad_template_resp.json()["detail"].lower()


@pytest.mark.asyncio
async def test_reorder_sections_and_toggle_visibility(builder_test_env):
    """Allows user to customize section order and visibility toggles."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        await client.post("/api/session")
        doc = (await client.get("/api/builder")).json()

        custom_order = [
            "contact",
            "skills",
            "experience",
            "projects",
            "education",
            "certifications",
            "summary",
            "additional",
        ]
        custom_vis = dict(doc["section_visibility"])
        custom_vis["summary"] = False  # Hide summary

        update_resp = await client.put(
            "/api/builder",
            json={
                "version": doc["version"],
                "section_order": custom_order,
                "section_visibility": custom_vis,
            },
        )
        assert update_resp.status_code == 200
        updated = update_resp.json()
        assert updated["section_order"] == custom_order
        assert updated["section_visibility"]["summary"] is False


@pytest.mark.asyncio
async def test_reset_builder_document(builder_test_env):
    """Allows user to reset working document to uploaded resume or clean blank slate."""
    pdf_bytes = create_synthetic_pdf(name="Taylor Slate", pages=1)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        await client.post(
            "/api/resume/upload",
            files={"file": ("taylor_resume.pdf", pdf_bytes, "application/pdf")},
        )
        doc = (await client.get("/api/builder")).json()

        # Reset to empty
        empty_reset = await client.post("/api/builder/reset", json={"source": "empty"})
        assert empty_reset.status_code == 200
        data_empty = empty_reset.json()
        assert data_empty["content"]["contact"]["name"] == ""
        assert len(data_empty["content"]["experience"]) == 0

        # Reset back to reviewed resume
        resume_reset = await client.post("/api/builder/reset", json={"source": "reviewed_resume"})
        assert resume_reset.status_code == 200
        data_resumed = resume_reset.json()
        assert "Taylor Slate" in data_resumed["content"]["contact"]["name"]


@pytest.mark.asyncio
async def test_builder_preserves_canonical_resume_and_historical_assessments(builder_test_env):
    """Modifying the builder working document never silently alters canonical resume or prior assessments."""
    pdf_bytes = create_synthetic_pdf(name="Casey Audit", pages=1)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # 1. Upload resume
        upload_resp = await client.post(
            "/api/resume/upload",
            files={"file": ("casey_resume.pdf", pdf_bytes, "application/pdf")},
        )
        assert upload_resp.status_code == 201

        # 2. Run ATS Assessment
        ats_resp = await client.post("/api/assessment")
        assert ats_resp.status_code == 200
        ats_score_before = ats_resp.json()["overall_score"]

        # 3. Read canonical resume before builder edits
        resume_before = (await client.get("/api/resume")).json()

        # 4. Perform drastic edits in builder
        doc = (await client.get("/api/builder")).json()
        drastic_content = dict(doc["content"])
        drastic_content["contact"]["name"] = "Totally Changed Name"
        drastic_content["experience"] = []  # Clear experience in builder

        update_resp = await client.put(
            "/api/builder",
            json={
                "version": doc["version"],
                "content": drastic_content,
            },
        )
        assert update_resp.status_code == 200

        # 5. Verify canonical resume is 100% UNCHANGED
        resume_after = (await client.get("/api/resume")).json()
        assert resume_after["structured_data"]["contact"]["name"] == resume_before["structured_data"]["contact"]["name"]
        assert len(resume_after["structured_data"]["experience"]) == len(resume_before["structured_data"]["experience"])

        # 6. Verify historical ATS assessment is 100% UNCHANGED
        ats_cached = (await client.get("/api/assessment")).json()
        assert ats_cached["overall_score"] == ats_score_before


@pytest.mark.asyncio
async def test_builder_session_isolation(builder_test_env):
    """Session B cannot read or overwrite Session A's builder document."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client_a:
        await client_a.post("/api/session")
        doc_a = (await client_a.get("/api/builder")).json()
        await client_a.put(
            "/api/builder",
            json={
                "version": doc_a["version"],
                "template_id": "ats_professional",
            },
        )

    # Session B on fresh client
    async with AsyncClient(transport=transport, base_url="http://test") as client_b:
        await client_b.post("/api/session")
        doc_b = (await client_b.get("/api/builder")).json()
        # Session B starts with default ATS Professional template and unique ID
        assert doc_b["id"] != doc_a["id"]
        assert doc_b["template_id"] == "ats_professional"
