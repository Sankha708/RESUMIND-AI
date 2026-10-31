"""Deterministic ATS-Readiness Scoring Engine.

Implements pure, explainable, and reproducible heuristic scoring across
the 5 approved dimensions:
  1. File Integrity (25%)
  2. Section Taxonomy (20%)
  3. Contact Information (15%)
  4. Bullet Impact (25%)
  5. Length & Hygiene (15%)

Zero AI hallucinations, zero metric fabrication, and zero reliance on external
APIs, Ollama, or job descriptions.
"""

from __future__ import annotations

import re
from typing import Any, Dict, List, Optional, Set
from pydantic import BaseModel, Field

# ── Approved Scoring Framework Weights (LOCKED) ─────────────────────────────
WEIGHTS: Dict[str, float] = {
    "file_integrity": 0.25,
    "section_taxonomy": 0.20,
    "contact": 0.15,
    "bullet_impact": 0.25,
    "length_hygiene": 0.15,
}

DISCLAIMER: str = (
    "This assessment is RESUMIND AI's heuristic ATS-readiness estimate based on "
    "consensus parsing standards and machine readability guidelines. It does not "
    "guarantee any employer's ATS outcome, ranking, or interview invitation."
)

# ── Curated Action Verbs & Weak Starters ──────────────────────────────────────
ACTION_VERBS: Set[str] = {
    "accelerated", "accomplished", "achieved", "acquired", "adapted", "administered",
    "advanced", "advised", "advocated", "aligned", "allocated", "analyzed", "architected",
    "authored", "automated", "boosted", "briefed", "budgeted", "built", "calculated",
    "centralized", "championed", "coached", "collaborated", "compiled", "composed",
    "conceived", "conducted", "configured", "consolidated", "constructed", "consulted",
    "converted", "coordinated", "counseled", "created", "cultivated", "customized",
    "debugged", "decreased", "defined", "delegated", "delivered", "demonstrated",
    "deployed", "designed", "developed", "devised", "diagnosed", "directed", "discovered",
    "documented", "doubled", "drafted", "drove", "eliminated", "enabled", "enacted",
    "engineered", "enhanced", "established", "evaluated", "examined", "executed",
    "expanded", "expedited", "facilitated", "formulated", "founded", "generated",
    "governed", "guided", "halted", "headed", "identified", "implemented", "improved",
    "improvised", "increased", "indexed", "influenced", "initiated", "innovated",
    "inspected", "installed", "instituted", "instructed", "integrated", "introduced",
    "invented", "investigated", "launched", "lead", "led", "leveraged", "managed",
    "mapped", "maximized", "measured", "mentored", "migrated", "minimized", "modeled",
    "modernized", "monitored", "negotiated", "operated", "optimized", "orchestrated",
    "organized", "originated", "overhauled", "oversaw", "partnered", "performed",
    "piloted", "pioneered", "planned", "prepared", "presented", "programmed", "produced",
    "promoted", "proposed", "published", "rebuilt", "redesigned", "reduced", "refined",
    "refactored", "regulated", "remodeled", "reorganized", "repaired", "replaced",
    "researched", "resolved", "restructured", "revamped", "reviewed", "revitalized",
    "routed", "scaled", "scheduled", "secured", "selected", "separated", "simplified",
    "simulated", "spearheaded", "standardized", "streamlined", "strengthened", "structured",
    "supervised", "surpassed", "synthesized", "systematized", "tested", "tracked",
    "trained", "transformed", "transitioned", "translated", "troubleshot", "unified",
    "upgraded", "utilized", "validated", "visualized", "won", "wrote",
}

PASSIVE_STARTERS: List[str] = [
    "responsible for", "duties included", "helped with", "assisted in", "assisted with",
    "worked on", "handled", "participated in", "tasked with", "involved in", "served as",
    "contributed to",
]

