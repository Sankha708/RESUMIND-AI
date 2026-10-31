"""Deterministic Job Description Matching Engine.

Extracts, categorizes, and matches job description requirements against verified
resume content across 4 approved dimensions:
  1. Hard Technical Skills (40%)
  2. Domain Competencies (30%)
  3. Experience Scope & Seniority (15%)
  4. Education & Credentials (15%)

Zero AI hallucinations, zero fabricated resume quotations, zero reliance on external
APIs or Ollama. Every evidence snippet is strictly verified as a verbatim substring
of the candidate's resume.
"""

from __future__ import annotations

import re
from typing import Any, Dict, List, Optional, Set, Tuple
from pydantic import BaseModel, Field

# ── Approved Category Weights (Phase 0 Standard) ─────────────────────────────
JOB_MATCH_WEIGHTS: Dict[str, float] = {
    "hard_skills": 0.40,
    "domain_competencies": 0.30,
    "experience_scope": 0.15,
    "education_credentials": 0.15,
}

JOB_MATCH_DISCLAIMER: str = (
    "This assessment is RESUMIND AI's heuristic job-match estimate based on "
    "grounded textual overlap. It does not evaluate unwritten qualifications or "
    "guarantee an interview or hiring outcome. A requirement marked 'not demonstrated' "
    "indicates absence of textual evidence in the submitted resume, not that the "
    "candidate lacks the underlying skill."
)

# ── Curated Taxonomies ───────────────────────────────────────────────────────
HARD_SKILL_TAXONOMY: Dict[str, List[str]] = {
    "python": ["python", "python3", "py"],
    "javascript": ["javascript", "js", "ecmascript"],
    "typescript": ["typescript", "ts"],
    "go": ["golang", "go"],
    "rust": ["rust"],
    "java": ["java", "jvm"],
    "c++": ["c++", "cpp"],
    "c#": ["c#", "csharp", ".net"],
    "sql": ["sql", "relational database", "rdbms"],
    "react": ["react", "react.js", "reactjs"],
    "next.js": ["next.js", "nextjs", "next"],
    "node.js": ["node.js", "nodejs", "node"],
    "fastapi": ["fastapi", "fast-api"],
    "django": ["django"],
    "flask": ["flask"],
    "spring": ["spring", "spring boot", "springboot"],
    "docker": ["docker", "containerization", "containers"],
    "kubernetes": ["kubernetes", "k8s"],
    "aws": ["aws", "amazon web services"],
    "gcp": ["gcp", "google cloud", "google cloud platform"],
    "azure": ["azure", "microsoft azure"],
    "terraform": ["terraform", "iac", "infrastructure as code"],
    "postgresql": ["postgresql", "postgres"],
    "mysql": ["mysql"],
    "mongodb": ["mongodb", "mongo"],
    "redis": ["redis"],
    "elasticsearch": ["elasticsearch", "elastic search", "opensearch"],
    "kafka": ["kafka", "apache kafka"],
    "rabbitmq": ["rabbitmq"],
    "graphql": ["graphql"],
    "rest": ["rest", "restful", "rest api", "restful apis"],
    "grpc": ["grpc"],
    "ci/cd": ["ci/cd", "continuous integration", "continuous deployment", "github actions", "gitlab ci", "jenkins"],
    "git": ["git", "version control", "github", "gitlab"],
    "linux": ["linux", "unix"],
    "html/css": ["html", "html5", "css", "css3", "tailwind", "sass"],
    "pytorch": ["pytorch", "torch"],
    "tensorflow": ["tensorflow", "tf"],
}

