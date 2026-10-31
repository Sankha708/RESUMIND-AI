"""Diagnostic Improvement Report PDF Service (Phase 10 — Screen 7).

Generates a comprehensive, professional diagnostic PDF report covering the candidate's
actual ATS Readiness assessment, Job Match evaluation (when present), and AI Improvement
Studio revision history. Never fabricates scores, dates, or requirement matches.
"""

from datetime import datetime, timezone
import io
from typing import Any, Dict, List, Optional
import pymupdf as fitz  # Use the canonical PyMuPDF import; retain fitz namespace internally

PAGE_WIDTH = 595.0
PAGE_HEIGHT = 842.0
MARGIN = 48.0
CONTENT_WIDTH = PAGE_WIDTH - (MARGIN * 2)

# Palette
COLOR_OBSIDIAN = (0.09, 0.10, 0.11)    # #181A1D
COLOR_STEEL_BLUE = (0.33, 0.47, 0.72)  # #5477B8
COLOR_EMERALD = (0.18, 0.50, 0.35)     # #2E7D5A
COLOR_AMBER = (0.72, 0.45, 0.20)       # #B87333
COLOR_MUTED = (0.45, 0.49, 0.55)       # #737D8C
COLOR_LIGHT_BG = (0.95, 0.96, 0.97)    # #F3F5F6
COLOR_BORDER = (0.80, 0.83, 0.87)      # #CCD4DE