# Patterns for measurable impact: numbers, percentages, currency, scale
METRIC_REGEX = re.compile(
    r"(?:\b\d+(?:[\.,]\d+)?%|\$\s*\d+(?:[\.,]\d+)?(?:\s*[kKmMbB])?|"
    r"\b\d+(?:[\.,]\d+)?\s*(?:k|m|million|billion|users|clients|requests|ms|seconds|minutes|hours|days|x|fold)\b|"
    r"\b(?:reduced|increased|improved|boosted|saved|grew)\s+by\s+\d+)",
    re.IGNORECASE,
)

# Standard regexes for validation
EMAIL_REGEX = re.compile(r"^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$")
PHONE_DIGITS_REGEX = re.compile(r"\d")


# ── Report Schema Types ──────────────────────────────────────────────────────
class Finding(BaseModel):
    """Specific diagnostic finding tied to extracted resume content."""
    severity: str = Field(..., description="'critical', 'warning', or 'positive'")
    title: str
    message: str
    evidence: Optional[str] = None


class DimensionResult(BaseModel):
    """Result for an individual scoring dimension (0-100 scale)."""
    score: float = Field(..., ge=0.0, le=100.0)
    weight: float
    weighted_score: float
    strengths: List[str] = Field(default_factory=list)
    findings: List[Finding] = Field(default_factory=list)


class ATSReport(BaseModel):
    """Complete explainable ATS readiness evaluation report."""
    overall_score: float = Field(..., ge=0.0, le=100.0)
    subscores: Dict[str, DimensionResult]
    top_strengths: List[str] = Field(default_factory=list)
    prioritized_findings: List[Finding] = Field(default_factory=list)
    limitations: List[str] = Field(default_factory=list)
    disclaimer: str = DISCLAIMER


# ── Dimension 1: File Integrity (25%) ─────────────────────────────────────────
def evaluate_file_integrity(
    raw_text: str,
    file_type: str,
    file_size: int,
    warnings: List[str],
) -> DimensionResult:
    """Evaluates mechanical text extraction quality and document integrity."""
    strengths: List[str] = []
    findings: List[Finding] = []
    score = 100.0

    raw_len = len(raw_text.strip())

    # 1. Critical empty / scanned document check
    is_scanned = any("scanned" in w.lower() or "image-only" in w.lower() for w in warnings)
    if is_scanned or raw_len < 30:
        score = 15.0
        findings.append(
            Finding(
                severity="critical",
                title="Unreadable or Scanned Document Layer",
                message="No selectable text layer was extracted. Standard applicant tracking systems require native text rather than scanned images.",
                evidence=warnings[0] if warnings else "Extracted text length < 30 characters.",
            )
        )
        return DimensionResult(
            score=round(score, 1),
            weight=WEIGHTS["file_integrity"],
            weighted_score=round(score * WEIGHTS["file_integrity"], 1),
            strengths=strengths,
            findings=findings,
        )

    # 2. Text extractability score base
    if raw_len >= 200:
        strengths.append(f"Clean, selectable text layer extracted successfully ({raw_len:,} characters).")
    elif raw_len >= 80:
        score -= 20.0
        findings.append(
            Finding(
                severity="warning",
                title="Low Extracted Text Volume",
                message="The document yielded a relatively short text layer. Ensure all sections are written as selectable text rather than images or icons.",
                evidence=f"{raw_len} total characters extracted.",
            )
        )
    else:
        score -= 50.0
        findings.append(
            Finding(
                severity="critical",
                title="Minimal Text Content",
                message="Very little text could be recovered from this document.",
                evidence=f"{raw_len} characters extracted.",
            )
        )

    # 3. File type check
    file_type_norm = file_type.lower().replace(".", "")
    if file_type_norm in ["pdf", "docx"]:
        strengths.append(f"Format ({file_type_norm.upper()}) is natively supported by modern parser engines.")
    else:
        score -= 25.0
        findings.append(
            Finding(
                severity="critical",
                title="Non-Standard File Extension",
                message=f"File extension '{file_type}' may be rejected by strict corporate parsers.",
                evidence=file_type,
            )
        )

    # 4. Text-to-filesize density check
    if file_size > 0:
        chars_per_kb = raw_len / (file_size / 1024.0)
        if chars_per_kb < 0.1 and file_size > 500 * 1024:
            score -= 15.0
            findings.append(
                Finding(
                    severity="warning",
                    title="Heavy File Payload vs. Text Content",
                    message="Document file size is large relative to the extracted text. This typically indicates embedded background images, vectors, or graphics that can confuse legacy ATS engines.",
                    evidence=f"File size {file_size // 1024} KB with {raw_len} characters.",
                )
            )

    # 5. Line/paragraph segmentation check
    lines = [line.strip() for line in raw_text.splitlines() if line.strip()]
    if len(lines) < 5 and raw_len > 200:
        score -= 20.0
        findings.append(
            Finding(
                severity="warning",
                title="Unsegmented Text Flow",
                message="Text appears as a continuous block without line breaks. Ensure paragraphs and bullets use standard return breaks.",
            )
        )
    else:
        strengths.append("Standard line and paragraph delimiters recognized.")

    # 6. Parser warnings check
    for w in warnings:
        if "scanned" not in w.lower():  # already handled
            findings.append(
                Finding(
                    severity="warning",
                    title="Parser Diagnostic Notice",
                    message=w,
                )
            )

    final_score = max(0.0, min(100.0, score))
    return DimensionResult(
        score=round(final_score, 1),
        weight=WEIGHTS["file_integrity"],
        weighted_score=round(final_score * WEIGHTS["file_integrity"], 1),
        strengths=strengths,
        findings=findings,
    )


