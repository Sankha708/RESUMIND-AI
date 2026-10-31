"""Resume Builder Service Layer.

Handles data transformations between reviewed resume profile snapshots and the
rich, customizable ResumeBuilderDocument content model, as well as optimistic concurrency
and template layout normalization.
"""

import re
import uuid
from typing import Any, Dict, List, Optional, Tuple

from app.services.parser_service import normalize_text_encoding

from app.schemas.builder import (
    AdditionalSectionItem,
    BuilderContent,
    CertificationItem,
    ContactInfo,
    EducationItem,
    ExperienceItem,
    ProjectItem,
    SkillCategory,
    TemplateConfig,
)

DEFAULT_SECTION_ORDER = [
    "contact",
    "summary",
    "experience",
    "projects",
    "skills",
    "education",
    "certifications",
    "additional",
]

DEFAULT_SECTION_VISIBILITY = {
    "contact": True,
    "summary": True,
    "experience": True,
    "projects": True,
    "skills": True,
    "education": True,
    "certifications": True,
    "additional": True,
}

_MONTH_YEAR = r"(?:(?:Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|Jun(?:e)?|Jul(?:y)?|Aug(?:ust)?|Sep(?:tember)?|Oct(?:ober)?|Nov(?:ember)?|Dec(?:ember)?)\.?\s+\d{4})"
_DATE_TOKEN = rf"(?:{_MONTH_YEAR}|\d{{4}})"
DATE_RANGE_REGEX = re.compile(
    rf"\b({_DATE_TOKEN}\s*(?:-|\u2013|\u2014|\u00b7|\bto\b)\s*(?:Present|Current|Now|{_DATE_TOKEN}))\b",
    re.IGNORECASE,
)
PROJECT_DATE_REGEX = re.compile(
    r"\b(?:(?:Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|Jun(?:e)?|Jul(?:y)?|Aug(?:ust)?|Sep(?:tember)?|Oct(?:ober)?|Nov(?:ember)?|Dec(?:ember)?)\.?\s+\d{4}|(?:19|20)\d{2})\b",
    re.IGNORECASE,
)

# Normalize first; include common PDF bullet glyphs and Windows-1252 remnants.
_BULLET_PREFIX_RE = re.compile(r"^[\u2022\u2023\u25e6\u25aa\u00b7\u00bb\u203a\u0095\-\*]\s*|^\d+[.)]\s+")
_ROLE_WORD_RE = re.compile(
    r"\b(co[- ]?founder|founder|intern|engineer|developer|analyst|manager|designer|"
    r"consultant|architect|scientist|specialist|assistant|director|lead|officer|trainer|"
    r"administrator|coordinator|researcher|teacher|student|executive|associate|trainee)\b",
    re.IGNORECASE,
)


def _normalize_line(text: str) -> str:
    text = normalize_text_encoding(str(text or ""))
    text = text.replace("\ufeff", "").replace("\u00a0", " ")
    return re.sub(r"[\t ]+", " ", text).strip()


def _flatten_input_lines(raw_lines: List[Any]) -> List[str]:
    """Normalize and split stored list entries that may themselves contain newlines."""
    output: List[str] = []
    for raw in raw_lines or []:
        normalized = normalize_text_encoding(str(raw or "")).replace("\r\n", "\n").replace("\r", "\n")
        for line in normalized.split("\n"):
            line = _normalize_line(line)
            if line and not line.startswith("--- Page Break"):
                output.append(line)
    return output


def _is_bullet_line(text: str) -> bool:
    return bool(_BULLET_PREFIX_RE.match(_normalize_line(text)))


def _strip_bullet_prefix(text: str) -> str:
    return _BULLET_PREFIX_RE.sub("", _normalize_line(text)).strip()


def _has_date_range(text: str) -> bool:
    return bool(DATE_RANGE_REGEX.search(normalize_text_encoding(text or "")))