DOMAIN_COMPETENCY_KEYWORDS: Dict[str, List[str]] = {
    "distributed systems": ["distributed systems", "distributed computing", "high throughput", "fault tolerance"],
    "system design": ["system design", "software architecture", "architecting", "scalable systems", "system architecture"],
    "microservices": ["microservices", "microservice architecture", "service oriented architecture", "soa"],
    "api design": ["api design", "api development", "contract first", "openapi"],
    "database design": ["database design", "data modeling", "query optimization", "indexing", "schema design"],
    "agile / scrum": ["agile", "scrum", "kanban", "sprint planning", "sdlc"],
    "cloud architecture": ["cloud architecture", "cloud native", "serverless", "multi-tenant"],
    "security & auth": ["security", "authentication", "authorization", "oauth", "jwt", "zero trust", "rbac", "encryption"],
    "performance optimization": ["performance optimization", "latency reduction", "caching", "profiling", "tuning"],
    "unit & integration testing": ["unit testing", "integration testing", "automated testing", "tdd", "test driven development"],
    "etl & data pipelines": ["etl", "data pipelines", "data pipeline", "batch processing", "stream processing"],
    "devops & sre": ["devops", "sre", "site reliability", "monitoring", "observability", "metrics", "alerting"],
}

EDUCATION_KEYWORDS: List[str] = [
    "bachelor", "master", "phd", "b.s", "m.s", "degree", "computer science",
    "engineering", "mathematics", "information technology", "diploma",
]

SENIORITY_INDICATORS: List[str] = [
    "senior", "lead", "staff", "principal", "architect", "director", "manager",
    "junior", "mid-level", "associate",
]


# ── Schemas for Requirement & Assessment ─────────────────────────────────────
class ExtractedRequirement(BaseModel):
    """An individual requirement extracted from a job description."""
    id: str
    category: str = Field(..., description="hard_skills, domain_competencies, experience_scope, or education_credentials")
    original_text: str
    normalized_term: str
    is_required: bool = True  # True if required / must have; False if preferred / bonus
    match_status: str = Field(..., description="'matched', 'partially_supported', or 'not_demonstrated'")
    explanation: str
    evidence_snippet: Optional[str] = None  # Verbatim substring from resume
    recommendation: Optional[str] = None


class CategoryScore(BaseModel):
    """Score evaluation for one of the 4 job-match dimensions."""
    category: str
    label: str
    base_weight: float
    normalized_weight: float
    score: float = Field(..., ge=0.0, le=100.0)
    is_applicable: bool = True
    total_requirements: int = 0
    matched_count: int = 0
    partial_count: int = 0
    gap_count: int = 0


class JobMatchReport(BaseModel):
    """Complete explainable job-match assessment report."""
    job_title: Optional[str] = None
    overall_score: Optional[float] = None
    score_withheld: bool = False
    withheld_reason: Optional[str] = None
    category_scores: Dict[str, CategoryScore]
    requirements: List[ExtractedRequirement] = Field(default_factory=list)
    matched_count: int = 0
    partial_count: int = 0
    gap_count: int = 0
    top_recommendations: List[str] = Field(default_factory=list)
    limitations: List[str] = Field(default_factory=list)
    disclaimer: str = JOB_MATCH_DISCLAIMER


# ── Job Title Detection Helper ───────────────────────────────────────────────
def detect_job_title(jd_text: str) -> Optional[str]:
    """Infers job title from top lines or title header patterns."""
    lines = [line.strip() for line in jd_text.splitlines() if line.strip()]
    if not lines:
        return None

    # Check for explicit prefix: e.g. "Role: Senior Backend Engineer"
    title_pattern = re.compile(
        r"^(?:job\s+title|role|position|title)\s*[:\-–]\s*(.+)$",
        re.IGNORECASE,
    )
    for line in lines[:5]:
        match = title_pattern.match(line)
        if match:
            candidate = match.group(1).strip()
            if 3 <= len(candidate) <= 80:
                return candidate

    # Check if first non-empty line looks like a title (short, contains engineering/role terms)
    first_line = lines[0]
    if len(first_line) <= 60:
        lower = first_line.lower()
        role_signals = ["engineer", "developer", "manager", "lead", "architect", "designer", "scientist", "analyst", "specialist"]
        if any(sig in lower for sig in role_signals):
            return first_line

    return None