# ── Dimension 2: Section Taxonomy (20%) ───────────────────────────────────────
def evaluate_section_taxonomy(
    structured_data: Dict[str, Any],
) -> DimensionResult:
    """Evaluates standard section header recognition and structure."""
    strengths: List[str] = []
    findings: List[Finding] = []
    score = 0.0

    exp = structured_data.get("experience") or []
    edu = structured_data.get("education") or []
    skills = structured_data.get("skills") or []
    proj = structured_data.get("projects") or []
    cert = structured_data.get("certifications") or []
    summary = structured_data.get("summary")
    other = structured_data.get("other") or []

    # 1. Experience or Projects (Primary Work Demonstration) - Up to 35 pts
    if len(exp) > 0:
        score += 35.0
        strengths.append(f"Recognized 'Experience' section with {len(exp)} extracted entries.")
    elif len(proj) > 0:
        # Early-career / Student parity: give equal primary credit for projects
        score += 35.0
        strengths.append(f"Recognized 'Projects' section with {len(proj)} project entries (valid portfolio alternative to traditional experience).")
    else:
        findings.append(
            Finding(
                severity="critical",
                title="Missing Work Experience or Projects Section",
                message="No distinct 'Experience', 'Work History', or 'Projects' heading was recognized. This is the most heavily inspected section in candidate screening.",
            )
        )

    # 2. Education - Up to 25 pts
    if len(edu) > 0:
        score += 25.0
        strengths.append(f"Recognized 'Education' section with {len(edu)} credential entries.")
    else:
        findings.append(
            Finding(
                severity="warning",
                title="Missing Education Section",
                message="No recognized 'Education' heading was identified. Many automated filters check for degree or institution names.",
            )
        )

    # 3. Skills - Up to 25 pts
    if len(skills) > 0:
        score += 25.0
        strengths.append(f"Recognized 'Skills' taxonomy with {len(skills)} identified skill items.")
    else:
        findings.append(
            Finding(
                severity="warning",
                title="Missing Dedicated Skills Section",
                message="No dedicated 'Skills' or 'Technical Proficiencies' section was recognized. A distinct skills section maximizes keyword indexing.",
            )
        )

    # 4. Summary / Profile - Up to 10 pts
    if summary and len(summary.strip()) > 20:
        score += 10.0
        strengths.append("Professional Summary / Profile header recognized.")

    # 5. Certifications or Supplemental Projects - Up to 5 pts
    if len(cert) > 0:
        score += 5.0
        strengths.append(f"Recognized 'Certifications' section with {len(cert)} credentials.")
    elif len(proj) > 0 and len(exp) > 0:
        score += 5.0
        strengths.append(f"Supplemental 'Projects' section recognized alongside Experience.")

    # 6. Unclassified / Other sections inspection
    if len(other) > 0:
        sample = other[0][:80] + ("..." if len(other[0]) > 80 else "")
        findings.append(
            Finding(
                severity="warning",
                title="Unclassified Content Detected",
                message=f"Found {len(other)} entries under non-standard or unrecognized section headings. Consider using standard headers like 'Summary', 'Experience', 'Education', 'Projects', or 'Skills'.",
                evidence=f"Example: \"{sample}\"",
            )
        )

    final_score = max(0.0, min(100.0, score))
    return DimensionResult(
        score=round(final_score, 1),
        weight=WEIGHTS["section_taxonomy"],
        weighted_score=round(final_score * WEIGHTS["section_taxonomy"], 1),
        strengths=strengths,
        findings=findings,
    )