def _extract_date_range(date_text: str) -> Tuple[str, str, bool]:
    m = DATE_RANGE_REGEX.search(normalize_text_encoding(date_text or ""))
    if not m:
        return "", "", False
    full = m.group(1).strip()
    parts = re.split(r"\s*(?:-|\u2013|\u2014|\u00b7|\bto\b)\s*", full, maxsplit=1, flags=re.IGNORECASE)
    start = parts[0].strip() if parts else ""
    end_raw = parts[1].strip() if len(parts) > 1 else ""
    is_current = end_raw.lower() in ("present", "current", "now")
    return start, "" if is_current else end_raw, is_current


def _looks_like_experience_header(line: str) -> bool:
    stripped = _normalize_line(line)
    if not stripped or _is_bullet_line(stripped):
        return False
    # Company | location | date headers used by many student resumes.
    if "|" in stripped and _has_date_range(stripped):
        return True
    if _has_date_range(stripped) and len(stripped.split()) <= 28:
        return True
    if re.search(r"\s+at\s+", stripped, re.IGNORECASE) and len(stripped.split()) <= 14:
        return True
    # A short role/company pair separated by a dash, but not a sentence bullet.
    if re.search(r"\s[\u2013\u2014\u00b7-]\s", stripped) and len(stripped.split()) <= 16:
        return True
    return False


def _group_flat_lines_into_blocks(flat_lines: List[str]) -> List[List[str]]:
    """Group flat lines at detected entry headers without treating wrapped lines as records."""
    blocks: List[List[str]] = []
    current: List[str] = []
    for line in _flatten_input_lines(flat_lines):
        if _looks_like_experience_header(line) and current:
            blocks.append(current)
            current = []
        current.append(line)
    if current:
        blocks.append(current)
    return blocks


def _split_head_and_metadata(header_line: str) -> Tuple[str, List[str], str]:
    text = _normalize_line(header_line)
    dm = DATE_RANGE_REGEX.search(text)
    date_text = dm.group(0).strip(" ()") if dm else ""
    without_date = text
    if dm:
        without_date = text[:dm.start()] + text[dm.end():]
        without_date = re.sub(r"\(\s*\)", "", without_date)
        without_date = without_date.strip(" |,()–—-").strip()
    fields = [part.strip() for part in without_date.split("|") if part.strip()]
    head = fields[0] if fields else without_date
    metadata = fields[1:] if len(fields) > 1 else []
    # Remove a dangling date-only metadata field where the date regex did not span it.
    metadata = [m for m in metadata if not PROJECT_DATE_REGEX.fullmatch(m.strip(" ()"))]
    return head, metadata, date_text


def _looks_like_role(text: str) -> bool:
    return bool(_ROLE_WORD_RE.search(text or ""))


def _parse_experience_header(header_line: str) -> Tuple[str, str, str, str]:
    """Return role, company, date text, and location from common resume header shapes."""
    head, metadata, date_text = _split_head_and_metadata(header_line)
    location = metadata[0] if metadata else ""
    if location and (DATE_RANGE_REGEX.search(location) or PROJECT_DATE_REGEX.fullmatch(location)):
        location = ""

    if re.search(r"\s+at\s+", head, re.IGNORECASE):
        left, right = re.split(r"\s+at\s+", head, maxsplit=1, flags=re.IGNORECASE)
        role, company = left.strip(" |,"), right.strip(" |,")
    else:
        parts = re.split(r"\s+[\u2013\u2014\u00b7-]\s+", head, maxsplit=1)
        if len(parts) == 2:
            left, right = parts[0].strip(" |,"), parts[1].strip(" |,")
            # Typical header is either "Role — Company" or "Company — Role".
            # Prefer the side that looks like a job title; fall back to organization-first.
            left_is_role, right_is_role = _looks_like_role(left), _looks_like_role(right)
            if right_is_role and not left_is_role:
                company, role = left, right
            elif left_is_role and not right_is_role:
                role, company = left, right
            elif re.fullmatch(r"[A-Z0-9&.]{2,}", left) and not re.fullmatch(r"[A-Z0-9&.]{2,}", right):
                company, role = left, right
            else:
                role, company = left, right
        else:
            role, company = "", head.strip(" |,")
    return role, company, date_text, location


