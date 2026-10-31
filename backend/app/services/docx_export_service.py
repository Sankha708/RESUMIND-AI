"""DOCX Resume Generator Service (Phase 10 — Screen 7).

Generates genuinely editable Microsoft Word (.docx) documents from canonical
ResumeBuilderDocument state using python-docx. Preserves section order, template
distinctions, typography, bullet points, and single-column ATS parseability.
"""

import io
import re
from typing import Any, Dict, List, Optional, Tuple
import docx
from docx.shared import Inches, Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn

from app.schemas.builder import (
    AdditionalSectionItem,
    BuilderContent,
    CertificationItem,
    EducationItem,
    ExperienceItem,
    ProjectItem,
    SkillCategory,
    TemplateConfig,
)

# Standard font families mapped to Microsoft Word fonts
DOCX_FONT_MAP = {
    "inter": "Arial",
    "merriweather": "Georgia",
    "roboto_mono": "Consolas",
}

# Typography scale mappings in Points
DOCX_FONT_SIZES = {
    "compact": {"body": 9.5, "sub": 10.5, "head": 12.0, "title": 18.0},
    "medium": {"body": 10.5, "sub": 11.5, "head": 13.0, "title": 20.0},
    "spacious": {"body": 11.5, "sub": 12.5, "head": 14.5, "title": 22.0},
}

# Margins mapped to Inches
DOCX_MARGIN_MAP = {
    "compact": Inches(0.5),
    "standard": Inches(0.75),
    "wide": Inches(1.0),
}


def hex_to_docx_rgb(hex_code: str) -> RGBColor:
    """Converts a hex color string to a python-docx RGBColor."""
    hex_clean = hex_code.lstrip("#")
    if len(hex_clean) == 3:
        hex_clean = "".join(c * 2 for c in hex_clean)
    if len(hex_clean) != 6:
        return RGBColor(24, 26, 29)
    try:
        r = int(hex_clean[0:2], 16)
        g = int(hex_clean[2:4], 16)
        b = int(hex_clean[4:6], 16)
        return RGBColor(r, g, b)
    except ValueError:
        return RGBColor(24, 26, 29)


def add_bottom_border_to_paragraph(p, hex_color: str = "181A1D"):
    """Adds an ATS-safe horizontal border under a Word paragraph via direct oxml manipulation."""
    pPr = p._p.get_or_add_pPr()
    pBdr = OxmlElement('w:pBdr')
    bottom = OxmlElement('w:bottom')
    bottom.set(qn('w:val'), 'single')
    bottom.set(qn('w:sz'), '12')  # 1.5 pt
    bottom.set(qn('w:space'), '4')
    bottom.set(qn('w:color'), hex_color.lstrip('#'))
    pBdr.append(bottom)
    pPr.append(pBdr)