# ── Dimension 3: Contact Information (15%) ────────────────────────────────────
def evaluate_contact_information(
    structured_data: Dict[str, Any],
) -> DimensionResult:
    """Evaluates candidate contact details completeness and parseability."""
    strengths: List[str] = []
    findings: List[Finding] = []
    score = 0.0

    contact = structured_data.get("contact") or {}
    name = (contact.get("name") or "").strip()
    email = (contact.get("email") or "").strip()
    phone = (contact.get("phone") or "").strip()
    urls = contact.get("urls") or []
    location = (contact.get("location") or "").strip()
    uncertainty = contact.get("uncertainty") or {}

    # 1. Email (35 pts)
    if email and EMAIL_REGEX.match(email):
        score += 35.0
        # Privacy-preserving confirmation: do not expose raw email
        domain = email.split("@")[-1]
        strengths.append(f"Valid, RFC-compliant email address verified (@{domain}).")
    elif email:
        score += 15.0
        findings.append(
            Finding(
                severity="warning",
                title="Potentially Malformed Email",
                message="An email was extracted but its format may be non-standard.",
            )
        )
    else:
        findings.append(
            Finding(
                severity="critical",
                title="Missing Contact Email",
                message="No valid email address was detected. ATS systems require a verified email to create and index applicant records.",
            )
        )

    # 2. Phone (25 pts)
    phone_digits = len(PHONE_DIGITS_REGEX.findall(phone)) if phone else 0
    if phone and phone_digits >= 7:
        score += 25.0
        strengths.append("Standard contact telephone number identified.")
    elif phone:
        score += 10.0
        findings.append(
            Finding(
                severity="warning",
                title="Incomplete Phone Number",
                message="Extracted phone number has fewer digits than standard international or domestic formats.",
            )
        )
    else:
        findings.append(
            Finding(
                severity="warning",
                title="Missing Telephone Number",
                message="No telephone number was identified. Providing a direct phone line improves recruiter contact rate.",
            )
        )

    # 3. Name (20 pts)
    name_uncertain = uncertainty.get("name", False)
    if name and len(name) >= 2 and not name_uncertain:
        score += 20.0
        strengths.append("Candidate name identified with high parser confidence.")
    elif name and len(name) >= 2:
        score += 10.0
        findings.append(
            Finding(
                severity="warning",
                title="Candidate Name Confidence Flag",
                message="The candidate name position is ambiguous or positioned near other title text. Ensure your name is the topmost heading in the document.",
            )
        )
    else:
        findings.append(
            Finding(
                severity="critical",
                title="Missing Candidate Name",
                message="Could not clearly isolate the candidate's name at the top of the resume.",
            )
        )

    # 4. Professional Links / URLs (15 pts)
    if len(urls) > 0:
        score += 15.0
        has_linkedin = any("linkedin" in u.lower() for u in urls)
        has_github = any("github" in u.lower() for u in urls)
        if has_linkedin and has_github:
            strengths.append("Both LinkedIn and GitHub professional profile links detected.")
        elif has_linkedin:
            strengths.append("Professional LinkedIn profile link detected.")
        elif has_github:
            strengths.append("Technical GitHub / portfolio link detected.")
        else:
            strengths.append(f"Professional web URL detected ({len(urls)} link{'s' if len(urls) > 1 else ''}).")
    else:
        findings.append(
            Finding(
                severity="warning",
                title="No Professional Profiles Detected",
                message="No LinkedIn, GitHub, or online portfolio URL was found. Adding a verified LinkedIn or portfolio URL provides immediate external evidence of your background.",
            )
        )

    # 5. Location (5 pts bonus)
    if location and len(location) >= 2:
        score += 5.0
        strengths.append("Geographic location / city detected.")

    final_score = max(0.0, min(100.0, score))
    return DimensionResult(
        score=round(final_score, 1),
        weight=WEIGHTS["contact"],
        weighted_score=round(final_score * WEIGHTS["contact"], 1),
        strengths=strengths,
        findings=findings,
    )


