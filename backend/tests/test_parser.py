"""Automated test suite for document parsing, PDF/DOCX validation,
streaming size bounds, structured section extraction, and session isolation.
"""

import io
import zipfile
from pathlib import Path
import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from app.config import settings
from app.database import Base, get_db
from app.main import app
from app.models.resume import UploadedResume
from app.services.parser_service import (
    DocumentLimitExceededError,
    extract_text_from_pdf,
    validate_file_signatures,
)
from app.services.storage_service import get_session_storage_dirs
from tests.fixtures.synthetic_generator import (
    create_corrupt_docx_package,
    create_encrypted_pdf,
    create_scanned_image_only_pdf,
    create_synthetic_docx,
    create_synthetic_pdf,
)


@pytest.fixture
async def parser_test_env(tmp_path: Path):
    """Provisions an isolated SQLite test database and temporary storage root."""
    test_db_path = tmp_path / "test_parser.db"
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
    await engine.dispose()


@pytest.fixture
async def client():
    """Async HTTP test client bound to FastAPI application."""
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        yield ac


@pytest.mark.asyncio
async def test_parse_valid_single_page_pdf(parser_test_env, client):
    """Verify clean upload, text extraction, and structured parsing of a valid 1-page PDF."""
    pdf_bytes = create_synthetic_pdf(name="Alex Mercer", pages=1)

    files = {"file": ("alex_mercer_resume.pdf", pdf_bytes, "application/pdf")}
    response = await client.post("/api/resume/upload", files=files)
    assert response.status_code == 201

    data = response.json()
    assert data["filename"] == "alex_mercer_resume.pdf"
    assert data["file_type"] == "pdf"
    assert data["file_size"] == len(pdf_bytes)
    assert "Alex Mercer" in data["raw_text"]
    assert "alex.mercer@synthetic-domain.com" in data["raw_text"]

    # Verify structured fields
    structured = data["structured_data"]
    assert structured["contact"]["email"] == "alex.mercer@synthetic-domain.com"
    assert "+1 (555) 019-2834" in structured["contact"]["phone"]
    assert "FastAPI" in structured["skills"]
    assert len(structured["experience"]) > 0
    assert len(structured["education"]) > 0

    # Verify file stored on disk under session
    session_id = data["session_id"]
    dirs = get_session_storage_dirs(session_id, base_root=parser_test_env["storage_root"])
    stored_files = list(dirs["uploads"].glob("*.pdf"))
    assert len(stored_files) == 1


@pytest.mark.asyncio
async def test_parse_valid_multi_page_pdf(parser_test_env, client):
    """Verify text across multiple pages is preserved with page separation."""
    pdf_bytes = create_synthetic_pdf(pages=2)

    files = {"file": ("multi_page.pdf", pdf_bytes, "application/pdf")}
    response = await client.post("/api/resume/upload", files=files)
    assert response.status_code == 201

    data = response.json()
    assert "--- Page Break ---" in data["raw_text"]
    assert "PROJECTS & CERTIFICATIONS (Page 2)" in data["raw_text"]


@pytest.mark.asyncio
async def test_parse_valid_docx(parser_test_env, client):
    """Verify upload and extraction of DOCX headings, paragraphs, and list items."""
    docx_bytes = create_synthetic_docx(name="Elena Rostova")

    files = {"file": ("elena_resume.docx", docx_bytes, "application/vnd.openxmlformats-officedocument.wordprocessingml.document")}
    response = await client.post("/api/resume/upload", files=files)
    assert response.status_code == 201

    data = response.json()
    assert data["filename"] == "elena_resume.docx"
    assert data["file_type"] == "docx"
    assert "Elena Rostova" in data["raw_text"]

    structured = data["structured_data"]
    assert structured["contact"]["email"] == "elena.rostova@synthetic-domain.com"
    assert "Rust" in structured["skills"] or "Python" in structured["skills"]
    assert len(structured["experience"]) > 0