class DOCXResumeGenerator:
    """Renders structured resume documents into native editable DOCX packages."""

    def __init__(self, doc_data: Dict[str, Any]):
        self.doc_data = doc_data
        self.content: BuilderContent = BuilderContent(**doc_data.get("content", {}))
        self.template_id: str = "ats_professional"  # One canonical single-column resume format
        # Keep the exported document on the single approved ATS Professional style.
        self.template_config: TemplateConfig = TemplateConfig()
        self.section_order: List[str] = doc_data.get("section_order", [])
        self.section_visibility: Dict[str, bool] = doc_data.get("section_visibility", {})

        # Font and layout resolution
        font_key = self.template_config.font_family
        self.font_name = DOCX_FONT_MAP.get(font_key, "Arial")

        self.sizes = DOCX_FONT_SIZES.get(self.template_config.font_size, DOCX_FONT_SIZES["medium"])
        self.margin = DOCX_MARGIN_MAP.get(self.template_config.margin_size, DOCX_MARGIN_MAP["standard"])
        self.accent_rgb = hex_to_docx_rgb(self.template_config.accent_color)
        self.text_rgb = RGBColor(24, 26, 29)
        self.muted_rgb = RGBColor(90, 97, 107)

        # Initialize python-docx Document
        self.doc = docx.Document()

        # Configure page geometry (A4 dimensions: 8.27 x 11.69 inches)
        for section in self.doc.sections:
            section.page_width = Inches(8.27)
            section.page_height = Inches(11.69)
            section.top_margin = self.margin
            section.bottom_margin = self.margin
            section.left_margin = self.margin
            section.right_margin = self.margin

        # Set default normal style
        style = self.doc.styles['Normal']
        style.font.name = self.font_name
        style.font.size = Pt(self.sizes["body"])
        style.font.color.rgb = self.text_rgb

    def generate(self) -> bytes:
        """Main rendering pipeline. Translates structured tree into Word elements."""
        # 1. Contact Header
        if self.section_visibility.get("contact", True):
            self._render_contact_header()

        # 2. Iterate through ordered sections
        for sec_key in self.section_order:
            if sec_key == "contact":
                continue
            if not self.section_visibility.get(sec_key, True):
                continue

            if sec_key == "summary" and self.content.summary:
                self._render_summary()
            elif sec_key == "experience" and self.content.experience:
                self._render_experience()
            elif sec_key == "projects" and self.content.projects:
                self._render_projects()
            elif sec_key == "skills" and self.content.skills:
                self._render_skills()
            elif sec_key == "education" and self.content.education:
                self._render_education()
            elif sec_key == "certifications" and self.content.certifications:
                self._render_certifications()
            elif sec_key == "additional" and self.content.additional:
                self._render_additional()

        buffer = io.BytesIO()
        self.doc.save(buffer)
        return buffer.getvalue()

    # ── Section Renderers ───────────────────────────────────────────────────────

    def _render_contact_header(self):
        """Create a clean contact header using only supplied candidate fields."""
        contact = self.content.contact
        name = (contact.name or "").strip()
        headline = (contact.headline or "").strip()

        if name:
            p_name = self.doc.add_paragraph()
            p_name.paragraph_format.space_before = Pt(0)
            p_name.paragraph_format.space_after = Pt(2)
            r_name = p_name.add_run(name)
            r_name.font.name = self.font_name
            r_name.font.size = Pt(self.sizes["title"])
            r_name.font.bold = True
            r_name.font.color.rgb = self.accent_rgb

        if headline:
            p_head = self.doc.add_paragraph()
            p_head.paragraph_format.space_before = Pt(0)
            p_head.paragraph_format.space_after = Pt(4)
            r_head = p_head.add_run(headline)
            r_head.font.name = self.font_name
            r_head.font.size = Pt(self.sizes["sub"])
            r_head.font.color.rgb = self.muted_rgb

        tokens = []
        for value in [contact.location, contact.email, contact.phone, contact.linkedin, contact.github, contact.website]:
            clean = re.sub(r"^https?://(www\.)?", "", (value or "").strip())
            if clean and clean not in tokens:
                tokens.append(clean)
        if tokens:
            p_contact = self.doc.add_paragraph()
            p_contact.paragraph_format.space_before = Pt(0)
            p_contact.paragraph_format.space_after = Pt(8)
            run = p_contact.add_run("  •  ".join(tokens))
            run.font.name = self.font_name
            run.font.size = Pt(self.sizes["body"] - 0.5)
            run.font.color.rgb = self.muted_rgb
            add_bottom_border_to_paragraph(p_contact, self.template_config.accent_color)

    def _render_section_heading(self, title: str):
        """Creates section header paragraph with uppercase text and bottom border rule."""
        p = self.doc.add_paragraph()
        p.paragraph_format.space_before = Pt(12)
        p.paragraph_format.space_after = Pt(4)
        p.paragraph_format.keep_with_next = True

        display_title = title.upper()
        run = p.add_run(display_title)
        run.font.name = self.font_name
        run.font.size = Pt(self.sizes["head"])
        run.font.bold = True
        run.font.color.rgb = self.accent_rgb

        add_bottom_border_to_paragraph(p, self.template_config.accent_color)

    def _render_summary(self):
        """Renders summary section."""
        self._render_section_heading("Professional Summary")
        p = self.doc.add_paragraph()
        p.paragraph_format.space_before = Pt(4)
        p.paragraph_format.space_after = Pt(8)
        run = p.add_run(self.content.summary or "")
        run.font.name = self.font_name
        run.font.size = Pt(self.sizes["body"])
        run.font.color.rgb = self.text_rgb

    def _render_experience(self):
        """Render grouped work entries without substituting fake Position/Company values."""
        entries = [item for item in self.content.experience if item.role or item.company or item.bullets]
        if not entries:
            return
        self._render_section_heading("Professional Experience")

        for item in entries:
            heading = " — ".join(part.strip() for part in (item.role, item.company) if part and part.strip())
            metadata = []
            if item.start_date:
                metadata.append(item.start_date.strip())
            end = item.end_date.strip() if item.end_date else ("Present" if item.current else "")
            if end:
                metadata.append(end)
            if item.location:
                metadata.append(item.location.strip())

            if heading:
                p_role = self.doc.add_paragraph()
                p_role.paragraph_format.space_before = Pt(5)
                p_role.paragraph_format.space_after = Pt(1)
                p_role.paragraph_format.keep_with_next = True
                run = p_role.add_run(heading)
                run.font.name = self.font_name
                run.font.size = Pt(self.sizes["sub"])
                run.font.bold = True
                run.font.color.rgb = self.text_rgb
            if metadata:
                p_meta = self.doc.add_paragraph()
                p_meta.paragraph_format.space_before = Pt(0)
                p_meta.paragraph_format.space_after = Pt(2)
                p_meta.paragraph_format.keep_with_next = bool(item.bullets)
                run = p_meta.add_run("  |  ".join(metadata))
                run.font.name = self.font_name
                run.font.size = Pt(self.sizes["body"] - 0.5)
                run.font.italic = True
                run.font.color.rgb = self.muted_rgb

            for bullet in item.bullets:
                if bullet and bullet.strip():
                    p_b = self.doc.add_paragraph(style="List Bullet")
                    p_b.paragraph_format.space_before = Pt(0)
                    p_b.paragraph_format.space_after = Pt(2)
                    rb = p_b.add_run(bullet.strip())
                    rb.font.name = self.font_name
                    rb.font.size = Pt(self.sizes["body"])
                    rb.font.color.rgb = self.text_rgb

    def _render_projects(self):
        """Render named projects with the actual stack, URL and grouped descriptions."""
        entries = [proj for proj in self.content.projects if proj.title or proj.url or proj.tech_stack or proj.bullets]
        if not entries:
            return
        self._render_section_heading("Projects")

        for proj in entries:
            title = (proj.title or "").strip()
            if title:
                p = self.doc.add_paragraph()
                p.paragraph_format.space_before = Pt(5)
                p.paragraph_format.space_after = Pt(1)
                p.paragraph_format.keep_with_next = True
                run = p.add_run(title)
                run.font.name = self.font_name
                run.font.size = Pt(self.sizes["sub"])
                run.font.bold = True
                run.font.color.rgb = self.text_rgb
            metadata = []
            if proj.start_date:
                metadata.append(proj.start_date.strip())
            if proj.url:
                metadata.append(re.sub(r"^https?://(www\.)?", "", proj.url.strip()))
            if proj.role:
                metadata.append(proj.role.strip())
            if metadata:
                p_meta = self.doc.add_paragraph()
                p_meta.paragraph_format.space_before = Pt(0)
                p_meta.paragraph_format.space_after = Pt(2)
                p_meta.paragraph_format.keep_with_next = bool(proj.tech_stack or proj.bullets)
                run = p_meta.add_run("  |  ".join(metadata))
                run.font.name = self.font_name
                run.font.size = Pt(self.sizes["body"] - 0.5)
                run.font.color.rgb = self.muted_rgb
            if proj.tech_stack:
                p_stack = self.doc.add_paragraph()
                p_stack.paragraph_format.space_before = Pt(0)
                p_stack.paragraph_format.space_after = Pt(2)
                p_stack.paragraph_format.keep_with_next = bool(proj.bullets)
                label = p_stack.add_run("Technologies: ")
                label.font.name = self.font_name
                label.font.size = Pt(self.sizes["body"] - 0.5)
                label.font.bold = True
                stack = p_stack.add_run(", ".join(proj.tech_stack))
                stack.font.name = self.font_name
                stack.font.size = Pt(self.sizes["body"] - 0.5)
                stack.font.color.rgb = self.muted_rgb
            for bullet in proj.bullets:
                if bullet and bullet.strip():
                    pb = self.doc.add_paragraph(style="List Bullet")
                    pb.paragraph_format.space_before = Pt(0)
                    pb.paragraph_format.space_after = Pt(2)
                    r_b = pb.add_run(bullet.strip())
                    r_b.font.name = self.font_name
                    r_b.font.size = Pt(self.sizes["body"])
                    r_b.font.color.rgb = self.text_rgb

    def _render_skills(self):
        """Renders skills matrix."""
        self._render_section_heading("Technical Skills")

        for cat in self.content.skills:
            if not cat.skills:
                continue
            p = self.doc.add_paragraph()
            p.paragraph_format.space_before = Pt(2)
            p.paragraph_format.space_after = Pt(2)

            r_cat = p.add_run(f"{cat.category}: ")
            r_cat.font.name = self.font_name
            r_cat.font.size = Pt(self.sizes["body"])
            r_cat.font.bold = True
            r_cat.font.color.rgb = self.text_rgb

            r_skills = p.add_run(", ".join(cat.skills))
            r_skills.font.name = self.font_name
            r_skills.font.size = Pt(self.sizes["body"])
            r_skills.font.color.rgb = self.text_rgb

    def _render_education(self):
        """Render only real education fields without placeholder institutions."""
        entries = [edu for edu in self.content.education if edu.institution or edu.degree or edu.highlights or edu.start_date or edu.end_date or edu.gpa]
        if not entries:
            return
        self._render_section_heading("Education")

        for edu in entries:
            title_parts = [edu.degree, edu.field_of_study, edu.institution]
            title = " — ".join(part.strip() for part in title_parts if part and part.strip())
            if title:
                p = self.doc.add_paragraph()
                p.paragraph_format.space_before = Pt(3)
                p.paragraph_format.space_after = Pt(1)
                run = p.add_run(title)
                run.font.name = self.font_name
                run.font.size = Pt(self.sizes["sub"])
                run.font.bold = True
                run.font.color.rgb = self.text_rgb
            details = [part.strip() for part in (edu.start_date, edu.end_date) if part and part.strip()]
            if edu.gpa:
                details.append(f"CGPA: {edu.gpa.strip()}")
            if details:
                p_meta = self.doc.add_paragraph()
                p_meta.paragraph_format.space_after = Pt(2)
                run = p_meta.add_run("  |  ".join(details))
                run.font.name = self.font_name
                run.font.size = Pt(self.sizes["body"] - 0.5)
                run.font.color.rgb = self.muted_rgb
            for highlight in edu.highlights:
                if highlight and highlight.strip():
                    p_b = self.doc.add_paragraph(style="List Bullet")
                    p_b.paragraph_format.space_before = Pt(0)
                    p_b.paragraph_format.space_after = Pt(1)
                    run = p_b.add_run(highlight.strip())
                    run.font.name = self.font_name
                    run.font.size = Pt(self.sizes["body"])
                    run.font.color.rgb = self.text_rgb

    def _render_certifications(self):
        """Render actual named certifications only."""
        entries = [cert for cert in self.content.certifications if cert.name and cert.name.strip()]
        if not entries:
            return
        self._render_section_heading("Certifications")
        for cert in entries:
            details = [value.strip() for value in (cert.issuer, cert.issue_date) if value and value.strip()]
            text = cert.name.strip() + (f" ({' · '.join(details)})" if details else "")
            p = self.doc.add_paragraph(style="List Bullet")
            p.paragraph_format.space_before = Pt(0)
            p.paragraph_format.space_after = Pt(2)
            run = p.add_run(text)
            run.font.name = self.font_name
            run.font.size = Pt(self.sizes["body"])
            run.font.color.rgb = self.text_rgb

    def _render_additional(self):
        """Renders custom additional sections."""
        for item in self.content.additional:
            self._render_section_heading(item.section_title or "Honors & Activities")
            for b in item.bullets:
                if b.strip():
                    pb = self.doc.add_paragraph(style='List Bullet')
                    pb.paragraph_format.space_before = Pt(0)
                    pb.paragraph_format.space_after = Pt(2)
                    rb = pb.add_run(b.strip())
                    rb.font.name = self.font_name
                    rb.font.size = Pt(self.sizes["body"])
                    rb.font.color.rgb = self.text_rgb


def generate_resume_docx(builder_doc_dict: Dict[str, Any]) -> bytes:
    """Entrypoint function to generate an ATS-compliant editable DOCX package from builder state."""
    generator = DOCXResumeGenerator(builder_doc_dict)
    return generator.generate()
