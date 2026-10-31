"""PDF Resume Generator Service (Phase 10 — Screen 7).

Generates a clean, single-column vector PDF from canonical ResumeBuilderDocument
state using PyMuPDF (fitz). Uses one ATS Professional template
with dynamic typography, custom section ordering, page budgeting, and clickable hyperlinks.
"""

import io
import re
from typing import Any, Dict, List, Optional, Tuple
import pymupdf as fitz  # Use the canonical PyMuPDF import; retain fitz namespace internally

from app.schemas.builder import (
    AdditionalSectionItem,
    BuilderContent,
    CertificationItem,
    EducationItem,
    ExperienceItem,
    ProjectItem,
    ResumeBuilderDocumentSchema,
    SkillCategory,
    TemplateConfig,
)

# Standard A4 page geometry in points (72 points per inch)
# 210mm x 297mm = 595.28 x 841.89 points
PAGE_WIDTH = 595.0
PAGE_HEIGHT = 842.0

# Safe standard PDF base fonts supported natively by PyMuPDF and PDF readers
FONT_MAP = {
    "inter": {
        "regular": "helv",
        "bold": "hebo",
        "italic": "heit",
        "bold_italic": "hebi",
    },
    "merriweather": {
        "regular": "times-roman",
        "bold": "times-bold",
        "italic": "times-italic",
        "bold_italic": "times-bolditalic",
    },
    "roboto_mono": {
        "regular": "courier",
        "bold": "courier-bold",
        "italic": "courier-oblique",
        "bold_italic": "courier-boldoblique",
    },
}

# Typography scale mappings (base body size, heading size, subhead size)
FONT_SIZES = {
    "compact": {"body": 9.0, "sub": 10.0, "head": 12.0, "title": 18.0, "line_gap": 12.0},
    "medium": {"body": 10.0, "sub": 11.0, "head": 13.0, "title": 20.0, "line_gap": 13.5},
    "spacious": {"body": 11.0, "sub": 12.0, "head": 14.0, "title": 22.0, "line_gap": 15.0},
}

# Margin scales in points (72 points = 1 inch)
MARGIN_MAP = {
    "compact": 36.0,   # 0.5 inch
    "standard": 54.0,  # 0.75 inch
    "wide": 72.0,      # 1.0 inch
}

# Line spacing multipliers
LINE_SPACING_MAP = {
    "tight": 1.15,
    "normal": 1.30,
    "relaxed": 1.45,
}


def hex_to_rgb(hex_code: str) -> Tuple[float, float, float]:
    """Converts a hex color code to a PyMuPDF normalized RGB tuple (0.0 - 1.0)."""
    hex_clean = hex_code.lstrip("#")
    if len(hex_clean) == 3:
        hex_clean = "".join(c * 2 for c in hex_clean)
    if len(hex_clean) != 6:
        return (0.1, 0.1, 0.1)  # Default charcoal
    try:
        r = int(hex_clean[0:2], 16) / 255.0
        g = int(hex_clean[2:4], 16) / 255.0
        b = int(hex_clean[4:6], 16) / 255.0
        return (round(r, 3), round(g, 3), round(b, 3))
    except ValueError:
        return (0.1, 0.1, 0.1)