def _should_continue_bullet(previous: str, current: str) -> bool:
    """Treat visual wrapping as continuation, not as an unrelated new bullet."""
    previous = previous.rstrip()
    current = current.strip()
    if not previous or not current:
        return False
    if previous.endswith((",", ";", ":", "-", "\u2013", "\u2014", "/")):
        return True
    if current[:1].islower():
        return True
    # A line that ends without sentence punctuation is commonly a wrapped PDF line.
    if not re.search(r"[.!?][\"')\]]?$", previous):
        return True
    return False


def _append_bullet(bullets: List[str], line: str) -> None:
    cleaned = _strip_bullet_prefix(line) if _is_bullet_line(line) else _normalize_line(line)
    if not cleaned:
        return
    if bullets and not _is_bullet_line(line) and _should_continue_bullet(bullets[-1], cleaned):
        bullets[-1] = f"{bullets[-1].rstrip()} {cleaned.lstrip()}".strip()
    else:
        bullets.append(cleaned)


def _build_experience_items(raw_lines: List[str]) -> List[ExperienceItem]:
    """Build one item per actual detected role, preserving complete multi-line bullets."""
    lines = _flatten_input_lines(raw_lines)
    items: List[ExperienceItem] = []
    current: Optional[ExperienceItem] = None

    for line in lines:
        if _looks_like_experience_header(line):
            role, company, date_text, location = _parse_experience_header(line)
            start_date, end_date, current_role = _extract_date_range(date_text) if date_text else ("", "", False)
            current = ExperienceItem(
                id=str(uuid.uuid4())[:8], company=company, role=role, location=location,
                start_date=start_date, end_date=end_date, current=current_role, bullets=[],
            )
            items.append(current)
            continue

        if current is None:
            # Never create an invented role from orphaned preamble or bullet text.
            continue
        if re.match(r"^(?:code|repository|repo|url|github)\s*:", line, re.IGNORECASE):
            continue
        _append_bullet(current.bullets, line)

    # Remove only empty records caused by malformed source data; preserve bullet-only roles when present.
    return [item for item in items if item.company or item.role or item.bullets]


def _looks_like_project_header(line: str) -> bool:
    stripped = _normalize_line(line)
    if not stripped or _is_bullet_line(stripped):
        return False
    if re.match(r"^(?:code|repository|repo|url|github)\s*:", stripped, re.IGNORECASE):
        return False
    parts = [part.strip() for part in stripped.split("|") if part.strip()]
    if len(parts) >= 2:
        # Title | tech stack | month/year is the format used in the supplied resume.
        if PROJECT_DATE_REGEX.search(parts[-1]) or any(
            re.search(r"\b(?:Next\.js|FastAPI|Python|React|MongoDB|LangGraph|Java|JavaScript|API|SQL|AWS)\b", part, re.I)
            for part in parts[1:]
        ):
            return len(parts[0].split()) <= 16
    if re.search(r"\(\s*(?:19|20)\d{2}\s*\)", stripped) and len(stripped.split()) <= 18:
        return True
    if ":" in stripped:
        left, right = stripped.split(":", 1)
        if 1 <= len(left.split()) <= 7 and right.strip() and not re.match(r"//", right.strip()):
            return True
    return False