@pytest.mark.asyncio
async def test_empty_and_corrupt_documents_rejected(parser_test_env, client):
    """Verify rejection of empty, zero-byte, or malformed files."""
    # 1. Zero-byte file
    files_empty = {"file": ("empty.pdf", b"", "application/pdf")}
    res_empty = await client.post("/api/resume/upload", files=files_empty)
    assert res_empty.status_code == 400
    assert "empty" in res_empty.json()["detail"].lower()

    # 2. Corrupt junk bytes in PDF
    files_junk_pdf = {"file": ("junk.pdf", b"This is not a pdf file at all", "application/pdf")}
    res_junk_pdf = await client.post("/api/resume/upload", files=files_junk_pdf)
    assert res_junk_pdf.status_code == 400
    assert "magic header" in res_junk_pdf.json()["detail"]

    # 3. Corrupt DOCX package
    corrupt_docx = create_corrupt_docx_package()
    files_corrupt_docx = {"file": ("broken.docx", corrupt_docx, "application/vnd.openxmlformats-officedocument.wordprocessingml.document")}
    res_corrupt_docx = await client.post("/api/resume/upload", files=files_corrupt_docx)
    assert res_corrupt_docx.status_code == 400


@pytest.mark.asyncio
async def test_extension_content_mismatch_rejected(parser_test_env, client):
    """Verify that mislabeled extensions are rejected based on signature inspection."""
    # Text file disguised as .pdf
    files = {"file": ("sneaky.pdf", b"Random text without pdf header", "application/pdf")}
    res = await client.post("/api/resume/upload", files=files)
    assert res.status_code == 400

    # Unsupported extension
    files_unsupported = {"file": ("executable.exe", b"%PDF-fake", "application/octet-stream")}
    res_unsupported = await client.post("/api/resume/upload", files=files_unsupported)
    assert res_unsupported.status_code == 400


@pytest.mark.asyncio
async def test_oversized_file_rejected_beyond_10mb(parser_test_env, client):
    """Verify that uploads exceeding 10MB are rejected with 413 Payload Too Large."""
    # 10MB + 50KB payload
    oversized_bytes = b"%PDF-" + b"0" * (10 * 1024 * 1024 + 50 * 1024)

    files = {"file": ("oversized.pdf", oversized_bytes, "application/pdf")}
    res = await client.post("/api/resume/upload", files=files)
    assert res.status_code == 413
    assert "10 MB" in res.json()["detail"]

    # Verify no file remains in storage
    storage_root = parser_test_env["storage_root"]
    all_stored_files = list((storage_root / "uploads").glob("*/*"))
    assert len(all_stored_files) == 0


@pytest.mark.asyncio
async def test_scanned_image_only_pdf_generates_warning(parser_test_env, client):
    """Verify detection of image-only/scanned PDF without text layer."""
    scanned_pdf = create_scanned_image_only_pdf()

    files = {"file": ("scanned_resume.pdf", scanned_pdf, "application/pdf")}
    res = await client.post("/api/resume/upload", files=files)
    assert res.status_code == 201

    data = res.json()
    warnings = data["structured_data"]["warnings"]
    assert any("OCR is not supported" in w for w in warnings)


@pytest.mark.asyncio
async def test_encrypted_pdf_rejected_gracefully(parser_test_env, client):
    """Verify password-protected PDF is caught and rejected gracefully."""
    encrypted_pdf = create_encrypted_pdf(password="secret123")

    files = {"file": ("encrypted.pdf", encrypted_pdf, "application/pdf")}
    res = await client.post("/api/resume/upload", files=files)
    assert res.status_code == 400
    assert "encrypted" in res.json()["detail"].lower()


