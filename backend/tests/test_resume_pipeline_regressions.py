"""Pure regression tests for resume parsing, canonical Builder conversion, and exports.

These tests intentionally avoid importing app.main and therefore can run even when
optional async database drivers are not installed in the execution environment.
"""

from io import BytesIO

import pymupdf as fitz
from docx import Document

from app.services.parser_service import normalize_text_encoding, parse_structured_profile
from app.services.builder_service import convert_structured_profile_to_builder_content
from app.services.pdf_export_service import generate_resume_pdf
from app.services.docx_export_service import generate_resume_docx


SYNTHETIC_RESUME = """Riley Example
+1 (555) 010-2034 • riley@example.com • linkedin.com/in/riley-example-synthetic • github.com/riley-example-synthetic

Executive Summary
Early-career software engineer building practical applications with Python, TypeScript, and accessible product design.

Professional Experience
Kestrel Learning Studio – Co-Founder (3-person team) | Portland, USA | May 2025 – Present
• Led frontend delivery for 18 interactive learning experiences and 4 small business websites, including event pages,
community portals, and accessible course materials.
• Built an internal React invoicing tool with automated invoice numbering and tailored interfaces.
• Analyzed market and competitor offerings to identify customer needs and product opportunities.
CodeWorks Lab – Machine Learning Intern | Remote | Sep 2024 – Oct 2024
• Built a synthetic message classifier on a 5,500-message sample dataset using TF-IDF vectorization and Multinomial
Naive Bayes, reaching 94% classification accuracy.
• Applied SHAP to explain which features drove individual model predictions.
North Valley Training Program | On-site | May 2024 – Jun 2024
• Completed a 45-day industry training program on applied programming and technical problem-solving.

Key Projects & Initiatives
Mindful Path – Wellness Companion | Next.js, FastAPI, LangGraph, MongoDB | Dec 2024
Code: github.com/riley-example-synthetic/mindful-path
• Built a full-stack wellness companion with a Next.js interface and FastAPI backend, using a LangGraph workflow
for context-aware responses.
• Stored conversation history in MongoDB and added a mood journal.
SignalMatch Resume Analyzer | Python, FastAPI, LangGraph, Next.js | Aug 2024
Code: github.com/riley-example-synthetic/signalmatch
• Built a tool that compares resume evidence with job requirements and identifies skill gaps.
• Implemented a workflow that extracts job requirements and generates grounded improvement suggestions.

Areas of Expertise
Technical Skills & Proficiencies: Languages: Python, JavaScript, TypeScript, Frontend: React, Next.js, HTML, CSS, Backend: FastAPI, Node.js, Generative AI & NLP: LangGraph, Agentic AI, Generative AI, LLMs, Prompt Engineering, Natural Language Processing, Machine Learning: scikit-learn, TF-IDF, Naive Bayes, Logistic Regression, SHAP, Data: Pandas, NumPy, Matplotlib, Databases: MongoDB, MySQL, Tools: Git, GitHub, Jupyter Notebook, VS Code, Fundamentals: Data Structures & Algorithms, Working knowledge: TensorFlow, CNN, Decision Trees, Ensemble Methods, AWS, Streamlit

Education
Artificial Intelligence & Machine Learning | Cascade Technical University | 2022 – 2026 | CGPA: 3.8
Oregon | 2021 — Senior Secondary (Class XII) | Example Valley High School

Achievements & Certifications
Community Technology Award, Campus Build Challenge: finalist, Certifications: Cloud Foundations, Practical Data Modeling, Accessible Web Interfaces
"""


def _builder_doc(profile):
    content = convert_structured_profile_to_builder_content(profile)
    return {
        "id": "synthetic-builder",
        "session_id": "synthetic-session",
        "source_resume_id": "synthetic-resume",
        "version": 2,
        "template_id": "ats_professional",
        "template_config": {
            "font_family": "inter",
            "font_size": "medium",
            "margin_size": "standard",
            "line_spacing": "normal",
            "accent_color": "#254B78",
        },
        "section_order": [
            "contact", "summary", "experience", "projects", "skills",
            "education", "certifications", "additional",
        ],
        "section_visibility": {
            key: True for key in [
                "contact", "summary", "experience", "projects", "skills",
                "education", "certifications", "additional",
            ]
        },
        "content": content.model_dump(),
    }


