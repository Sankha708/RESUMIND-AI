"""Build evidence-backed comparisons from stored assessments and Builder revisions."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

import pymupdf as fitz

from app.models.assessment import ATSAssessment
from app.models.builder import ResumeBuilderDocument
from app.models.job_match import JobMatchAssessment
from app.models.resume import UploadedResume
from app.schemas.builder import BuilderContent
from app.schemas.reanalysis import (
    ATSReanalysisDelta,
    JobMatchReanalysisDelta,
    ReanalysisDimensionDelta,
    ReanalysisResponse,
    ReanalysisSectionDiff,
)
from app.services.builder_service import convert_structured_profile_to_builder_content
from app.services.job_match_service import evaluate_job_match
from app.services.pdf_export_service import generate_resume_pdf
from app.services.scoring_service import WEIGHTS, calculate_ats_score

SECTION_LABELS = {
    "contact": "Contact",
    "summary": "Professional Summary",
    "experience": "Experience",
    "projects": "Projects",
    "skills": "Skills",
    "education": "Education",
    "certifications": "Certifications",
    "additional": "Additional Information",
}

DIMENSION_LABELS = {
    "file_integrity": "File Integrity",
    "section_taxonomy": "Section Taxonomy",
    "contact": "Contact Information",
    "bullet_impact": "Bullet Impact",
    "length_hygiene": "Length & Hygiene",
}

LIMITATIONS = [
    "ATS Readiness is a deterministic heuristic and does not predict an employer's ATS outcome.",
    "The revised score is calculated from the current Builder PDF; the original score is the saved assessment for the uploaded document.",
    "Job Match checks textual evidence against the saved job description. Candidate-added statements and metrics are not independently verified.",
]


def _as_utc(value: datetime) -> datetime:
    return value.replace(tzinfo=timezone.utc) if value.tzinfo is None else value.astimezone(timezone.utc)


def _is_fresh(assessment_at: datetime, resume_updated_at: datetime) -> bool:
    return _as_utc(assessment_at) >= _as_utc(resume_updated_at)


def _items(value: Any) -> List[Dict[str, Any]]:
    return [entry for entry in (value or []) if isinstance(entry, dict)]


def _clean(value: Any) -> str:
    return str(value or "").strip()


def _join_fields(*values: Any) -> str:
    return " | ".join(_clean(value) for value in values if _clean(value))


def _format_section(content: BuilderContent, key: str) -> str:
    if key == "contact":
        c = content.contact
        return "\n".join(line for line in [
            _clean(c.name), _clean(c.headline), _join_fields(c.email, c.phone, c.location),
            _join_fields(c.website, c.linkedin, c.github),
        ] if line)
    if key == "summary":
        return _clean(content.summary)
    if key == "experience":
        entries = []
        for item in content.experience:
            header = _join_fields(" at ".join(v for v in [_clean(item.role), _clean(item.company)] if v),
                                  item.location, _join_fields(item.start_date, item.end_date or ("Present" if item.current else "")))
            entries.extend(value for value in [header, *item.bullets] if _clean(value))
        return "\n".join(entries)
    if key == "projects":
        entries = []
        for item in content.projects:
            header = _join_fields(item.title, ", ".join(item.tech_stack), item.url,
                                  _join_fields(item.start_date, item.end_date))
            entries.extend(value for value in [header, *item.bullets] if _clean(value))
        return "\n".join(entries)
    if key == "skills":
        return "\n".join(
            _join_fields(item.category, ", ".join(skill.strip() for skill in item.skills if skill.strip()))
            for item in content.skills if item.category.strip() or any(skill.strip() for skill in item.skills)
        )
    if key == "education":
        entries = []
        for item in content.education:
            header = _join_fields(item.degree, item.field_of_study, item.institution,
                                  _join_fields(item.start_date, item.end_date), item.gpa)
            entries.extend(value for value in [header, *item.highlights] if _clean(value))
        return "\n".join(entries)
    if key == "certifications":
        return "\n".join(_join_fields(item.name, item.issuer, item.issue_date, item.expiry_date, item.url)
                         for item in content.certifications if any(_clean(getattr(item, field)) for field in ("name", "issuer", "issue_date", "expiry_date", "url")))
    if key == "additional":
        return "\n".join(
            "\n".join(value for value in [item.section_title.strip(), *item.bullets] if _clean(value))
            for item in content.additional if item.section_title.strip() or any(b.strip() for b in item.bullets)
        )
    return ""


def _changed_sections(
    before: BuilderContent,
    after: BuilderContent,
    visibility: Dict[str, bool],
) -> List[ReanalysisSectionDiff]:
    changes: List[ReanalysisSectionDiff] = []
    for key, label in SECTION_LABELS.items():
        before_text = _format_section(before, key)
        after_text = _format_section(after, key)
        visible_before = True
        visible_after = visibility.get(key, True)
        if before_text != after_text or visible_before != visible_after:
            changes.append(ReanalysisSectionDiff(
                key=key,
                label=label,
                before=before_text if visible_before else "[Section hidden]",
                after=after_text if visible_after else "[Section hidden]",
                change="added" if not before_text and after_text else "removed" if before_text and not after_text else "changed",
                visible_before=visible_before,
                visible_after=visible_after,
            ))
    return changes


def _revision_profile(content: BuilderContent, visibility: Dict[str, bool]) -> Dict[str, Any]:
    """Flatten Builder fields to the scoring engine's established resume profile shape."""
    enabled = lambda key: visibility.get(key, True)
    contact = content.contact.model_dump() if enabled("contact") else {}
    urls = [contact.get(key, "") for key in ("website", "linkedin", "github") if contact.get(key)]
    return {
        "contact": {
            "name": contact.get("name"), "headline": contact.get("headline"),
            "email": contact.get("email"), "phone": contact.get("phone"),
            "location": contact.get("location"), "urls": urls,
        },
        "summary": content.summary if enabled("summary") else "",
        "experience": [line for item in content.experience for line in [
            _join_fields(" at ".join(v for v in [_clean(item.role), _clean(item.company)] if v),
                         item.location, _join_fields(item.start_date, item.end_date or ("Present" if item.current else ""))),
            *item.bullets,
        ] if _clean(line)] if enabled("experience") else [],
        "projects": [line for item in content.projects for line in [
            _join_fields(item.title, ", ".join(item.tech_stack), item.start_date, item.end_date, item.url),
            *item.bullets,
        ] if _clean(line)] if enabled("projects") else [],
        "skills": [skill.strip() for item in content.skills for skill in item.skills if skill.strip()] if enabled("skills") else [],
        "skill_categories": [
            {"category": item.category, "skills": [skill.strip() for skill in item.skills if skill.strip()]}
            for item in content.skills if item.category.strip() and any(skill.strip() for skill in item.skills)
        ] if enabled("skills") else [],
        "education": [line for item in content.education for line in [
            _join_fields(item.degree, item.field_of_study, item.institution, item.start_date, item.end_date, item.gpa),
            *item.highlights,
        ] if _clean(line)] if enabled("education") else [],
        "certifications": [line for item in content.certifications for line in [
            _join_fields(item.name, item.issuer, item.issue_date, item.expiry_date, item.url)
        ] if _clean(line)] if enabled("certifications") else [],
        "other": [line for item in content.additional if item.section_title.strip()
                  for line in [item.section_title, *item.bullets] if _clean(line)] if enabled("additional") else [],
        "warnings": [],
    }