@pytest.mark.asyncio
async def test_session_isolation_and_cross_session_denial(parser_test_env, client):
    """Verify Session A and Session B cannot view or tamper with each other's resumes."""
    # 1. Session A uploads resume
    pdf_a = create_synthetic_pdf(name="Candidate Alpha")
    res_a = await client.post("/api/resume/upload", files={"file": ("alpha.pdf", pdf_a, "application/pdf")})
    assert res_a.status_code == 201
    cookie_a = res_a.cookies.get(settings.SESSION_COOKIE_NAME)

    # 2. Session B checks /api/resume without cookie
    client.cookies.clear()
    res_b_empty = await client.get("/api/resume")
    assert res_b_empty.status_code == 401

    # 3. Session B initializes its own session
    res_b_init = await client.post("/api/session")
    cookie_b = res_b_init.cookies.get(settings.SESSION_COOKIE_NAME)
    assert cookie_a != cookie_b

    # Session B queries /api/resume -> returns 404 (its session has no resume)
    client.cookies.set(settings.SESSION_COOKIE_NAME, cookie_b)
    res_b_resume = await client.get("/api/resume")
    assert res_b_resume.status_code == 404

    # 4. Session A can retrieve its own resume
    client.cookies.set(settings.SESSION_COOKIE_NAME, cookie_a)
    res_a_resume = await client.get("/api/resume")
    assert res_a_resume.status_code == 200
    assert res_a_resume.json()["filename"] == "alpha.pdf"


@pytest.mark.asyncio
async def test_get_and_update_structured_profile(parser_test_env, client):
    """Verify updating user-corrected structured fields persists changes accurately."""
    pdf_bytes = create_synthetic_pdf(name="Original Name")
    upload_res = await client.post("/api/resume/upload", files={"file": ("resume.pdf", pdf_bytes, "application/pdf")})
    assert upload_res.status_code == 201
    cookie = upload_res.cookies.get(settings.SESSION_COOKIE_NAME)

    # Fetch structured data
    client.cookies.set(settings.SESSION_COOKIE_NAME, cookie)
    get_res = await client.get("/api/resume")
    assert get_res.status_code == 200
    profile = get_res.json()["structured_data"]

    # User edits name and adds a verified skill
    profile["contact"]["name"] = "Verified Correct Name"
    profile["skills"].append("GraphQL")

    update_res = await client.put("/api/resume", json={"structured_data": profile})
    assert update_res.status_code == 200
    assert update_res.json()["structured_data"]["contact"]["name"] == "Verified Correct Name"
    assert "GraphQL" in update_res.json()["structured_data"]["skills"]

    # Re-fetch to ensure DB persistence
    re_get = await client.get("/api/resume")
    assert re_get.json()["structured_data"]["contact"]["name"] == "Verified Correct Name"


@pytest.mark.asyncio
async def test_delete_and_reset_cleanup(parser_test_env, client):
    """Verify document deletion and session reset thoroughly purge disk files and DB rows."""
    pdf_bytes = create_synthetic_pdf()
    upload_res = await client.post("/api/resume/upload", files={"file": ("to_delete.pdf", pdf_bytes, "application/pdf")})
    assert upload_res.status_code == 201
    cookie = upload_res.cookies.get(settings.SESSION_COOKIE_NAME)
    session_id = upload_res.json()["session_id"]

    dirs = get_session_storage_dirs(session_id, base_root=parser_test_env["storage_root"])
    assert len(list(dirs["uploads"].glob("*.pdf"))) == 1

    # DELETE /api/resume
    client.cookies.set(settings.SESSION_COOKIE_NAME, cookie)
    del_res = await client.delete("/api/resume")
    assert del_res.status_code == 200
    assert len(list(dirs["uploads"].glob("*.pdf"))) == 0

    # Query DB directly to verify row was expunged
    async with parser_test_env["session_factory"]() as db:
        stmt = UploadedResume.__table__.select().where(UploadedResume.session_id == session_id)
        result = await db.execute(stmt)
        assert result.first() is None


def test_docx_expansion_limit_rejects_large_archive_member():
    archive = io.BytesIO()
    with zipfile.ZipFile(archive, "w", compression=zipfile.ZIP_DEFLATED) as package:
        package.writestr("[Content_Types].xml", "<Types/>")
        package.writestr("word/document.xml", "<document/>")
        package.writestr("word/media/oversized.bin", b"x" * (25 * 1024 * 1024 + 1))

    with pytest.raises(DocumentLimitExceededError, match="25 MB parsing limit"):
        validate_file_signatures(archive.getvalue(), ".docx")


def test_pdf_page_limit_rejects_oversized_document():
    pdf_bytes = create_synthetic_pdf(pages=101)

    with pytest.raises(DocumentLimitExceededError, match="100-page parsing limit"):
        extract_text_from_pdf(pdf_bytes)