# ── Dimension 4: Bullet Construction & Impact (25%) ───────────────────────────
def evaluate_bullet_impact(
    structured_data: Dict[str, Any],
) -> DimensionResult:
    """Evaluates action verbs, quantifiable metrics, and statement structure.
    
    Treats projects and experience equally so students and career-transitioners
    are not penalized unfairly.
    """
    strengths: List[str] = []
    findings: List[Finding] = []

    exp_items: List[str] = structured_data.get("experience") or []
    proj_items: List[str] = structured_data.get("projects") or []

    all_bullets = [b.strip() for b in (exp_items + proj_items) if b.strip()]

    # Filter out pure date/company header lines (e.g. lines with < 4 words)
    candidate_bullets = [b for b in all_bullets if len(b.split()) >= 4]

    # Boundary: No bullets available
    if not candidate_bullets:
        return DimensionResult(
            score=20.0,
            weight=WEIGHTS["bullet_impact"],
            weighted_score=round(20.0 * WEIGHTS["bullet_impact"], 1),
            strengths=[],
            findings=[
                Finding(
                    severity="critical",
                    title="No Descriptive Experience or Project Bullets",
                    message="Could not identify descriptive bullet statements in either the Experience or Projects sections. ATS algorithms look for bulleted accomplishments to score experience relevance.",
                )
            ],
        )

    total_count = len(candidate_bullets)
    action_verb_count = 0
    metric_count = 0
    passive_count = 0
    too_short_count = 0
    too_long_count = 0
    first_words: List[str] = []

    for bullet in candidate_bullets:
        words = [w.strip(".,;:•-–—()[]*\"'") for w in bullet.split()]
        words = [w for w in words if w]
        if not words:
            continue

        first_word = words[0].lower()
        first_words.append(first_word)
        word_count = len(words)

        # 1. Action verb check
        if first_word in ACTION_VERBS:
            action_verb_count += 1

        # 2. Passive start check
        lower_bullet = bullet.lower()
        if any(lower_bullet.startswith(p) for p in PASSIVE_STARTERS):
            passive_count += 1

        # 3. Measurable metrics check
        if METRIC_REGEX.search(bullet):
            metric_count += 1

        # 4. Length checks
        if word_count < 8:
            too_short_count += 1
        elif word_count > 50:
            too_long_count += 1

    action_ratio = action_verb_count / total_count
    metric_ratio = metric_count / total_count

    # Calculate subscore out of 100:
    # - Action verbs ratio: up to 40 pts (target >= 65%)
    # - Metrics presence ratio: up to 30 pts (target >= 30%)
    # - Bullet length / readability: up to 20 pts (penalize excessive short/long)
    # - Absence of passive starters: up to 10 pts
    score = 0.0

    # Action verbs (40 pts max)
    verb_points = min(40.0, (action_ratio / 0.65) * 40.0)
    score += verb_points

    if action_ratio >= 0.60:
        strengths.append(f"Strong action-verb front-loading: {int(action_ratio * 100)}% of bullets start with direct impact verbs.")
    elif action_ratio >= 0.35:
        findings.append(
            Finding(
                severity="warning",
                title="Moderate Action Verb Density",
                message=f"Only {int(action_ratio * 100)}% of statements begin with active verbs. Aim to start at least 65% of bullet points with strong verbs (e.g., 'Engineered', 'Orchestrated', 'Optimized').",
            )
        )
    else:
        findings.append(
            Finding(
                severity="critical",
                title="Low Action Verb Density",
                message=f"Only {int(action_ratio * 100)}% of bullet points begin with active verbs. Front-load bullets with direct action verbs rather than passive task descriptions.",
            )
        )

    # Metrics / Specificity (30 pts max) - Do NOT require metrics in every bullet!
    metric_points = min(30.0, (metric_ratio / 0.30) * 30.0)
    score += metric_points

    if metric_ratio >= 0.30:
        strengths.append(f"Excellent quantifiable impact: {int(metric_ratio * 100)}% of statements include measurable metrics, percentages, or scale.")
    elif metric_ratio >= 0.15:
        strengths.append(f"Quantifiable evidence detected in {int(metric_ratio * 100)}% of bullet points.")
        findings.append(
            Finding(
                severity="warning",
                title="Opportunity for More Quantifiable Results",
                message=f"Found quantifiable metrics in {metric_count} of {total_count} bullets. Where possible, add numbers, percentages, volume, or time savings to substantiate outcomes.",
            )
        )
    else:
        findings.append(
            Finding(
                severity="warning",
                title="Low Quantifiable Metrics",
                message=f"Only {int(metric_ratio * 100)}% of bullets include measurable figures or scale indicators. Substantive results (e.g., 'improved by 20%', 'supported 10k users') improve recruiter traction.",
            )
        )

    # Readability / Length (20 pts max)
    length_penalty = 0.0
    if too_short_count > 0:
        length_penalty += min(10.0, (too_short_count / total_count) * 20.0)
    if too_long_count > 0:
        length_penalty += min(10.0, (too_long_count / total_count) * 20.0)

    score += max(0.0, 20.0 - length_penalty)

    if too_long_count > 0:
        findings.append(
            Finding(
                severity="warning",
                title="Overly Dense Bullet Statements",
                message=f"{too_long_count} statement{'s' if too_long_count > 1 else ''} exceed 50 words. Break long run-on sentences into distinct bullets for faster parser and recruiter skimming.",
            )
        )
    if too_short_count > 0 and (too_short_count / total_count) > 0.3:
        findings.append(
            Finding(
                severity="warning",
                title="Vague or Abbreviated Bullets",
                message=f"{too_short_count} bullet{'s are' if too_short_count > 1 else ' is'} under 8 words. Expand on your scope, methods, and results.",
            )
        )
    if too_long_count == 0 and too_short_count <= 1:
        strengths.append("Well-calibrated bullet lengths (typically 10–40 words per statement).")

    # Passive Starters (10 pts max)
    if passive_count == 0:
        score += 10.0
        strengths.append("Zero passive starter phrases ('Responsible for', 'Worked on') detected.")
    else:
        score += max(0.0, 10.0 - (passive_count * 3.0))
        findings.append(
            Finding(
                severity="warning",
                title="Passive Starter Phrases Detected",
                message=f"Detected {passive_count} bullet{'s' if passive_count > 1 else ''} beginning with passive phrases like 'Responsible for' or 'Helped with'. Replace with direct verbs showing what you actually delivered.",
            )
        )

    # Repetitive opening words check
    word_freq: Dict[str, int] = {}
    for w in first_words:
        word_freq[w] = word_freq.get(w, 0) + 1
    repeated = [(w, c) for w, c in word_freq.items() if c >= 3 and w in ACTION_VERBS]
    if repeated:
        rep_verb, rep_count = repeated[0]
        findings.append(
            Finding(
                severity="warning",
                title="Repetitive Action Verbs",
                message=f"The verb '{rep_verb.capitalize()}' is used to start {rep_count} different bullets. Diversify your vocabulary with synonyms.",
            )
        )

    final_score = max(0.0, min(100.0, score))
    return DimensionResult(
        score=round(final_score, 1),
        weight=WEIGHTS["bullet_impact"],
        weighted_score=round(final_score * WEIGHTS["bullet_impact"], 1),
        strengths=strengths,
        findings=findings,
    )