def _parse_project_header(header: str) -> Tuple[str, List[str], str, str]:
    """Return title, technologies, date, and repository URL from a project heading."""
    line = _normalize_line(header)
    parts = [part.strip() for part in line.split("|") if part.strip()]
    title = parts[0] if parts else line
    tech_stack: List[str] = []
    date_text = ""
    url = ""

    # A colon format like "Distributed Cache: Built Redis-compatible engine".
    if len(parts) == 1 and ":" in title:
        left, right = title.split(":", 1)
        if len(left.split()) <= 7 and right.strip():
            title = left.strip()
            # The first description is returned via the special date_text slot only internally? no;
            # it will be handled by _build_project_items below.

    if len(parts) >= 2:
        for field in parts[1:]:
            if PROJECT_DATE_REGEX.fullmatch(field.strip(" ()")):
                date_text = field.strip(" ()")
            elif re.search(r"\b(?:19|20)\d{2}\b", field) and len(field.split()) <= 4:
                date_text = field.strip(" ()")
            elif re.match(r"^(?:https?://)?(?:www\.)?(?:github\.com|gitlab\.com|bitbucket\.org)\b", field, re.I):
                url = field
            else:
                maybe_tech = [value.strip() for value in field.split(",") if value.strip()]
                if maybe_tech:
                    tech_stack.extend(maybe_tech)

    # Preserve date in parenthetical single-year title format.
    if not date_text:
        m = re.search(r"\(\s*((?:19|20)\d{2})\s*\)", line)
        if m:
            date_text = m.group(1)
            title = re.sub(r"\s*\(\s*(?:19|20)\d{2}\s*\)\s*", "", title).strip()

    return title.strip(), list(dict.fromkeys(tech_stack)), date_text, url


def _build_project_items(raw_lines: List[str]) -> List[ProjectItem]:
    """Build project records independently from experience records."""
    lines = _flatten_input_lines(raw_lines)
    items: List[ProjectItem] = []
    current: Optional[ProjectItem] = None

    for line in lines:
        if _looks_like_project_header(line):
            title, tech_stack, project_date, url = _parse_project_header(line)
            # For "Name: description" keep the description as the first bullet.
            first_description = ""
            if "|" not in line and ":" in line:
                left, right = line.split(":", 1)
                if len(left.split()) <= 7:
                    title = left.strip()
                    first_description = right.strip()
            start_date = project_date
            current = ProjectItem(
                id=str(uuid.uuid4())[:8], title=title, role="", url=url,
                start_date=start_date, end_date="", bullets=[], tech_stack=tech_stack,
            )
            items.append(current)
            if first_description:
                _append_bullet(current.bullets, first_description)
            continue

        if current is None:
            continue
        code_match = re.match(r"^(?:code|repository|repo|url|github)\s*:\s*(\S+)", line, re.IGNORECASE)
        if code_match:
            current.url = code_match.group(1).rstrip(".,)")
            continue
        if _is_bullet_line(line):
            current.bullets.append(_strip_bullet_prefix(line))
        else:
            _append_bullet(current.bullets, line)

    return [item for item in items if item.title or item.url or item.bullets or item.tech_stack]

def create_blank_builder_content() -> BuilderContent:
    """Returns an empty starter profile without any fabricated claims or metrics."""
    return BuilderContent(
        contact=ContactInfo(
            name="",
            headline="",
            email="",
            phone="",
            location="",
            website="",
            linkedin="",
            github="",
        ),
        summary="",
        experience=[],
        projects=[],
        skills=[
            SkillCategory(
                id=str(uuid.uuid4())[:8],
                category="Core Competencies",
                skills=[],
            )
        ],
        education=[],
        certifications=[],
        additional=[],
    )


