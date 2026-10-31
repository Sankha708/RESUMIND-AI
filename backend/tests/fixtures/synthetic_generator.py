"""Synthetic Non-PII Resume Fixture Generator for Unit & Integration Tests.

Generates valid, multi-page, empty, corrupt, scanned, and encrypted PDFs and DOCX files.
All generated documents use 100% synthetic, non-real identity and career data.
"""

import io
import pymupdf as fitz
import docx


def create_synthetic_pdf(
    name: str = "Alex Mercer",
    email: str = "alex.mercer@synthetic-domain.com",
    phone: str = "+1 (555) 019-2834",
    linkedin: str = "linkedin.com/in/alexmercer-synthetic",
    pages: int = 1,
) -> bytes:
    """Generates a valid single- or multi-page PDF with realistic section hierarchy."""
    doc = fitz.open()

    for p_idx in range(pages):
        page = doc.new_page(width=595, height=842)  # A4 standard
        y = 50

        if p_idx == 0:
            # Header block
            page.insert_text(fitz.Point(50, y), name, fontsize=18, fontname="helv", color=(0.1, 0.1, 0.1))
            y += 24
            contact_line = f"{email}  |  {phone}  |  {linkedin}"
            page.insert_text(fitz.Point(50, y), contact_line, fontsize=10, fontname="helv", color=(0.3, 0.3, 0.3))
            y += 30

            # Summary Section
            page.insert_text(fitz.Point(50, y), "PROFESSIONAL SUMMARY", fontsize=12, fontname="helv", color=(0.2, 0.3, 0.6))
            y += 18
            summary_text = (
                "Strategic and results-driven Software Engineer with 6+ years of experience designing\n"
                "scalable cloud services, high-throughput APIs, and modern data platforms."
            )
            page.insert_text(fitz.Point(50, y), summary_text, fontsize=10, fontname="helv", color=(0.2, 0.2, 0.2))
            y += 45

            # Experience Section
            page.insert_text(fitz.Point(50, y), "WORK EXPERIENCE", fontsize=12, fontname="helv", color=(0.2, 0.3, 0.6))
            y += 18
            exp_text = (
                "Lead Backend Engineer — Nexus Systems (Jan 2021 – Present)\n"
                "• Architected async microservices reducing API latency by 35%.\n"
                "• Spearheaded zero-trust session token migration across distributed services.\n\n"
                "Software Engineer — CoreLogic Inc (Jun 2018 – Dec 2020)\n"
                "• Designed automated ETL pipelines processing 2M+ synthetic records daily.\n"
                "• Collaborated with product teams to deliver accessibility compliance."
            )
            page.insert_text(fitz.Point(50, y), exp_text, fontsize=10, fontname="helv", color=(0.2, 0.2, 0.2))
            y += 90

            # Education Section
            page.insert_text(fitz.Point(50, y), "EDUCATION", fontsize=12, fontname="helv", color=(0.2, 0.3, 0.6))
            y += 18
            edu_text = "B.S. in Computer Science — Pacific Crest University (2014 – 2018)"
            page.insert_text(fitz.Point(50, y), edu_text, fontsize=10, fontname="helv", color=(0.2, 0.2, 0.2))
            y += 35

            # Skills Section
            page.insert_text(fitz.Point(50, y), "TECHNICAL SKILLS", fontsize=12, fontname="helv", color=(0.2, 0.3, 0.6))
            y += 18
            skills_text = "Python, FastAPI, PostgreSQL, SQLite, Next.js, TypeScript, Docker, PyMuPDF, CI/CD"
            page.insert_text(fitz.Point(50, y), skills_text, fontsize=10, fontname="helv", color=(0.2, 0.2, 0.2))

        else:
            # Page 2+ content
            page.insert_text(fitz.Point(50, y), f"PROJECTS & CERTIFICATIONS (Page {p_idx + 1})", fontsize=12, fontname="helv", color=(0.2, 0.3, 0.6))
            y += 24
            extra_text = (
                "Project Horizon — Open source telemetry tooling (2022)\n"
                "• Authored high-performance parser for structured document formats.\n\n"
                "CERTIFICATIONS\n"
                "• AWS Certified Solutions Architect (2022)"
            )
            page.insert_text(fitz.Point(50, y), extra_text, fontsize=10, fontname="helv", color=(0.2, 0.2, 0.2))

    pdf_bytes = doc.tobytes()
    doc.close()
    return pdf_bytes


def create_scanned_image_only_pdf() -> bytes:
    """Generates a PDF page containing only an image drawing without any text layer."""
    doc = fitz.open()
    page = doc.new_page(width=595, height=842)
    # Draw geometric shapes to simulate a scanned raster page without text
    rect = fitz.Rect(50, 50, 545, 792)
    page.draw_rect(rect, color=(0.8, 0.8, 0.8), fill=(0.95, 0.95, 0.95))
    pdf_bytes = doc.tobytes()
    doc.close()
    return pdf_bytes


def create_encrypted_pdf(password: str = "testpass123") -> bytes:
    """Generates an encrypted/password-protected PDF."""
    doc = fitz.open()
    page = doc.new_page(width=595, height=842)
    page.insert_text(fitz.Point(50, 50), "Confidential Protected Document Content")
    pdf_bytes = doc.tobytes(
        encryption=fitz.PDF_ENCRYPT_AES_256,
        user_pw=password,
        owner_pw=password,
    )
    doc.close()
    return pdf_bytes


def create_synthetic_docx(
    name: str = "Elena Rostova",
    email: str = "elena.rostova@synthetic-domain.com",
    phone: str = "+1 (555) 012-4491",
) -> bytes:
    """Generates a valid DOCX document containing headings, paragraphs, and list items."""
    doc = docx.Document()

    # Title / Name
    doc.add_heading(name, level=0)
    doc.add_paragraph(f"{email} | +1 (555) 012-4491 | github.com/elena-synthetic")

    # Summary
    doc.add_heading("PROFESSIONAL SUMMARY", level=1)
    doc.add_paragraph("Principal Systems Architect specializing in secure distributed services and event-driven architectures.")

    # Experience
    doc.add_heading("WORK EXPERIENCE", level=1)
    doc.add_paragraph("Principal Architect — Stratum Cloud Labs (2020 - Present)")
    doc.add_paragraph("Architected zero-login privacy-preserving session infrastructure.", style="List Bullet")
    doc.add_paragraph("Designed high-throughput parsing pipelines processing Office and PDF specifications.", style="List Bullet")

    # Education
    doc.add_heading("EDUCATION", level=1)
    doc.add_paragraph("M.S. in Computer Engineering — Horizon Institute (2018 - 2020)")

    # Skills
    doc.add_heading("SKILLS", level=1)
    doc.add_paragraph("Python, Rust, FastAPI, SQLAlchemy, Alembic, Architecture Design, Distributed Systems")

    bio = io.BytesIO()
    doc.save(bio)
    return bio.getvalue()


def create_corrupt_docx_package() -> bytes:
    """Generates a ZIP archive missing standard WordprocessingML files."""
    bio = io.BytesIO()
    with fitz.open() as d:  # just creating dummy bytes
        pass
    import zipfile
    with zipfile.ZipFile(bio, "w") as zf:
        zf.writestr("unrelated.txt", "not a docx")
    return bio.getvalue()