def _normalized_pdf_text(pdf_bytes):
    with fitz.open(stream=pdf_bytes, filetype="pdf") as document:
        return " ".join(" ".join(page.get_text("text") for page in document).split())


def test_windows_1252_bullet_and_dash_normalization_is_stable():
    source = "\x95 Led work \x96 delivered results"
    first = normalize_text_encoding(source)
    second = normalize_text_encoding(first)
    assert first == "• Led work – delivered results"
    assert second == first


def test_synthetic_resume_headings_sections_and_wrapped_lines_are_preserved():
    profile = parse_structured_profile(SYNTHETIC_RESUME, [])
    assert any("Kestrel Learning Studio" in item for item in profile["experience"])
    assert any("SignalMatch Resume Analyzer" in item for item in profile["projects"])
    assert len(profile["skill_categories"]) >= 8
    assert len(profile["skills"]) >= 30
    assert len(profile["certifications"]) == 3
    assert any("Campus Build Challenge" in item for item in profile["other"])
    assert profile["contact"]["email"] == "riley@example.com"
    assert "example.com" not in profile["contact"]["urls"]


def test_builder_groups_experience_and_project_bullets_and_preserves_gpa():
    profile = parse_structured_profile(SYNTHETIC_RESUME, [])
    content = convert_structured_profile_to_builder_content(profile)

    assert len(content.experience) == 3
    kolkode = content.experience[0]
    assert kolkode.company == "Kestrel Learning Studio"
    assert kolkode.role == "Co-Founder (3-person team)"
    assert kolkode.current is True
    assert len(kolkode.bullets) == 3
    assert "community portals, and accessible course materials" in kolkode.bullets[0]

    codealpha = content.experience[1]
    assert codealpha.company == "CodeWorks Lab"
    assert codealpha.role == "Machine Learning Intern"
    assert any("Multinomial Naive Bayes" in bullet for bullet in codealpha.bullets)

    assert len(content.projects) == 2
    maan = content.projects[0]
    assert maan.title.startswith("Mindful Path – Wellness Companion")
    assert "LangGraph" in maan.tech_stack
    assert maan.url == "github.com/riley-example-synthetic/mindful-path"
    assert len(maan.bullets) == 2
    assert "workflow for context-aware responses" in maan.bullets[0]
    assert content.projects[1].title == "SignalMatch Resume Analyzer"

    assert any(category.category == "Languages" and "Python" in category.skills for category in content.skills)
    assert any(category.category == "Working knowledge" and "TensorFlow" in category.skills for category in content.skills)
    assert content.education[0].gpa == "3.8"
    assert content.education[1].end_date == "2021"
    assert "Example Valley High School" in content.education[1].institution
    assert len(content.certifications) == 3


def test_generated_pdf_and_docx_keep_content_and_do_not_emit_fake_placeholders():
    profile = parse_structured_profile(SYNTHETIC_RESUME, [])
    builder_doc = _builder_doc(profile)

    pdf_bytes = generate_resume_pdf(builder_doc)
    pdf_text = _normalized_pdf_text(pdf_bytes)
    assert "Riley Example" in pdf_text
    assert "Kestrel Learning Studio" in pdf_text and "CodeWorks Lab" in pdf_text
    assert "Mindful Path" in pdf_text and "SignalMatch Resume Analyzer" in pdf_text
    assert "TECHNICAL SKILLS" in pdf_text and "TensorFlow" in pdf_text
    assert "Cloud Foundations" in pdf_text
    assert "Experience Role" not in pdf_text
    assert "Company / Organization" not in pdf_text
    assert "Project 1" not in pdf_text
    assert "Candidate Name" not in pdf_text
    assert "Institution" not in pdf_text

    docx_bytes = generate_resume_docx(builder_doc)
    doc = Document(BytesIO(docx_bytes))
    docx_text = " ".join(p.text for p in doc.paragraphs)
    assert "Riley Example" in docx_text
    assert "Kestrel Learning Studio" in docx_text and "CodeWorks Lab" in docx_text
    assert "Mindful Path" in docx_text and "SignalMatch Resume Analyzer" in docx_text
    assert "TECHNICAL SKILLS" in docx_text and "TensorFlow" in docx_text
    assert "Experience Role" not in docx_text
    assert "Company / Organization" not in docx_text
    assert "Project 1" not in docx_text
    assert "Candidate Name" not in docx_text