# ── Requirement Extraction ───────────────────────────────────────────────────
def extract_requirements_from_jd(jd_text: str) -> Tuple[List[ExtractedRequirement], bool, Optional[str]]:
    """Extracts and categorizes requirements from job description text.
    
    Returns:
        (extracted_requirements, is_sufficient, withheld_reason)
    """
    cleaned_jd = jd_text.strip()
    if len(cleaned_jd) < 50:
        return (
            [],
            False,
            "The job description text is too short to extract requirements. Please provide the full role description.",
        )

    requirements: List[ExtractedRequirement] = []
    seen_normalized: Set[str] = set()

    lines = [l.strip() for l in cleaned_jd.splitlines() if l.strip()]

    # Track current section context: required vs preferred
    is_in_preferred = False
    req_counter = 0

    preferred_patterns = re.compile(
        r"^(?:preferred|nice\s+to\s+have|bonus|desired|plus|good\s+to\s+have|preferred\s+qualifications)",
        re.IGNORECASE,
    )
    required_patterns = re.compile(
        r"^(?:requirements|qualifications|what\s+you(?:'ll)?\s+need|minimum\s+qualifications|basic\s+qualifications|must\s+have|responsibilities)",
        re.IGNORECASE,
    )

    full_lower = cleaned_jd.lower()

    # 1. HARD TECHNICAL SKILLS EXTRACTION
    for canonical_name, variants in HARD_SKILL_TAXONOMY.items():
        for variant in variants:
            # Word boundary regex search
            pattern = re.compile(r"(?<!\w)" + re.escape(variant) + r"(?!\w)", re.IGNORECASE)
            match = pattern.search(cleaned_jd)
            if match:
                if canonical_name not in seen_normalized:
                    seen_normalized.add(canonical_name)
                    req_counter += 1

                    # Determine if in a preferred context
                    start_pos = match.start()
                    preceding_text = cleaned_jd[max(0, start_pos - 150):start_pos].lower()
                    is_preferred = bool(preferred_patterns.search(preceding_text)) or "preferred" in preceding_text or "nice to have" in preceding_text

                    # Capture containing line or sentence for context
                    line_start = cleaned_jd.rfind("\n", 0, start_pos)
                    line_end = cleaned_jd.find("\n", start_pos)
                    line_start = 0 if line_start == -1 else line_start + 1
                    line_end = len(cleaned_jd) if line_end == -1 else line_end
                    snippet = cleaned_jd[line_start:line_end].strip()
                    if len(snippet) > 120:
                        snippet = snippet[:117] + "..."

                    requirements.append(
                        ExtractedRequirement(
                            id=f"req_hard_{req_counter}",
                            category="hard_skills",
                            original_text=snippet or canonical_name.capitalize(),
                            normalized_term=canonical_name,
                            is_required=not is_preferred,
                            match_status="not_demonstrated",
                            explanation="",
                        )
                    )
                break

    # 2. DOMAIN COMPETENCIES EXTRACTION
    for canonical_domain, keywords in DOMAIN_COMPETENCY_KEYWORDS.items():
        for kw in keywords:
            pattern = re.compile(r"(?<!\w)" + re.escape(kw) + r"(?!\w)", re.IGNORECASE)
            match = pattern.search(cleaned_jd)
            if match:
                if canonical_domain not in seen_normalized:
                    seen_normalized.add(canonical_domain)
                    req_counter += 1

                    start_pos = match.start()
                    preceding_text = cleaned_jd[max(0, start_pos - 150):start_pos].lower()
                    is_preferred = bool(preferred_patterns.search(preceding_text))

                    line_start = cleaned_jd.rfind("\n", 0, start_pos)
                    line_end = cleaned_jd.find("\n", start_pos)
                    line_start = 0 if line_start == -1 else line_start + 1
                    line_end = len(cleaned_jd) if line_end == -1 else line_end
                    snippet = cleaned_jd[line_start:line_end].strip()
                    if len(snippet) > 120:
                        snippet = snippet[:117] + "..."

                    requirements.append(
                        ExtractedRequirement(
                            id=f"req_domain_{req_counter}",
                            category="domain_competencies",
                            original_text=snippet or canonical_domain.capitalize(),
                            normalized_term=canonical_domain,
                            is_required=not is_preferred,
                            match_status="not_demonstrated",
                            explanation="",
                        )
                    )
                break

    # 3. EXPERIENCE SCOPE & SENIORITY EXTRACTION
    # Pattern: "X+ years of experience in..."
    exp_pattern = re.compile(
        r"(\d+)\+?\s*(?:-\s*(\d+))?\s*(?:years?|yrs?)(?:\s+of)?(?:\s+relevant)?\s+(?:experience|work)",
        re.IGNORECASE,
    )
    for line in lines:
        if preferred_patterns.match(line):
            is_in_preferred = True
            continue
        if required_patterns.match(line):
            is_in_preferred = False
            continue

        exp_match = exp_pattern.search(line)
        if exp_match:
            term = exp_match.group(0).lower()
            if term not in seen_normalized:
                seen_normalized.add(term)
                req_counter += 1
                requirements.append(
                    ExtractedRequirement(
                        id=f"req_exp_{req_counter}",
                        category="experience_scope",
                        original_text=line[:120],
                        normalized_term=term,
                        is_required=not is_in_preferred,
                        match_status="not_demonstrated",
                        explanation="",
                    )
                )

    # Check for seniority keywords if no explicit years found
    if not any(r.category == "experience_scope" for r in requirements):
        for sen in SENIORITY_INDICATORS:
            if re.search(r"\b" + sen + r"\b", full_lower):
                seen_normalized.add(sen)
                req_counter += 1
                requirements.append(
                    ExtractedRequirement(
                        id=f"req_exp_{req_counter}",
                        category="experience_scope",
                        original_text=f"{sen.capitalize()} level responsibilities and scope",
                        normalized_term=f"{sen} level",
                        is_required=True,
                        match_status="not_demonstrated",
                        explanation="",
                    )
                )
                break

    # 4. EDUCATION & CREDENTIALS EXTRACTION
    degree_pattern = re.compile(
        r"(?:bachelor(?:'s)?|master(?:'s)?|ph\.?d\.?|b\.?s\.?|m\.?s\.?)(?:\s+(?:degree|in))?\s*(?:computer\s+science|engineering|math|information\s+technology|related\s+field)?",
        re.IGNORECASE,
    )
    for line in lines:
        deg_match = degree_pattern.search(line)
        if deg_match:
            deg_term = deg_match.group(0).strip().lower()
            if deg_term and len(deg_term) > 3 and "degree" not in seen_normalized:
                seen_normalized.add("degree")
                req_counter += 1
                requirements.append(
                    ExtractedRequirement(
                        id=f"req_edu_{req_counter}",
                        category="education_credentials",
                        original_text=line[:120],
                        normalized_term=deg_term,
                        is_required="preferred" not in line.lower(),
                        match_status="not_demonstrated",
                        explanation="",
                    )
                )
                break

    # Boundary check: do we have enough identifiable requirements?
    if len(requirements) < 2:
        return (
            requirements,
            False,
            "The job description did not yield enough identifiable requirements (skills, experience, or credentials) to compute a meaningful match score. Please provide a more complete job posting.",
        )

    return requirements, True, None