class PDFResumeGenerator:
    """Renders structured resume documents into single-column ATS vector PDFs."""

    def __init__(self, doc_data: Dict[str, Any]):
        self.doc_data = doc_data
        self.content: BuilderContent = BuilderContent(**doc_data.get("content", {}))
        self.template_id: str = "ats_professional"  # One canonical single-column resume format
        # Keep the exported document on the single approved ATS Professional style.
        self.template_config: TemplateConfig = TemplateConfig()
        self.section_order: List[str] = doc_data.get("section_order", [])
        self.section_visibility: Dict[str, bool] = doc_data.get("section_visibility", {})

        # Resolve typography and margins
        self.font_family = self.template_config.font_family
        self.fonts = FONT_MAP.get(self.font_family, FONT_MAP["inter"])

        self.sizes = FONT_SIZES.get(self.template_config.font_size, FONT_SIZES["medium"])
        self.margin = MARGIN_MAP.get(self.template_config.margin_size, MARGIN_MAP["standard"])
        self.line_mult = LINE_SPACING_MAP.get(self.template_config.line_spacing, LINE_SPACING_MAP["normal"])
        self.accent_rgb = hex_to_rgb(self.template_config.accent_color)
        self.text_rgb = (0.1, 0.1, 0.1)
        self.muted_rgb = (0.35, 0.35, 0.35)

        # Dynamic layout bounds
        self.left_x = self.margin
        self.right_x = PAGE_WIDTH - self.margin
        self.content_width = self.right_x - self.left_x
        self.top_y = self.margin
        self.bottom_y = PAGE_HEIGHT - self.margin

        # Active rendering state
        self.pdf: fitz.Document = fitz.open()
        self.current_page: fitz.Page = self._new_page()
        self.cursor_y: float = self.top_y

    def _new_page(self) -> fitz.Page:
        """Appends a new standard A4 page to the PDF document."""
        page = self.pdf.new_page(width=PAGE_WIDTH, height=PAGE_HEIGHT)
        self.cursor_y = self.top_y
        return page

    def _ensure_vertical_space(self, required_height: float):
        """Creates a new page if the required vertical space exceeds available page budget."""
        if self.cursor_y + required_height > self.bottom_y:
            self.current_page = self._new_page()

    def generate(self) -> bytes:
        """Main rendering pipeline. Processes sections in configured order."""
        # Contact Header is typically rendered first
        if self.section_visibility.get("contact", True):
            self._render_contact_header()

        for sec_key in self.section_order:
            if sec_key == "contact":
                continue  # Header already handled
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

        return self.pdf.tobytes(deflate=True)

    # ── Section Renderers ───────────────────────────────────────────────────────

    def _render_contact_header(self):
        """Render only supplied candidate fields; never invent a name placeholder."""
        contact = self.content.contact
        name = (contact.name or "").strip()
        headline = (contact.headline or "").strip()
        tokens = []
        for value in [contact.location, contact.email, contact.phone, contact.linkedin, contact.github, contact.website]:
            clean = re.sub(r"^https?://(www\.)?", "", (value or "").strip())
            if clean and clean not in tokens:
                tokens.append(clean)

        if not (name or headline or tokens):
            return
        self._ensure_vertical_space(60)

        if name:
            title_size = self.sizes["title"]
            self.current_page.insert_text(
                fitz.Point(self.left_x, self.cursor_y + title_size),
                name,
                fontsize=title_size,
                fontname=self.fonts["bold"],
                color=self.accent_rgb,
            )
            self.cursor_y += title_size + 4

        if headline:
            sub_size = self.sizes["sub"]
            self._ensure_vertical_space(sub_size + 4)
            self.current_page.insert_text(
                fitz.Point(self.left_x, self.cursor_y + sub_size),
                headline,
                fontsize=sub_size,
                fontname=self.fonts["regular"],
                color=self.muted_rgb,
            )
            self.cursor_y += sub_size + 4

        if tokens:
            self._render_wrapped_paragraph("  •  ".join(tokens))
            self.cursor_y += 4

        self._ensure_vertical_space(12)
        self.current_page.draw_line(
            fitz.Point(self.left_x, self.cursor_y),
            fitz.Point(self.right_x, self.cursor_y),
            color=self.accent_rgb,
            width=1.0,
        )
        self.cursor_y += 12

    def _render_section_heading(self, title: str):
        """Renders standard section header with horizontal rule or prefix."""
        self._ensure_vertical_space(35)
        self.cursor_y += 6

        head_size = self.sizes["head"]
        display_title = title.upper()

        self.current_page.insert_text(
            fitz.Point(self.left_x, self.cursor_y + head_size),
            display_title,
            fontsize=head_size,
            fontname=self.fonts["bold"],
            color=self.accent_rgb,
        )
        self.cursor_y += head_size + 4

        # Thin rule under section heading
        self.current_page.draw_line(
            fitz.Point(self.left_x, self.cursor_y),
            fitz.Point(self.right_x, self.cursor_y),
            color=self.accent_rgb,
            width=0.75,
        )
        self.cursor_y += 8

    def _render_summary(self):
        """Renders executive or professional summary paragraph."""
        self._render_section_heading("Professional Summary")
        text = self.content.summary or ""
        self._render_wrapped_paragraph(text)
        self.cursor_y += 8

    def _render_experience(self):
        """Render experience records without fake role/company labels."""
        entries = [item for item in self.content.experience if item.role or item.company or item.bullets]
        if not entries:
            return
        self._render_section_heading("Professional Experience")

        for item in entries:
            role = (item.role or "").strip()
            company = (item.company or "").strip()
            heading = " — ".join(part for part in (role, company) if part)
            date_parts = []
            if item.start_date:
                date_parts.append(item.start_date.strip())
            end = item.end_date.strip() if item.end_date else ("Present" if item.current else "")
            if end:
                date_parts.append(end)
            if item.location:
                date_parts.append(item.location.strip())
            metadata = "  |  ".join(date_parts)

            if heading:
                self._ensure_vertical_space(self.sizes["sub"] + 8)
                self.current_page.insert_text(
                    fitz.Point(self.left_x, self.cursor_y + self.sizes["sub"]),
                    heading,
                    fontsize=self.sizes["sub"],
                    fontname=self.fonts["bold"],
                    color=self.text_rgb,
                )
                heading_width = fitz.get_text_length(heading, fontname=self.fonts["bold"], fontsize=self.sizes["sub"])
                metadata_width = fitz.get_text_length(metadata, fontname=self.fonts["regular"], fontsize=self.sizes["body"] - 0.5) if metadata else 0
                if metadata and heading_width + metadata_width + 16 <= self.content_width:
                    self.current_page.insert_text(
                        fitz.Point(self.right_x - metadata_width, self.cursor_y + self.sizes["sub"]),
                        metadata,
                        fontsize=self.sizes["body"] - 0.5,
                        fontname=self.fonts["regular"],
                        color=self.muted_rgb,
                    )
                self.cursor_y += self.sizes["sub"] + 4
                if metadata and heading_width + metadata_width + 16 > self.content_width:
                    self._render_wrapped_paragraph(metadata)
            elif metadata:
                self._render_wrapped_paragraph(metadata)

            for bullet in item.bullets:
                text = (bullet or "").strip()
                if text:
                    self._render_bullet_item(text)
            if heading or metadata or item.bullets:
                self.cursor_y += 4

    def _render_projects(self):
        """Render real project titles and content; omit empty headings instead of placeholders."""
        entries = [proj for proj in self.content.projects if proj.title or proj.url or proj.tech_stack or proj.bullets]
        if not entries:
            return
        self._render_section_heading("Projects")

        for proj in entries:
            title = (proj.title or "").strip()
            if title:
                self._ensure_vertical_space(self.sizes["sub"] + 5)
                self.current_page.insert_text(
                    fitz.Point(self.left_x, self.cursor_y + self.sizes["sub"]),
                    title,
                    fontsize=self.sizes["sub"],
                    fontname=self.fonts["bold"],
                    color=self.text_rgb,
                )
                self.cursor_y += self.sizes["sub"] + 3

            metadata = []
            if proj.start_date:
                metadata.append(proj.start_date.strip())
            if proj.url:
                metadata.append(re.sub(r"^https?://(www\.)?", "", proj.url.strip()))
            if metadata:
                self._render_wrapped_paragraph("  |  ".join(metadata))

            if proj.role:
                self._render_wrapped_paragraph(proj.role.strip())
            if proj.tech_stack:
                self._render_wrapped_paragraph("Technologies: " + ", ".join(proj.tech_stack))
            for bullet in proj.bullets:
                text = (bullet or "").strip()
                if text:
                    self._render_bullet_item(text)
            self.cursor_y += 4

    def _render_skills(self):
        """Render all skill categories with measured wrapping and continued-page headings."""
        categories = [cat for cat in self.content.skills if cat.skills]
        if not categories:
            return

        # Reserve space for a heading and at least one category so a section title
        # cannot be stranded at the bottom of a page.
        self._ensure_vertical_space(self.sizes["head"] + self.sizes["body"] * 4 + 26)
        self._render_section_heading("Technical Skills")
        needs_continued_heading = False

        for cat in categories:
            label = (cat.category or "Technical Skills").strip()
            values = ", ".join(skill.strip() for skill in cat.skills if skill and skill.strip())
            if not values:
                continue

            if needs_continued_heading:
                self._ensure_vertical_space(self.sizes["head"] + self.sizes["body"] * 4 + 26)
                self._render_section_heading("Technical Skills (continued)")
                needs_continued_heading = False

            before_page = self.pdf.page_count
            self._ensure_vertical_space(self.sizes["body"] * 4 + 18)
            if self.pdf.page_count > before_page:
                self._render_section_heading("Technical Skills (continued)")

            self._ensure_vertical_space(self.sizes["body"] * 2.5)
            self.current_page.insert_text(
                fitz.Point(self.left_x, self.cursor_y + self.sizes["body"]),
                f"{label}:",
                fontsize=self.sizes["body"],
                fontname=self.fonts["bold"],
                color=self.text_rgb,
            )
            self.cursor_y += self.sizes["body"] + 1
            page_before_values = self.pdf.page_count
            self._render_wrapped_paragraph(values)
            if self.pdf.page_count > page_before_values:
                needs_continued_heading = True
            self.cursor_y += 3

    def _render_education(self):
        """Render education records while omitting absent fields rather than fake institutions."""
        entries = [edu for edu in self.content.education if edu.institution or edu.degree or edu.highlights or edu.start_date or edu.end_date]
        if not entries:
            return
        self._render_section_heading("Education")

        for edu in entries:
            title_parts = [edu.degree, edu.field_of_study, edu.institution]
            title = " — ".join(part.strip() for part in title_parts if part and part.strip())
            if title:
                self._ensure_vertical_space(self.sizes["sub"] + 5)
                self.current_page.insert_text(
                    fitz.Point(self.left_x, self.cursor_y + self.sizes["sub"]),
                    title,
                    fontsize=self.sizes["sub"],
                    fontname=self.fonts["bold"],
                    color=self.text_rgb,
                )
                self.cursor_y += self.sizes["sub"] + 3
            date_parts = [part.strip() for part in (edu.start_date, edu.end_date) if part and part.strip()]
            if edu.gpa:
                date_parts.append(f"CGPA: {edu.gpa.strip()}")
            if date_parts:
                self._render_wrapped_paragraph("  |  ".join(date_parts))
            for highlight in edu.highlights:
                if highlight and highlight.strip():
                    self._render_bullet_item(highlight.strip())
            self.cursor_y += 3

    def _render_certifications(self):
        """Render named certifications only; empty records are omitted."""
        entries = [cert for cert in self.content.certifications if cert.name and cert.name.strip()]
        if not entries:
            return
        self._render_section_heading("Certifications")

        for cert in entries:
            details = [value.strip() for value in (cert.issuer, cert.issue_date) if value and value.strip()]
            text = cert.name.strip() + (f" ({' · '.join(details)})" if details else "")
            self._render_bullet_item(text)
        self.cursor_y += 3

    def _render_additional(self):
        """Renders custom sections (Honors & Awards, Publications, etc.)."""
        for item in self.content.additional:
            self._render_section_heading(item.section_title or "Honors & Activities")
            for bullet in item.bullets:
                if bullet.strip():
                    self._render_bullet_item(bullet.strip())
            self.cursor_y += 4

    # ── Text Wrapping & Bullet Formatting Helpers ──────────────────────────────

    def _render_wrapped_paragraph(self, text: str):
        """Flows multi-line text cleanly across page boundaries."""
        words = text.split()
        if not words:
            return

        line_words = []
        line_height = self.sizes["body"] * self.line_mult

        for word in words:
            test_line = " ".join(line_words + [word])
            line_w = fitz.get_text_length(test_line, fontname=self.fonts["regular"], fontsize=self.sizes["body"])

            if line_w <= self.content_width:
                line_words.append(word)
            else:
                self._ensure_vertical_space(line_height)
                self.current_page.insert_text(
                    fitz.Point(self.left_x, self.cursor_y + self.sizes["body"]),
                    " ".join(line_words),
                    fontsize=self.sizes["body"],
                    fontname=self.fonts["regular"],
                    color=self.text_rgb,
                )
                self.cursor_y += line_height
                line_words = [word]

        if line_words:
            self._ensure_vertical_space(line_height)
            self.current_page.insert_text(
                fitz.Point(self.left_x, self.cursor_y + self.sizes["body"]),
                " ".join(line_words),
                fontsize=self.sizes["body"],
                fontname=self.fonts["regular"],
                color=self.text_rgb,
            )
            self.cursor_y += line_height

    def _render_bullet_item(self, text: str):
        """Renders an indented bullet point with wrapped lines hanging neatly."""
        bullet_symbol = "•"
        bullet_indent = 14.0
        bullet_width = self.content_width - bullet_indent
        line_height = self.sizes["body"] * self.line_mult

        words = text.split()
        if not words:
            return

        # Insert bullet glyph
        self._ensure_vertical_space(line_height)
        self.current_page.insert_text(
            fitz.Point(self.left_x + 2, self.cursor_y + self.sizes["body"]),
            bullet_symbol,
            fontsize=self.sizes["body"],
            fontname=self.fonts["bold"],
            color=self.muted_rgb,
        )

        line_words = []
        is_first_line = True

        for word in words:
            test_line = " ".join(line_words + [word])
            line_w = fitz.get_text_length(test_line, fontname=self.fonts["regular"], fontsize=self.sizes["body"])

            if line_w <= bullet_width:
                line_words.append(word)
            else:
                self._ensure_vertical_space(line_height)
                self.current_page.insert_text(
                    fitz.Point(self.left_x + bullet_indent, self.cursor_y + self.sizes["body"]),
                    " ".join(line_words),
                    fontsize=self.sizes["body"],
                    fontname=self.fonts["regular"],
                    color=self.text_rgb,
                )
                self.cursor_y += line_height
                line_words = [word]
                is_first_line = False

        if line_words:
            self._ensure_vertical_space(line_height)
            self.current_page.insert_text(
                fitz.Point(self.left_x + bullet_indent, self.cursor_y + self.sizes["body"]),
                " ".join(line_words),
                fontsize=self.sizes["body"],
                fontname=self.fonts["regular"],
                color=self.text_rgb,
            )
            self.cursor_y += line_height


def generate_resume_pdf(builder_doc_dict: Dict[str, Any]) -> bytes:
    """Entrypoint function to generate an ATS-oriented vector PDF from builder document state."""
    generator = PDFResumeGenerator(builder_doc_dict)
    return generator.generate()