# ── Dimension 5: Length & Hygiene (15%) ────────────────────────────────────────
def evaluate_length_and_hygiene(
    raw_text: str,
    structured_data: Dict[str, Any],
) -> DimensionResult:
    """Evaluates document length sanity, duplicate lines, and structural hygiene."""
    strengths: List[str] = []
    findings: List[Finding] = []
    score = 100.0

    lines = [line.strip() for line in raw_text.splitlines() if line.strip()]
    content_lines = [l for l in lines if not l.startswith("--- Page Break")]
    words = raw_text.split()
    total_words = len(words)

    # 1. Total word count sanity check
    if 250 <= total_words <= 1200:
        strengths.append(f"Balanced document length: {total_words:,} words (standard 1–2 page budget).")
    elif total_words < 150:
        score -= 40.0
        findings.append(
            Finding(
                severity="critical",
                title="Significantly Under-Length Resume",
                message=f"Document contains only {total_words} words. Standard resumes provide 300–800 words detailing background, technologies, and achievements.",
            )
        )
    elif total_words < 250:
        score -= 20.0
        findings.append(
            Finding(
                severity="warning",
                title="Brief Content Volume",
                message=f"Total word count ({total_words} words) is on the lower side. Consider expanding upon key projects or skills.",
            )
        )
    elif total_words > 2200:
        score -= 25.0
        findings.append(
            Finding(
                severity="warning",
                title="Overly Verbose Document",
                message=f"Document contains {total_words:,} words. Resumes exceeding 2,000 words risk candidate drop-off and parser truncations.",
            )
        )
    else:
        strengths.append(f"Document contains {total_words:,} words.")

    # 2. Duplicate line / sentence check (copy-paste artifact or header stamp)
    seen_lines: Dict[str, int] = {}
    for line in content_lines:
        # Ignore short headers or numbers
        if len(line) >= 20:
            norm = line.lower()
            seen_lines[norm] = seen_lines.get(norm, 0) + 1

    duplicate_lines = [line for line, count in seen_lines.items() if count >= 2]
    if duplicate_lines:
        score -= min(25.0, len(duplicate_lines) * 10.0)
        sample = duplicate_lines[0][:75] + ("..." if len(duplicate_lines[0]) > 75 else "")
        findings.append(
            Finding(
                severity="warning",
                title="Duplicate Text Lines Detected",
                message=f"Found {len(duplicate_lines)} text line{'s' if len(duplicate_lines) > 1 else ''} repeated across the document. Remove duplicate bullets or overlapping header lines.",
                evidence=f"Example: \"{sample}\"",
            )
        )
    else:
        strengths.append("No repetitive or duplicated text lines detected.")

    # 3. Giant unbroken blocks (> 1000 characters with no line breaks)
    paragraphs = raw_text.split("\n\n")
    dense_paragraphs = [p for p in paragraphs if len(p.strip()) > 900]
    if dense_paragraphs:
        score -= min(20.0, len(dense_paragraphs) * 10.0)
        findings.append(
            Finding(
                severity="warning",
                title="Dense Unbroken Paragraph Blocks",
                message=f"Detected {len(dense_paragraphs)} unbroken block{'s' if len(dense_paragraphs) > 1 else ''} exceeding 900 characters. Break dense prose into readable bullet points.",
            )
        )
    else:
        strengths.append("Healthy paragraph sizing and spacing throughout.")

    # 4. Page Break hygiene check (if page breaks detected)
    page_break_count = raw_text.count("--- Page Break ---")
    if page_break_count > 0:
        page_count = page_break_count + 1
        if page_count <= 2:
            strengths.append(f"Clean page budget: {page_count} page{'s' if page_count > 1 else ''}.")
        elif page_count >= 4:
            score -= 15.0
            findings.append(
                Finding(
                    severity="warning",
                    title="High Page Count",
                    message=f"Document spans {page_count} pages. Standard industry practice is 1–2 pages for most professionals, or 3 pages for senior executive/academic CVs.",
                )
            )

    final_score = max(0.0, min(100.0, score))
    return DimensionResult(
        score=round(final_score, 1),
        weight=WEIGHTS["length_hygiene"],
        weighted_score=round(final_score * WEIGHTS["length_hygiene"], 1),
        strengths=strengths,
        findings=findings,
    )