class DiagnosticAuditReportGenerator:
    """Renders the comprehensive Diagnostic Improvement Report PDF."""

    def __init__(
        self,
        candidate_name: str,
        session_id: str,
        builder_version: int,
        ats_assessment: Optional[Dict[str, Any]] = None,
        job_match_assessment: Optional[Dict[str, Any]] = None,
        improvement_suggestions: Optional[List[Dict[str, Any]]] = None,
        builder_updated_at: Optional[datetime] = None,
    ):
        self.candidate_name = candidate_name or "Anonymous Candidate"
        self.session_id = session_id
        self.builder_version = builder_version
        self.ats_data = ats_assessment
        self.job_match_data = job_match_assessment
        self.suggestions = improvement_suggestions or []
        self.builder_updated_at = builder_updated_at

        self.pdf = fitz.open()
        self.cursor_y = MARGIN
        self.current_page = self._new_page()

    def _new_page(self) -> fitz.Page:
        page = self.pdf.new_page(width=PAGE_WIDTH, height=PAGE_HEIGHT)
        self.cursor_y = MARGIN
        self._render_page_header(page)
        return page

    def _ensure_space(self, height: float):
        if self.cursor_y + height > (PAGE_HEIGHT - MARGIN):
            self.current_page = self._new_page()

    def _render_page_header(self, page: fitz.Page):
        """Header line on every page."""
        page.insert_text(
            fitz.Point(MARGIN, 32),
            "RESUMIND AI  •  DIAGNOSTIC RESUME AUDIT & ATS INTELLIGENCE REPORT",
            fontsize=8,
            fontname="hebo",
            color=COLOR_MUTED,
        )
        page.draw_line(
            fitz.Point(MARGIN, 36),
            fitz.Point(PAGE_WIDTH - MARGIN, 36),
            color=COLOR_BORDER,
            width=0.5,
        )

    def generate(self) -> bytes:
        """Executes full diagnostic report generation pipeline."""
        self._render_title_block()
        self._render_ats_readiness_section()
        self._render_job_match_section()
        self._render_improvement_studio_summary()
        self._render_disclaimers()

        return self.pdf.tobytes(deflate=True)

    def _render_title_block(self):
        """Executive summary header block."""
        self._ensure_space(80)

        # Main Title
        self.current_page.insert_text(
            fitz.Point(MARGIN, self.cursor_y + 18),
            "Diagnostic Resume Improvement Report",
            fontsize=18,
            fontname="hebo",
            color=COLOR_OBSIDIAN,
        )
        self.cursor_y += 24

        # Meta row
        now_str = datetime.now(timezone.utc).strftime("%B %d, %Y at %H:%M UTC")
        meta_str = (
            f"Candidate: {self.candidate_name}   |   "
            f"Document Version: v{self.builder_version}   |   "
            f"Generated: {now_str}"
        )
        self.current_page.insert_text(
            fitz.Point(MARGIN, self.cursor_y + 10),
            meta_str,
            fontsize=9,
            fontname="helv",
            color=COLOR_MUTED,
        )
        self.cursor_y += 18

        # Check if assessment is historical
        if self.ats_data and self.builder_updated_at:
            ats_created_str = self.ats_data.get("updated_at") or self.ats_data.get("created_at")
            if ats_created_str:
                try:
                    ats_dt = datetime.fromisoformat(str(ats_created_str).replace("Z", "+00:00"))
                    # If builder was updated after assessment
                    if self.builder_updated_at.timestamp() > ats_dt.timestamp():
                        self._render_warning_banner(
                            "Notice: Assessment evaluated an earlier resume snapshot. Recent edits in the Resume Builder may have resolved previous warnings."
                        )
                except (TypeError, ValueError, OverflowError):
                    # An invalid historical timestamp must not hide the diagnostic report.
                    pass

        self.current_page.draw_line(
            fitz.Point(MARGIN, self.cursor_y),
            fitz.Point(PAGE_WIDTH - MARGIN, self.cursor_y),
            color=COLOR_STEEL_BLUE,
            width=1.5,
        )
        self.cursor_y += 16

    def _render_warning_banner(self, text: str):
        """Renders an amber contextual notice."""
        rect = fitz.Rect(MARGIN, self.cursor_y, PAGE_WIDTH - MARGIN, self.cursor_y + 26)
        self.current_page.draw_rect(rect, color=COLOR_AMBER, fill=(0.99, 0.96, 0.92), width=0.5)
        self.current_page.insert_text(
            fitz.Point(MARGIN + 10, self.cursor_y + 16),
            text,
            fontsize=8.5,
            fontname="heit",
            color=COLOR_AMBER,
        )
        self.cursor_y += 34

    def _render_section_title(self, title: str):
        self._ensure_space(35)
        self.current_page.insert_text(
            fitz.Point(MARGIN, self.cursor_y + 13),
            title.upper(),
            fontsize=12,
            fontname="hebo",
            color=COLOR_STEEL_BLUE,
        )
        self.cursor_y += 17
        self.current_page.draw_line(
            fitz.Point(MARGIN, self.cursor_y),
            fitz.Point(PAGE_WIDTH - MARGIN, self.cursor_y),
            color=COLOR_BORDER,
            width=0.75,
        )
        self.cursor_y += 10

    def _render_ats_readiness_section(self):
        """Part A: ATS Mechanical & Linguistic Readiness Assessment."""
        self._render_section_title("Part 1: Mechanical & Structural ATS Readiness")

        if not self.ats_data:
            self._ensure_space(30)
            self.current_page.insert_text(
                fitz.Point(MARGIN, self.cursor_y + 12),
                "No ATS Readiness evaluation has been conducted in this active session.",
                fontsize=9.5,
                fontname="heit",
                color=COLOR_MUTED,
            )
            self.cursor_y += 24
            return

        overall_score = self.ats_data.get("overall_score", 0)
        report_data = self.ats_data.get("report_data", {})
        dimensions = self.ats_data.get("dimension_scores", {})
        warnings = report_data.get("critical_issues", []) + report_data.get("warnings", [])

        # Scorecard box
        self._ensure_space(60)
        box_rect = fitz.Rect(MARGIN, self.cursor_y, PAGE_WIDTH - MARGIN, self.cursor_y + 50)
        self.current_page.draw_rect(box_rect, color=COLOR_BORDER, fill=COLOR_LIGHT_BG, width=0.5)

        # Big score display
        score_color = (
            COLOR_EMERALD if overall_score >= 80 else COLOR_STEEL_BLUE if overall_score >= 60 else COLOR_AMBER
        )
        self.current_page.insert_text(
            fitz.Point(MARGIN + 16, self.cursor_y + 35),
            f"{overall_score}",
            fontsize=26,
            fontname="hebo",
            color=score_color,
        )
        self.current_page.insert_text(
            fitz.Point(MARGIN + 62, self.cursor_y + 24),
            "/ 100 Overall ATS Readiness Score",
            fontsize=10,
            fontname="hebo",
            color=COLOR_OBSIDIAN,
        )

        tier_label = (
            "Optimal Machine Readability (Standard Parsers Supported)"
            if overall_score >= 90
            else "Good Parseability (Minor Structural Anomalies)"
            if overall_score >= 75
            else "Moderate Risk (Complex Formatting or Omissions Detected)"
            if overall_score >= 60
            else "Critical Parsing Risk (High Risk of Data Loss in Legacy ATS)"
        )
        self.current_page.insert_text(
            fitz.Point(MARGIN + 62, self.cursor_y + 38),
            tier_label,
            fontsize=8.5,
            fontname="helv",
            color=COLOR_MUTED,
        )
        self.cursor_y += 62

        # 5 Dimension breakdown table
        self._ensure_space(95)
        self.current_page.insert_text(
            fitz.Point(MARGIN, self.cursor_y + 11),
            "Scoring Dimension Breakdown (Weighted Framework):",
            fontsize=9.5,
            fontname="hebo",
            color=COLOR_OBSIDIAN,
        )
        self.cursor_y += 16

        dim_labels = {
            "file_integrity": ("File & Text Integrity", "25%"),
            "section_taxonomy": ("Section Taxonomy", "20%"),
            "contact": ("Contact Information", "15%"),
            "bullet_impact": ("Bullet Construction & Impact", "25%"),
            "length_hygiene": ("Length & Hygiene", "15%"),
        }

        for dim_key, (dim_name, default_weight_str) in dim_labels.items():
            dim_stat = dimensions.get(dim_key, {})
            score_val = dim_stat.get("score", 0)
            weight_val = dim_stat.get("weight")
            if weight_val is not None:
                weight_str = f"{int(round(float(weight_val) * 100))}%"
            else:
                weight_str = default_weight_str
            weighted_val = dim_stat.get("weighted_score", score_val * (float(weight_val) if weight_val is not None else 0.2))

            self.current_page.insert_text(
                fitz.Point(MARGIN + 10, self.cursor_y + 10),
                f"•  {dim_name} ({weight_str} Weight)",
                fontsize=9,
                fontname="helv",
                color=COLOR_OBSIDIAN,
            )
            score_summary = f"{score_val:.0f}/100  (Weighted: {weighted_val:.1f} pts)"
            self.current_page.insert_text(
                fitz.Point(PAGE_WIDTH - MARGIN - 180, self.cursor_y + 10),
                score_summary,
                fontsize=9,
                fontname="hebo",
                color=COLOR_MUTED,
            )
            self.cursor_y += 14

        self.cursor_y += 8

        # Warnings and Recommendations
        if warnings:
            self._ensure_space(60)
            self.current_page.insert_text(
                fitz.Point(MARGIN, self.cursor_y + 11),
                "Detected ATS Readability Findings & Warnings:",
                fontsize=9.5,
                fontname="hebo",
                color=COLOR_AMBER,
            )
            self.cursor_y += 16

            for w in warnings[:6]:  # Show top findings
                self._ensure_space(20)
                text_clean = w if isinstance(w, str) else str(w.get("message", w))
                self.current_page.insert_text(
                    fitz.Point(MARGIN + 10, self.cursor_y + 10),
                    f"!  {text_clean}",
                    fontsize=8.5,
                    fontname="helv",
                    color=COLOR_OBSIDIAN,
                )
                self.cursor_y += 13

        self.cursor_y += 12

    def _render_job_match_section(self):
        """Part B: Job Match & Target Alignment (Only when real JD assessment exists)."""
        self._render_section_title("Part 2: Job Match & Role Requirement Alignment")

        if not self.job_match_data:
            self._ensure_space(45)
            rect = fitz.Rect(MARGIN, self.cursor_y, PAGE_WIDTH - MARGIN, self.cursor_y + 36)
            self.current_page.draw_rect(rect, color=COLOR_BORDER, fill=COLOR_LIGHT_BG, width=0.5)
            self.current_page.insert_text(
                fitz.Point(MARGIN + 12, self.cursor_y + 15),
                "No target job description was evaluated for this candidate.",
                fontsize=9,
                fontname="hebo",
                color=COLOR_OBSIDIAN,
            )
            self.current_page.insert_text(
                fitz.Point(MARGIN + 12, self.cursor_y + 27),
                "Job match scoring requires semantic evaluation against a specific job posting. Unassessed role match scores are intentionally not fabricated.",
                fontsize=8,
                fontname="heit",
                color=COLOR_MUTED,
            )
            self.cursor_y += 48
            return

        report = self.job_match_data.get("report_data", {})
        job_title = report.get("job_title") or "Target Role"
        overall_score = report.get("overall_score")
        score_withheld = report.get("score_withheld", False)

        self._ensure_space(50)
        self.current_page.insert_text(
            fitz.Point(MARGIN, self.cursor_y + 11),
            f"Target Role: {job_title}",
            fontsize=11,
            fontname="hebo",
            color=COLOR_OBSIDIAN,
        )
        self.cursor_y += 16

        if score_withheld:
            self.current_page.insert_text(
                fitz.Point(MARGIN, self.cursor_y + 10),
                f"Overall Score Withheld: {report.get('withheld_reason', 'Insufficient job description requirements.')}",
                fontsize=9,
                fontname="heit",
                color=COLOR_AMBER,
            )
            self.cursor_y += 18
        elif overall_score is not None:
            self.current_page.insert_text(
                fitz.Point(MARGIN, self.cursor_y + 11),
                f"Semantic Qualification Match: {overall_score:.0f}/100",
                fontsize=11,
                fontname="hebo",
                color=COLOR_EMERALD if overall_score >= 75 else COLOR_STEEL_BLUE,
            )
            self.cursor_y += 18

        # Requirements Counts
        matched_c = report.get("matched_count", 0)
        partial_c = report.get("partial_count", 0)
        gap_c = report.get("gap_count", 0)

        self.current_page.insert_text(
            fitz.Point(MARGIN, self.cursor_y + 10),
            f"Requirements Breakdown: {matched_c} Fully Supported  •  {partial_c} Partially Supported  •  {gap_c} Missing / Unaddressed",
            fontsize=9,
            fontname="helv",
            color=COLOR_OBSIDIAN,
        )
        self.cursor_y += 18

        # Top Recommendations from Job Match
        top_recs = report.get("top_recommendations", [])
        if top_recs:
            self._ensure_space(40)
            self.current_page.insert_text(
                fitz.Point(MARGIN, self.cursor_y + 10),
                "Priority Tailoring Recommendations for this Role:",
                fontsize=9,
                fontname="hebo",
                color=COLOR_OBSIDIAN,
            )
            self.cursor_y += 14
            for rec in top_recs[:4]:
                self._ensure_space(16)
                self.current_page.insert_text(
                    fitz.Point(MARGIN + 10, self.cursor_y + 9),
                    f"→  {rec}",
                    fontsize=8.5,
                    fontname="helv",
                    color=COLOR_MUTED,
                )
                self.cursor_y += 12

        self.cursor_y += 12

    def _render_improvement_studio_summary(self):
        """Part C: AI Improvement Studio Revision Provenance."""
        self._render_section_title("Part 3: Improvement Studio Revisions & Provenance")

        if not self.suggestions:
            self._ensure_space(30)
            self.current_page.insert_text(
                fitz.Point(MARGIN, self.cursor_y + 11),
                "No AI improvement suggestions were recorded in this session.",
                fontsize=9,
                fontname="heit",
                color=COLOR_MUTED,
            )
            self.cursor_y += 24
            return

        accepted = sum(1 for s in self.suggestions if s.get("status") == "accepted")
        pending = sum(1 for s in self.suggestions if s.get("status") == "pending")
        rejected = sum(1 for s in self.suggestions if s.get("status") == "rejected")

        self._ensure_space(40)
        stat_line = (
            f"Total Suggestions Generated: {len(self.suggestions)}   |   "
            f"Accepted & Integrated: {accepted}   |   "
            f"Pending Review: {pending}   |   "
            f"Rejected / Kept Original: {rejected}"
        )
        self.current_page.insert_text(
            fitz.Point(MARGIN, self.cursor_y + 11),
            stat_line,
            fontsize=9,
            fontname="hebo",
            color=COLOR_OBSIDIAN,
        )
        self.cursor_y += 18

        # Sample accepted revisions
        accepted_items = [s for s in self.suggestions if s.get("status") == "accepted"]
        if accepted_items:
            self._ensure_space(30)
            self.current_page.insert_text(
                fitz.Point(MARGIN, self.cursor_y + 10),
                "Verified Accepted Revisions Sample:",
                fontsize=9,
                fontname="hebo",
                color=COLOR_OBSIDIAN,
            )
            self.cursor_y += 14

            for item in accepted_items[:3]:
                self._ensure_space(35)
                orig = item.get("original_text", "")
                rev = item.get("suggested_text", "")
                cat = item.get("category", "Revision")

                self.current_page.insert_text(
                    fitz.Point(MARGIN + 10, self.cursor_y + 9),
                    f"[{cat.upper()}] Accepted Enhancement:",
                    fontsize=8,
                    fontname="hebo",
                    color=COLOR_EMERALD,
                )
                self.cursor_y += 11
                self.current_page.insert_text(
                    fitz.Point(MARGIN + 10, self.cursor_y + 9),
                    f"+ \"{rev[:110]}...\"" if len(rev) > 110 else f"+ \"{rev}\"",
                    fontsize=8,
                    fontname="helv",
                    color=COLOR_OBSIDIAN,
                )
                self.cursor_y += 14

        self.cursor_y += 10

    def _render_disclaimers(self):
        """Honest Limitations & Ethical Disclaimers."""
        self._ensure_space(60)
        self.current_page.draw_line(
            fitz.Point(MARGIN, self.cursor_y),
            fitz.Point(PAGE_WIDTH - MARGIN, self.cursor_y),
            color=COLOR_BORDER,
            width=0.5,
        )
        self.cursor_y += 12

        self.current_page.insert_text(
            fitz.Point(MARGIN, self.cursor_y + 10),
            "Algorithmic Assessment Limitations & Ethical Guardrails:",
            fontsize=8.5,
            fontname="hebo",
            color=COLOR_MUTED,
        )
        self.cursor_y += 14

        disclaimer_text = (
            "1. ATS Readiness evaluates the mechanical, structural, and linguistic parseability of the resume. It does not measure candidate worth or interview eligibility.\n"
            "2. Job Match evaluates textual overlap against an unverified job description. Scores are heuristic indicators, not hiring guarantees.\n"
            "3. RESUMIND AI maintains strict zero-hallucination protocols: metrics or claims must reflect the candidate's genuine verified background."
        )
        for line in disclaimer_text.split("\n"):
            self._ensure_space(12)
            self.current_page.insert_text(
                fitz.Point(MARGIN, self.cursor_y + 8),
                line,
                fontsize=7.5,
                fontname="helv",
                color=COLOR_MUTED,
            )
            self.cursor_y += 11


def generate_diagnostic_audit_report(
    candidate_name: str,
    session_id: str,
    builder_version: int,
    ats_assessment: Optional[Dict[str, Any]] = None,
    job_match_assessment: Optional[Dict[str, Any]] = None,
    improvement_suggestions: Optional[List[Dict[str, Any]]] = None,
    builder_updated_at: Optional[datetime] = None,
) -> bytes:
    """Entrypoint function to generate the PDF Diagnostic Improvement Report."""
    generator = DiagnosticAuditReportGenerator(
        candidate_name=candidate_name,
        session_id=session_id,
        builder_version=builder_version,
        ats_assessment=ats_assessment,
        job_match_assessment=job_match_assessment,
        improvement_suggestions=improvement_suggestions,
        builder_updated_at=builder_updated_at,
    )
    return generator.generate()