def convert_structured_profile_to_builder_content(
    structured_data: Optional[Dict[str, Any]],
) -> BuilderContent:
    """Converts a reviewed resume structured data into the rich Resume Builder model.

    Key invariants:
    - One ExperienceItem per actual employer / role (not one per line).
    - One ProjectItem per actual project (not one per line; never 'Project N').
    - Bullets remain grouped under their correct parent entry.
    - Skills faithfully transferred from the parser output.
    - Missing optional fields remain empty rather than receiving generic labels.
    """
    if not structured_data:
        return create_blank_builder_content()

    # 1. Contact Info
    raw_contact = structured_data.get("contact") or {}
    urls = raw_contact.get("urls") or []
    linkedin_url = next((u for u in urls if "linkedin.com" in u.lower()), "")
    github_url = next((u for u in urls if "github.com" in u.lower()), "")
    other_url = next((u for u in urls if u not in [linkedin_url, github_url]), "")

    contact = ContactInfo(
        name=raw_contact.get("name") or "",
        headline=raw_contact.get("headline") or "",
        email=raw_contact.get("email") or "",
        phone=raw_contact.get("phone") or "",
        location=raw_contact.get("location") or "",
        website=other_url,
        linkedin=linkedin_url,
        github=github_url,
    )

    # 2. Summary
    summary = str(structured_data.get("summary") or "").strip()

    # 3. Work Experience
    raw_exp = structured_data.get("experience") or []
    experience_items = _build_experience_items(
        [str(item) for item in raw_exp if isinstance(item, str) and item.strip()]
    )

    # 4. Projects
    raw_projects = structured_data.get("projects") or []
    project_items = _build_project_items(
        [str(item) for item in raw_projects if isinstance(item, str) and item.strip()]
    )

    # 5. Skills
    raw_skills = structured_data.get("skills") or []
    skill_list: List[str] = []
    if isinstance(raw_skills, list):
        for s in raw_skills:
            if isinstance(s, str) and s.strip():
                skill_list.append(s.strip())
    elif isinstance(raw_skills, str):
        skill_list = [s.strip() for s in raw_skills.split(",") if s.strip()]

    # Preserve source category labels when available. The flat `skills` list remains
    # canonical for the review screen, so removed skills are filtered and newly added
    # skills are retained under an additional category instead of being lost.
    parsed_categories = structured_data.get("skill_categories") or []
    skill_categories: List[SkillCategory] = []
    remaining = list(skill_list)
    if isinstance(parsed_categories, list):
        for entry in parsed_categories:
            if not isinstance(entry, dict):
                continue
            category_name = str(entry.get("category") or "Technical Skills").strip() or "Technical Skills"
            source_skills = entry.get("skills") or []
            retained = []
            for value in source_skills:
                if not isinstance(value, str):
                    continue
                match = next((candidate for candidate in remaining if candidate.casefold() == value.strip().casefold()), None)
                if match:
                    retained.append(match)
                    remaining.remove(match)
            if retained:
                skill_categories.append(SkillCategory(
                    id=str(uuid.uuid4())[:8], category=category_name, skills=retained,
                ))
    if remaining:
        skill_categories.append(SkillCategory(
            id=str(uuid.uuid4())[:8],
            category="Additional Skills" if skill_categories else "Technical Skills",
            skills=remaining,
        ))
    if not skill_categories:
        skill_categories = [SkillCategory(
            id=str(uuid.uuid4())[:8], category="Technical Skills", skills=skill_list,
        )]

    # 6. Education
    education_items: List[EducationItem] = []
    raw_edu = structured_data.get("education") or []
    if isinstance(raw_edu, list):
        edu_blocks = _group_flat_lines_into_blocks(
            [str(item) for item in raw_edu if isinstance(item, str) and item.strip()]
        )
        for block in edu_blocks:
            if not block:
                continue
            text = _normalize_line(block[0])
            institution = text
            degree = ""
            field_of_study = ""
            start_date = ""
            end_date = ""
            gpa_match = re.search(r"\b(?:CGPA|GPA)\s*[:：]?\s*([0-9]+(?:\.[0-9]+)?(?:\s*/\s*[0-9]+(?:\.[0-9]+)?)?)", text, re.I)
            gpa = gpa_match.group(1).replace(" ", "") if gpa_match else ""

            # Some extraction orders place the degree abbreviation after the GPA,
            # e.g. "Field | Institution | 2023–2027 | CGPA: 8.05 — B.Tech".
            trailing_degree = ""
            if gpa_match:
                suffix = text[gpa_match.end():].strip(" |,;")
                suffix_match = re.fullmatch(r"[—–-]?\s*(B\.?Tech|M\.?Tech|B\.?E\.?|M\.?E\.?|B\.?Sc\.?|M\.?Sc\.?|BCA|MCA|MBA|Ph\.?D\.?)", suffix, re.I)
                if suffix_match:
                    trailing_degree = suffix_match.group(1).replace(" ", "")
                text = text[:gpa_match.start()].strip(" |,;–—-")

            dm = DATE_RANGE_REGEX.search(text)
            if dm:
                start_date, end_date, _ = _extract_date_range(dm.group(0))
                text = (text[:dm.start()] + text[dm.end():]).strip(" |–—,()")

            # Support reverse ordering: "West Bengal | 2022 — Class XII | JNV".
            legacy_education = False
            if not dm:
                reverse_match = re.match(r"^(.*?)\s+[—–-]\s+(.*)$", text)
                if reverse_match:
                    left_fields = [part.strip() for part in reverse_match.group(1).split("|") if part.strip()]
                    right_fields = [part.strip() for part in reverse_match.group(2).split("|") if part.strip()]
                    if len(left_fields) >= 2 and re.fullmatch(r"(?:19|20)\d{2}", left_fields[-1]) and right_fields:
                        end_date = left_fields[-1]
                        degree = right_fields[0]
                        institution_parts = right_fields[1:] + [left_fields[0]]
                        institution = ", ".join(part for part in institution_parts if part)
                        legacy_education = True

            if not legacy_education:
                fields = [part.strip() for part in text.split("|") if part.strip()]
                if len(fields) >= 2:
                    if trailing_degree:
                        field_of_study = fields[0]
                        degree = trailing_degree
                        institution = fields[1]
                        # Preserve any location or additional institution metadata.
                        if len(fields) > 2:
                            institution = ", ".join([institution] + fields[2:])
                    else:
                        degree = fields[0]
                        institution = fields[1]
                        if len(fields) > 2:
                            institution = ", ".join([institution] + fields[2:])
                elif re.search(r"\s+[—–\u2014\u00b7]\s+", text):
                    parts = re.split(r"\s+[—–\u2014\u00b7]\s+", text, maxsplit=1)
                    degree = parts[0].strip()
                    institution = parts[1].strip() if len(parts) > 1 else text
                elif " at " in text:
                    parts = text.split(" at ", 1)
                    degree = parts[0].strip()
                    institution = parts[1].strip()
                elif "," in text:
                    parts = text.split(",", 1)
                    degree = parts[0].strip()
                    institution = parts[1].strip()

            highlights = [
                _strip_bullet_prefix(ln)
                for ln in block[1:]
                if ln.strip() and _is_bullet_line(ln)
            ]

            education_items.append(EducationItem(
                id=str(uuid.uuid4())[:8],
                institution=institution,
                degree=degree,
                field_of_study=field_of_study,
                start_date=start_date,
                end_date=end_date,
                gpa=gpa,
                highlights=highlights,
            ))

    # 7. Certifications
    certification_items: List[CertificationItem] = []
    raw_certs = structured_data.get("certifications") or []
    if isinstance(raw_certs, list):
        for item in raw_certs:
            if not isinstance(item, str) or not item.strip():
                continue
            certification_items.append(CertificationItem(
                id=str(uuid.uuid4())[:8],
                name=item.strip(),
                issuer="",
                issue_date="",
                expiry_date="",
                url="",
            ))

    # 8. Additional
    additional_items: List[AdditionalSectionItem] = []
    raw_other = structured_data.get("other") or []
    if isinstance(raw_other, list) and len(raw_other) > 0:
        other_bullets = [str(b).strip() for b in raw_other if isinstance(b, str) and b.strip()]
        if other_bullets:
            additional_items.append(AdditionalSectionItem(
                id=str(uuid.uuid4())[:8],
                section_title="Additional Information",
                bullets=other_bullets,
            ))

    return BuilderContent(
        contact=contact,
        summary=summary,
        experience=experience_items,
        projects=project_items,
        skills=skill_categories,
        education=education_items,
        certifications=certification_items,
        additional=additional_items,
    )