# ── Primary ATS Scoring Function ──────────────────────────────────────────────
def calculate_ats_score(
    raw_text: str,
    structured_data: Dict[str, Any],
    file_type: str = "pdf",
    file_size: int = 0,
) -> ATSReport:
    """Computes transparent, deterministic ATS readiness score across 5 dimensions.
    
    Returns:
        ATSReport containing overall score, 5 subscores, prioritized findings,
        strengths, and limitations.
    """
    warnings: List[str] = structured_data.get("warnings") or []

    # 1. Evaluate individual dimensions
    res_integrity = evaluate_file_integrity(raw_text, file_type, file_size, warnings)
    res_taxonomy = evaluate_section_taxonomy(structured_data)
    res_contact = evaluate_contact_information(structured_data)
    res_impact = evaluate_bullet_impact(structured_data)
    res_hygiene = evaluate_length_and_hygiene(raw_text, structured_data)

    subscores: Dict[str, DimensionResult] = {
        "file_integrity": res_integrity,
        "section_taxonomy": res_taxonomy,
        "contact": res_contact,
        "bullet_impact": res_impact,
        "length_hygiene": res_hygiene,
    }

    # 2. Compute overall score as exact weighted sum
    overall = (
        res_integrity.weighted_score
        + res_taxonomy.weighted_score
        + res_contact.weighted_score
        + res_impact.weighted_score
        + res_hygiene.weighted_score
    )
    overall_score = max(0.0, min(100.0, round(overall, 1)))

    # 3. Aggregate top strengths
    all_strengths: List[str] = []
    for dim_res in subscores.values():
        all_strengths.extend(dim_res.strengths)
    # Pick up to top 6 strengths
    top_strengths = all_strengths[:6]

    # 4. Aggregate and prioritize findings: Critical first, then Warning
    all_findings: List[Finding] = []
    for dim_res in subscores.values():
        all_findings.extend(dim_res.findings)

    severity_order = {"critical": 0, "warning": 1, "positive": 2}
    prioritized_findings = sorted(
        all_findings,
        key=lambda f: severity_order.get(f.severity, 3),
    )

    # 5. Document limitations and confidence warnings
    limitations: List[str] = []
    if any(f.severity == "critical" for f in all_findings):
        limitations.append(
            "Critical structural or extraction barriers detected. Addressing these will yield the largest score improvements."
        )
    if not (structured_data.get("experience") or structured_data.get("projects")):
        limitations.append(
            "Bullet impact evaluation was limited due to absence of identifiable experience or project statements."
        )
    limitations.append(
        "Heuristic analysis does not evaluate role-specific job alignment (available separately in Job Match mode)."
    )

    return ATSReport(
        overall_score=overall_score,
        subscores=subscores,
        top_strengths=top_strengths,
        prioritized_findings=prioritized_findings,
        limitations=limitations,
        disclaimer=DISCLAIMER,
    )