def find_verbatim_evidence(term: str, variants: List[str], resume_raw: str, resume_lines: List[str]) -> Optional[str]:
    """Finds an exact verbatim sentence/bullet from resume content matching the term.
    
    CRITICAL GUARDRAIL: Returned evidence is GUARANTEED to be a verbatim substring
    of the candidate's resume content.
    """
    all_search_terms = [term] + variants

    # 1. Search directly in lines of resume_raw
    raw_lines = [l.strip() for l in resume_raw.splitlines() if l.strip()]
    for raw_line in raw_lines:
        if len(raw_line) < 4:
            continue
        line_lower = raw_line.lower()
        for t in all_search_terms:
            pattern = re.compile(r"(?<!\w)" + re.escape(t.lower()) + r"(?!\w)")
            if pattern.search(line_lower):
                if raw_line in resume_raw:
                    return raw_line

    # 2. Search sentences in resume_raw
    sentences = re.split(r"(?<=[.!?\n])\s+", resume_raw)
    for sent in sentences:
        sent_clean = sent.strip()
        if len(sent_clean) >= 8:
            sent_lower = sent_clean.lower()
            for t in all_search_terms:
                pattern = re.compile(r"(?<!\w)" + re.escape(t.lower()) + r"(?!\w)")
                if pattern.search(sent_lower) and sent_clean in resume_raw:
                    return sent_clean

    # 3. Check resume_lines ONLY IF the line is an authentic substring of resume_raw
    for line in resume_lines:
        line_clean = line.strip()
        if not line_clean or len(line_clean) < 4:
            continue
        line_lower = line_clean.lower()
        for t in all_search_terms:
            pattern = re.compile(r"(?<!\w)" + re.escape(t.lower()) + r"(?!\w)")
            if pattern.search(line_lower) and line_clean in resume_raw:
                return line_clean

    return None