def _valid_baseline_assessment(assessment: ATSAssessment) -> bool:
    if not isinstance(assessment.dimension_scores, dict) or set(assessment.dimension_scores) != set(WEIGHTS):
        return False
    if not isinstance(assessment.report_data, dict):
        return False
    subscores = assessment.report_data.get("subscores")
    if not isinstance(subscores, dict) or set(subscores) != set(WEIGHTS):
        return False
    for key, expected_weight in WEIGHTS.items():
        dimension = assessment.dimension_scores.get(key)
        if not isinstance(dimension, dict):
            return False
        try:
            if abs(float(dimension.get("weight")) - expected_weight) > 0.001:
                return False
            if abs(float(dimension.get("score")) - float(subscores[key]["score"])) > 0.001:
                return False
        except (KeyError, TypeError, ValueError):
            return False
    return True


def _finding_titles(report_data: Dict[str, Any]) -> set[str]:
    findings = report_data.get("prioritized_findings") or []
    return {str(item.get("title")) for item in findings if isinstance(item, dict) and item.get("title")}


def _requirement_counts(report: Any) -> Dict[str, int]:
    counts = {"matched": 0, "partially_supported": 0, "not_demonstrated": 0}
    for item in report.requirements:
        if item.match_status in counts:
            counts[item.match_status] += 1
    return counts


def _locked(reason: str, builder: Optional[ResumeBuilderDocument] = None,
            resume: Optional[UploadedResume] = None) -> ReanalysisResponse:
    return ReanalysisResponse(
        available=False,
        reason=reason,
        builder_version=builder.version if builder else None,
        baseline_resume_id=resume.id if resume else None,
        revised_at=builder.updated_at if builder else None,
        limitations=LIMITATIONS,
    )