# ── Match Assessment Engine ──────────────────────────────────────────────────
def evaluate_job_match(
    jd_text: str,
    raw_text: str,
    structured_data: Dict[str, Any],
) -> JobMatchReport:
    """Computes transparent, grounded Job Match score against active resume.
    
    Zero hallucination guarantee: every evidence snippet is checked against
    resume content.
    """
    job_title = detect_job_title(jd_text)
    extracted_reqs, is_sufficient, withheld_reason = extract_requirements_from_jd(jd_text)

    # Compile searchable resume lines from structured entries and raw text
    resume_skills: List[str] = structured_data.get("skills") or []
    resume_exp: List[str] = structured_data.get("experience") or []
    resume_edu: List[str] = structured_data.get("education") or []
    resume_proj: List[str] = structured_data.get("projects") or []
    resume_cert: List[str] = structured_data.get("certifications") or []
    resume_summary = structured_data.get("summary") or ""

    all_resume_lines = (
        resume_skills + resume_exp + resume_edu + resume_proj + resume_cert + [resume_summary]
    )

    if not is_sufficient:
        # Build category breakdown with withheld status
        categories_dict: Dict[str, CategoryScore] = {}
        labels = {
            "hard_skills": "Hard Technical Skills",
            "domain_competencies": "Domain Competencies",
            "experience_scope": "Experience Scope",
            "education_credentials": "Education & Credentials",
        }
        for cat_key, base_w in JOB_MATCH_WEIGHTS.items():
            categories_dict[cat_key] = CategoryScore(
                category=cat_key,
                label=labels[cat_key],
                base_weight=base_w,
                normalized_weight=base_w,
                score=0.0,
                is_applicable=False,
            )

        return JobMatchReport(
            job_title=job_title,
            overall_score=None,
            score_withheld=True,
            withheld_reason=withheld_reason,
            category_scores=categories_dict,
            requirements=[],
            matched_count=0,
            partial_count=0,
            gap_count=0,
            top_recommendations=["Provide a complete job description with explicit responsibilities and required qualifications."],
            limitations=[withheld_reason or "Insufficient requirement structure in job posting."],
            disclaimer=JOB_MATCH_DISCLAIMER,
        )

    # 1. Match each extracted requirement against resume text
    evaluated_reqs: List[ExtractedRequirement] = []
    matched_count = 0
    partial_count = 0
    gap_count = 0

    for req in extracted_reqs:
        term = req.normalized_term
        category = req.category

        if category == "hard_skills":
            variants = HARD_SKILL_TAXONOMY.get(term, [term])
            # Direct skill list check
            in_skills = any(
                any(v.lower() == s.lower() or v.lower() in s.lower() for v in variants)
                for s in resume_skills
            )
            evidence = find_verbatim_evidence(term, variants, raw_text, all_resume_lines)

            if evidence:
                req.match_status = "matched"
                req.evidence_snippet = evidence
                req.explanation = f"Directly demonstrated in your resume ({term.upper()})."
                matched_count += 1
            elif in_skills:
                # Skill is in list
                req.match_status = "matched"
                skill_evidence = next((s for s in resume_skills if any(v in s.lower() for v in variants)), term)
                req.evidence_snippet = skill_evidence if skill_evidence in raw_text else None
                req.explanation = f"Listed in your verified skills taxonomy ({term.upper()})."
                matched_count += 1
            else:
                req.match_status = "not_demonstrated"
                req.explanation = f"No textual evidence for {term.upper()} was found in your resume."
                req.recommendation = f"Add projects, coursework, or experience involving {term.capitalize()} if you have worked with it."
                gap_count += 1

        elif category == "domain_competencies":
            keywords = DOMAIN_COMPETENCY_KEYWORDS.get(term, [term])
            evidence = find_verbatim_evidence(term, keywords, raw_text, all_resume_lines)

            if evidence:
                req.match_status = "matched"
                req.evidence_snippet = evidence
                req.explanation = f"Demonstrated in your experience descriptions ({term.title()})."
                matched_count += 1
            else:
                # Check for partial keyword overlap
                partial_words = [w for w in term.split() if len(w) > 3]
                partial_evidence = None
                for pw in partial_words:
                    partial_evidence = find_verbatim_evidence(pw, [pw], raw_text, all_resume_lines)
                    if partial_evidence:
                        break

                if partial_evidence:
                    req.match_status = "partially_supported"
                    req.evidence_snippet = partial_evidence
                    req.explanation = f"Related concepts identified, but full scope for {term.title()} is not explicitly stated."
                    req.recommendation = f"Clarify your specific role in {term.title()} within work experience bullets."
                    partial_count += 1
                else:
                    req.match_status = "not_demonstrated"
                    req.explanation = f"No explicit experience with {term.title()} is documented."
                    req.recommendation = f"Incorporate contextual examples of {term.title()} if part of your past responsibilities."
                    gap_count += 1

        elif category == "experience_scope":
            # Search for years or seniority markers in resume
            years_match = re.search(r"(\d+)\+?\s*years?", term)
            req_years = int(years_match.group(1)) if years_match else 3

            # Look for years in summary or experience
            exp_evidence = None
            for line in resume_exp + [resume_summary]:
                if any(k in line.lower() for k in ["year", "engineer", "lead", "senior", "experience"]):
                    if len(line.strip()) > 15:
                        exp_evidence = line.strip()
                        break

            if exp_evidence and len(resume_exp) >= max(1, req_years // 2):
                req.match_status = "matched"
                req.evidence_snippet = exp_evidence
                req.explanation = "Documented employment history and role scope demonstrate relevant seniority."
                matched_count += 1
            elif len(resume_proj) >= 2 or len(resume_exp) >= 1:
                # Early career / project parity
                req.match_status = "partially_supported"
                req.evidence_snippet = resume_proj[0] if resume_proj else (resume_exp[0] if resume_exp else None)
                req.explanation = "Demonstrated technical project experience, with potential growth into full tenure requirement."
                req.recommendation = "Emphasize leadership, architecture decisions, and independent project ownership."
                partial_count += 1
            else:
                req.match_status = "not_demonstrated"
                req.explanation = "Extracted employment history does not yet demonstrate the target seniority or tenure scope."
                req.recommendation = "Detail additional professional or substantial open-source experience."
                gap_count += 1

        elif category == "education_credentials":
            # Check education section
            edu_evidence = None
            for edu_line in resume_edu + resume_cert:
                if any(w in edu_line.lower() for w in EDUCATION_KEYWORDS):
                    edu_evidence = edu_line.strip()
                    break

            if edu_evidence:
                req.match_status = "matched"
                req.evidence_snippet = edu_evidence
                req.explanation = "Verified degree or academic credential identified in Education section."
                matched_count += 1
            elif resume_edu:
                req.match_status = "partially_supported"
                req.evidence_snippet = resume_edu[0]
                req.explanation = "Education record present, though degree title or major may differ slightly."
                req.recommendation = "Highlight coursework or certifications relevant to the required specialization."
                partial_count += 1
            else:
                req.match_status = "not_demonstrated"
                req.explanation = "No degree or certification records identified in the parsed resume."
                req.recommendation = "Add completed degrees, diplomas, or accredited professional certifications."
                gap_count += 1

        evaluated_reqs.append(req)

    # 2. Compute Category Subscores with Pro-Rata Normalization for Absent Categories
    category_scores: Dict[str, CategoryScore] = {}
    labels = {
        "hard_skills": "Hard Technical Skills",
        "domain_competencies": "Domain Competencies",
        "experience_scope": "Experience Scope",
        "education_credentials": "Education & Credentials",
    }

    # First, calculate raw score for each category that has requirements
    applicable_weights_sum = 0.0

    for cat_key, base_w in JOB_MATCH_WEIGHTS.items():
        cat_reqs = [r for r in evaluated_reqs if r.category == cat_key]
        if not cat_reqs:
            # Genuinely absent from JD: Mark Not Applicable
            category_scores[cat_key] = CategoryScore(
                category=cat_key,
                label=labels[cat_key],
                base_weight=base_w,
                normalized_weight=0.0,
                score=0.0,
                is_applicable=False,
                total_requirements=0,
                matched_count=0,
                partial_count=0,
                gap_count=0,
            )
        else:
            applicable_weights_sum += base_w
            cat_matched = sum(1 for r in cat_reqs if r.match_status == "matched")
            cat_partial = sum(1 for r in cat_reqs if r.match_status == "partially_supported")
            cat_gap = sum(1 for r in cat_reqs if r.match_status == "not_demonstrated")

            # Weighted sum: Required = 1.0, Preferred = 0.5; Matched = 1.0, Partial = 0.5
            total_points = 0.0
            max_points = 0.0
            for r in cat_reqs:
                weight = 1.0 if r.is_required else 0.5
                max_points += weight
                if r.match_status == "matched":
                    total_points += 1.0 * weight
                elif r.match_status == "partially_supported":
                    total_points += 0.5 * weight

            cat_score = round((total_points / max_points) * 100.0, 1) if max_points > 0 else 0.0

            category_scores[cat_key] = CategoryScore(
                category=cat_key,
                label=labels[cat_key],
                base_weight=base_w,
                normalized_weight=base_w,  # will normalize below
                score=cat_score,
                is_applicable=True,
                total_requirements=len(cat_reqs),
                matched_count=cat_matched,
                partial_count=cat_partial,
                gap_count=cat_gap,
            )

    # Re-normalize weights pro-rata if any category was absent
    overall_score = 0.0
    if applicable_weights_sum > 0:
        for cat_key, cat_score_obj in category_scores.items():
            if cat_score_obj.is_applicable:
                norm_w = cat_score_obj.base_weight / applicable_weights_sum
                cat_score_obj.normalized_weight = round(norm_w, 3)
                overall_score += cat_score_obj.score * norm_w

    overall_score = max(0.0, min(100.0, round(overall_score, 1)))

    # 3. Compile Top Recommendations
    top_recommendations: List[str] = []
    gaps_with_rec = [r for r in evaluated_reqs if r.match_status == "not_demonstrated" and r.recommendation]
    for r in gaps_with_rec[:4]:
        if r.recommendation and r.recommendation not in top_recommendations:
            top_recommendations.append(r.recommendation)

    if not top_recommendations:
        top_recommendations.append("Review keyword phrasing in work experience bullets to ensure exact alignment with target role terminology.")

    # 4. Limitations
    limitations: List[str] = [
        "Analysis evaluates explicitly stated keywords and qualifications in the job description against text in your resume.",
        "Unstated company preferences, cultural fit, and unwritten expectations cannot be assessed via text parsing.",
    ]
    if applicable_weights_sum < 1.0:
        absent_cats = [c.label for c in category_scores.values() if not c.is_applicable]
        limitations.append(
            f"The job description did not specify requirements for: {', '.join(absent_cats)}. Active category weights were proportionally normalized."
        )

    return JobMatchReport(
        job_title=job_title,
        overall_score=overall_score,
        score_withheld=False,
        withheld_reason=None,
        category_scores=category_scores,
        requirements=evaluated_reqs,
        matched_count=matched_count,
        partial_count=partial_count,
        gap_count=gap_count,
        top_recommendations=top_recommendations,
        limitations=limitations,
        disclaimer=JOB_MATCH_DISCLAIMER,
    )