def build_reanalysis(
    resume: Optional[UploadedResume],
    baseline: Optional[ATSAssessment],
    builder: Optional[ResumeBuilderDocument],
    job_baseline: Optional[JobMatchAssessment],
) -> ReanalysisResponse:
    """Return a locked state or an authentic baseline versus saved Builder comparison."""
    if not resume:
        return _locked("Upload a resume and run its ATS Readiness assessment to establish a baseline.")
    if not baseline:
        return _locked("No saved baseline assessment exists for this uploaded resume. Run ATS Readiness first.", resume=resume)
    if not _is_fresh(baseline.created_at, resume.updated_at):
        return _locked("The stored assessment predates the last reviewed resume update. Re-run ATS Readiness to refresh the baseline.", resume=resume)
    if not _valid_baseline_assessment(baseline):
        return _locked("The stored baseline does not match the current ATS scoring framework, so scores cannot be compared safely.", resume=resume)
    if not builder:
        return _locked("Save a Builder document based on this uploaded resume to create a revised version.", resume=resume)
    if builder.source_resume_id != resume.id:
        return _locked("The saved Builder document is not linked to the active uploaded resume.", builder, resume)

    before = convert_structured_profile_to_builder_content(resume.structured_data)
    after = BuilderContent.model_validate(builder.content or {})
    changed_sections = _changed_sections(before, after, builder.section_visibility or {})
    if not changed_sections:
        return _locked("No content changes from the uploaded baseline are saved yet. Typography and template settings do not count as a revision.", builder, resume)

    pdf_bytes = generate_resume_pdf({
        "content": after.model_dump(),
        "template_id": "ats_professional",
        "template_config": builder.template_config or {},
        "section_order": builder.section_order or [],
        "section_visibility": builder.section_visibility or {},
    })
    with fitz.open(stream=pdf_bytes, filetype="pdf") as modified_pdf:
        revised_raw_text = "\n".join(page.get_text("text") for page in modified_pdf)
    if len(revised_raw_text.strip()) < 30:
        return _locked("The saved revision does not contain enough visible text to assess. Restore or add resume content first.", builder, resume)

    revised_profile = _revision_profile(after, builder.section_visibility or {})
    revised_ats = calculate_ats_score(
        raw_text=revised_raw_text,
        structured_data=revised_profile,
        file_type="pdf",
        file_size=len(pdf_bytes),
    )
    baseline_dimensions = baseline.dimension_scores
    dimensions = {
        key: ReanalysisDimensionDelta(
            label=DIMENSION_LABELS[key],
            weight=WEIGHTS[key],
            baseline_score=float(baseline_dimensions[key]["score"]),
            revised_score=revised_ats.subscores[key].score,
            delta=round(revised_ats.subscores[key].score - float(baseline_dimensions[key]["score"]), 1),
        )
        for key in WEIGHTS
    }
    baseline_score = float(baseline.overall_score)
    ats_delta = ATSReanalysisDelta(
        baseline_assessment_id=baseline.id,
        baseline_assessment_at=baseline.created_at,
        baseline_score=baseline_score,
        revised_score=revised_ats.overall_score,
        delta=round(revised_ats.overall_score - baseline_score, 1),
        dimensions=dimensions,
    )

    job_delta: Optional[JobMatchReanalysisDelta] = None
    if job_baseline and _is_fresh(job_baseline.created_at, resume.updated_at):
        if job_baseline.score_withheld or job_baseline.overall_score is None:
            job_delta = JobMatchReanalysisDelta(
                job_title=job_baseline.job_title,
                unavailable_reason="The saved baseline Job Match score was withheld because the job description did not provide enough requirements.",
            )
        else:
            revised_job = evaluate_job_match(
                jd_text=job_baseline.job_description_raw,
                raw_text=revised_raw_text,
                structured_data=revised_profile,
            )
            if revised_job.score_withheld or revised_job.overall_score is None:
                job_delta = JobMatchReanalysisDelta(
                    job_title=job_baseline.job_title,
                    baseline_score=job_baseline.overall_score,
                    unavailable_reason=revised_job.withheld_reason or "The revised Job Match score was withheld.",
                )
            else:
                before_counts = _requirement_counts_from_data(job_baseline.report_data)
                after_counts = _requirement_counts(revised_job)
                job_delta = JobMatchReanalysisDelta(
                    job_title=job_baseline.job_title,
                    baseline_score=float(job_baseline.overall_score),
                    revised_score=revised_job.overall_score,
                    delta=round(revised_job.overall_score - float(job_baseline.overall_score), 1),
                    matched_before=before_counts["matched"],
                    matched_after=after_counts["matched"],
                    partially_supported_before=before_counts["partially_supported"],
                    partially_supported_after=after_counts["partially_supported"],
                    not_demonstrated_before=before_counts["not_demonstrated"],
                    not_demonstrated_after=after_counts["not_demonstrated"],
                )

    resolved = sorted(_finding_titles(baseline.report_data) - _finding_titles(revised_ats.model_dump()))
    return ReanalysisResponse(
        available=True,
        builder_version=builder.version,
        baseline_resume_id=resume.id,
        revised_at=builder.updated_at,
        ats=ats_delta,
        job_match=job_delta,
        changed_sections=changed_sections,
        resolved_findings=resolved,
        limitations=LIMITATIONS,
    )


def _requirement_counts_from_data(report_data: Dict[str, Any]) -> Dict[str, int]:
    counts = {"matched": 0, "partially_supported": 0, "not_demonstrated": 0}
    for item in (report_data.get("requirements") or []):
        if isinstance(item, dict) and item.get("match_status") in counts:
            counts[item["match_status"]] += 1
    return counts
