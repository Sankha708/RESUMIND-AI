"""High-Fidelity Resume Document Parser Service.

Extracts text, preserves paragraph/section boundaries, normalizes structured profiles,
and identifies layout anomalies using PyMuPDF (fitz) and python-docx.
Strictly rule-based: zero AI hallucinations and zero metric/credential fabrication.
"""

import io
import re
import zipfile
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
import pymupdf as fitz  # Use the canonical PyMuPDF import; retain fitz namespace internally
import docx


class ParserError(Exception):
    """Base exception for document parsing failures."""
    pass


class CorruptDocumentError(ParserError):
    """Raised when document data is malformed or unreadable."""
    pass


class EncryptedDocumentError(ParserError):
    """Raised when document is password-protected or encrypted."""
    pass


class DocumentLimitExceededError(ParserError):
    """Raised when a document exceeds safe parsing resource limits."""
    pass


class UnsupportedFileTypeError(ParserError):
    """Raised when file extension or magic bytes do not match supported types."""
    pass


MAX_PDF_PAGES = 100
MAX_DOCX_ARCHIVE_MEMBERS = 1000
MAX_DOCX_UNCOMPRESSED_BYTES = 50 * 1024 * 1024
MAX_DOCX_MEMBER_BYTES = 25 * 1024 * 1024
MAX_DOCX_MEMBER_COMPRESSION_RATIO = 200
DOCX_RATIO_CHECK_MIN_BYTES = 1024 * 1024


# Section header patterns deliberately include common ATS/resume wording variants.
# Matching is centralized below so headings with inline content and page suffixes work too.
SECTION_PATTERNS = {
    "summary": re.compile(r"^(?:executive\s+summary|professional\s+summary|summary|profile|about\s+me|career\s+objective|objective)$", re.I),
    "experience": re.compile(r"^(?:work\s+experience|professional\s+experience|experience|employment\s+history|work\s+history|career\s+history|internship\s+experience)$", re.I),
    "education": re.compile(r"^(?:education|academic\s+background|academic\s+credentials|degrees|educational\s+history)$", re.I),
    "skills": re.compile(r"^(?:technical\s+skills(?:\s*&\s*proficiencies)?|technical\s+skills\s+and\s+proficiencies|areas\s+of\s+expertise|core\s+competencies|skills\s*&\s*proficiencies|skills|technologies|tools\s*&\s*technologies|technical\s+competencies)$", re.I),
    "projects": re.compile(r"^(?:key\s+projects(?:\s*&\s*initiatives)?|selected\s+projects|projects|personal\s+projects|technical\s+projects|projects\s*&\s*certifications)$", re.I),
    "certifications": re.compile(r"^(?:certifications|certificates|licenses|credentials|professional\s+certifications)$", re.I),
    "other": re.compile(r"^(?:achievements(?:\s*&\s*certifications)?|achievements\s*&\s*awards|awards\s*&\s*achievements|additional\s+information|honors(?:\s*&\s*awards)?|extracurricular\s+activities|volunteering)$", re.I),
}

# Aliases are used for detecting section headings embedded in a PDF text line.
_SECTION_ALIASES = [
    (key, alias)
    for key, aliases in {
        "summary": ["executive summary", "professional summary", "career objective", "objective", "summary", "profile", "about me"],
        "experience": ["professional experience", "work experience", "employment history", "work history", "career history", "internship experience", "experience"],
        "education": ["academic background", "academic credentials", "educational history", "education"],
        "skills": ["technical skills & proficiencies", "technical skills and proficiencies", "areas of expertise", "core competencies", "skills & proficiencies", "tools & technologies", "technical competencies", "technical skills", "technologies", "skills"],
        "projects": ["key projects & initiatives", "key projects", "selected projects", "personal projects", "technical projects", "projects & certifications", "projects"],
        "certifications": ["professional certifications", "certifications", "certificates", "licenses", "credentials"],
        "other": ["achievements & certifications", "achievements & awards", "awards & achievements", "additional information", "achievements", "honors & awards", "honors", "extracurricular activities", "volunteering"],
    }.items()
    for alias in aliases
]
_SECTION_ALIASES.sort(key=lambda pair: len(pair[1]), reverse=True)

# Date detection regex for tenure / experience splitting
# Includes both Unicode dashes (–—) and their Windows-1252 byte equivalents (\x96 \x97)
DATE_PATTERN = re.compile(
    r"\b(?:(?:Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|Jun(?:e)?|"
    r"Jul(?:y)?|Aug(?:ust)?|Sep(?:tember)?|Oct(?:ober)?|Nov(?:ember)?|Dec(?:ember)?)\.?\s+)?\d{4}\s*(?:-|\u2013|\u2014|\x96|\x97|to)\s*"
    r"(?:(?:Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|Jun(?:e)?|"
    r"Jul(?:y)?|Aug(?:ust)?|Sep(?:tember)?|Oct(?:ober)?|Nov(?:ember)?|Dec(?:ember)?)\.?\s+\d{4}|Present|Current|Now|\d{4})\b",
    re.IGNORECASE,
)

# Windows-1252 / CP-1252 byte-to-Unicode normalisation map.
# PyMuPDF sometimes extracts text with Windows-1252 control-plane bytes
# (0x80–0x9F) that are not valid ISO-8859-1; they require this mapping.
_CP1252_MAP: Dict[int, str] = {
    0x80: "\u20ac",  # €
    0x82: "\u201a",  # ‚
    0x83: "\u0192",  # ƒ
    0x84: "\u201e",  # „
    0x85: "\u2026",  # …
    0x86: "\u2020",  # †
    0x87: "\u2021",  # ‡
    0x88: "\u02c6",  # ˆ
    0x89: "\u2030",  # ‰
    0x8a: "\u0160",  # Š
    0x8b: "\u2039",  # ‹
    0x8c: "\u0152",  # Œ
    0x8e: "\u017d",  # Ž
    0x91: "\u2018",  # '
    0x92: "\u2019",  # '
    0x93: "\u201c",  # "
    0x94: "\u201d",  # "
    0x95: "\u2022",  # • (bullet)
    0x96: "\u2013",  # – (en-dash)
    0x97: "\u2014",  # — (em-dash)
    0x98: "\u02dc",  # ˜
    0x99: "\u2122",  # ™
    0x9a: "\u0161",  # š
    0x9b: "\u203a",  # ›
    0x9c: "\u0153",  # œ
    0x9e: "\u017e",  # ž
    0x9f: "\u0178",  # Ÿ
}


def normalize_text_encoding(text: str) -> str:
    """Replaces Windows-1252 control-plane byte sequences with proper Unicode.

    PyMuPDF occasionally extracts PDF text with bytes in the range 0x80–0x9F
    that are Windows-1252 private-use characters (bullet = \x95, en-dash = \x96,
    em-dash = \x97, etc.).  These bytes are *not* valid Unicode code points in
    that range (they are C1 control characters in ISO-8859-1 / Unicode), so they
    slip through as literal byte values in the Python string and cause every
    regex that tests for '•', '–', or '—' to silently fail.

    This function replaces them with their correct Unicode equivalents before
    any further parsing.
    """
    normalized = text.translate(_CP1252_MAP)
    # Repair a malformed entity observed in exported resume text without decoding
    # arbitrary entity sequences repeatedly or interpreting text as HTML.
    normalized = re.sub(r"&#x4[cC];anguages", "Languages", normalized, flags=re.IGNORECASE)
    return normalized

# Email and Phone regex patterns
EMAIL_PATTERN = re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b")
PHONE_PATTERN = re.compile(r"(?:\+?\d{1,3}[-.\s]?)?\(?\d{2,4}\)?[-.\s]?\d{3,4}[-.\s]?\d{3,4}\b")
URL_PATTERN = re.compile(r"\b(?:https?://)?(?:www\.)?(?:linkedin\.com/in/[a-zA-Z0-9_-]+|github\.com/[a-zA-Z0-9_-]+|[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}(?:/[^\s]*)?)\b", re.IGNORECASE)


def validate_file_signatures(content: bytes, declared_ext: str) -> str:
    """Validates magic bytes and internal structure for PDF and DOCX files.
    
    Returns:
        Canonical file type string ("pdf" or "docx")
    Raises:
        UnsupportedFileTypeError or CorruptDocumentError on invalid signatures.
    """
    if not content or len(content) < 8:
        raise CorruptDocumentError("The document is empty or unreadable.")

    # PDF validation
    if declared_ext.lower() == ".pdf":
        if not content.startswith(b"%PDF-"):
            raise UnsupportedFileTypeError("File extension is .pdf but content lacks valid %PDF- magic header.")
        return "pdf"

    # DOCX validation (ZIP archive containing [Content_Types].xml and word/document.xml)
    if declared_ext.lower() == ".docx":
        if not (content.startswith(b"PK\x03\x04") or content.startswith(b"PK\x05\x06") or content.startswith(b"PK\x07\x08")):
            raise UnsupportedFileTypeError("File extension is .docx but content lacks valid PK ZIP archive signature.")
        
        try:
            with zipfile.ZipFile(io.BytesIO(content)) as zf:
                members = zf.infolist()
                if len(members) > MAX_DOCX_ARCHIVE_MEMBERS:
                    raise DocumentLimitExceededError(
                        f"DOCX archive exceeds the {MAX_DOCX_ARCHIVE_MEMBERS}-part parsing limit."
                    )

                total_uncompressed = 0
                for member in members:
                    if member.flag_bits & 0x1:
                        raise CorruptDocumentError("Encrypted DOCX archive parts are not supported.")
                    if member.file_size > MAX_DOCX_MEMBER_BYTES:
                        raise DocumentLimitExceededError("A DOCX archive part exceeds the 25 MB parsing limit.")
                    total_uncompressed += member.file_size
                    if total_uncompressed > MAX_DOCX_UNCOMPRESSED_BYTES:
                        raise DocumentLimitExceededError("DOCX archive exceeds the 50 MB expanded-size limit.")
                    if (
                        member.file_size >= DOCX_RATIO_CHECK_MIN_BYTES
                        and member.file_size / max(member.compress_size, 1) > MAX_DOCX_MEMBER_COMPRESSION_RATIO
                    ):
                        raise DocumentLimitExceededError("DOCX archive contains an unusually compressed part.")

                namelist = {member.filename for member in members}
                if "word/document.xml" not in namelist or "[Content_Types].xml" not in namelist:
                    raise CorruptDocumentError("The DOCX package is corrupt or missing standard WordprocessingML parts.")
        except zipfile.BadZipFile as e:
            raise CorruptDocumentError("Corrupt DOCX document: invalid ZIP package structure.") from e
        return "docx"

    raise UnsupportedFileTypeError(f"Unsupported document format: '{declared_ext}'. Only .pdf and .docx are supported.")


def extract_text_from_pdf(content: bytes) -> Tuple[str, List[str]]:
    """Extracts text from PDF bytes using PyMuPDF in visual reading order.
    
    Returns:
        Tuple of (raw_text, warnings)
    """
    warnings = []
    text_blocks = []

    try:
        doc = fitz.open(stream=content, filetype="pdf")
    except Exception as e:
        raise CorruptDocumentError("Failed to open PDF document. The file may be damaged or malformed.") from e

    try:
        if doc.is_encrypted:
            raise EncryptedDocumentError("Password-protected or encrypted PDF documents are not supported.")

        page_count = doc.page_count
        if page_count == 0:
            raise CorruptDocumentError("PDF document contains 0 pages.")
        if page_count > MAX_PDF_PAGES:
            raise DocumentLimitExceededError(f"PDF exceeds the {MAX_PDF_PAGES}-page parsing limit.")

        total_extracted_chars = 0

        for page_idx in range(page_count):
            page = doc.load_page(page_idx)
            # Extract text blocks: (x0, y0, x1, y1, text, block_no, block_type)
            # block_type == 0 is text, block_type == 1 is image
            blocks = page.get_text("blocks")
            
            # Sort blocks primarily by vertical coordinate y0, then horizontal x0
            sorted_blocks = sorted(blocks, key=lambda b: (round(b[1], -1), b[0]))
            
            page_text_pieces = []
            for b in sorted_blocks:
                if b[6] == 0:  # Text block
                    block_text = b[4].strip()
                    if block_text:
                        page_text_pieces.append(block_text)
                        total_extracted_chars += len(block_text)

            if page_text_pieces:
                text_blocks.append("\n\n".join(page_text_pieces))

        # Check for image-only or scanned PDF
        if total_extracted_chars < 30 and page_count > 0:
            warnings.append(
                "Scanned or image-only document detected: No extractable text layer found. "
                "OCR is not supported in this phase."
            )

        raw_text = "\n\n--- Page Break ---\n\n".join(text_blocks)
        return raw_text, warnings

    finally:
        doc.close()


def extract_text_from_docx(content: bytes) -> Tuple[str, List[str]]:
    """Extracts text from DOCX bytes using python-docx preserving headings and paragraphs.
    
    Returns:
        Tuple of (raw_text, warnings)
    """
    warnings = []
    paragraphs_text = []

    try:
        doc = docx.Document(io.BytesIO(content))
    except Exception as e:
        raise CorruptDocumentError("Failed to parse DOCX document. File structure may be damaged.") from e

    for p in doc.paragraphs:
        txt = p.text.strip()
        if txt:
            paragraphs_text.append(txt)

    # Also inspect document tables if present
    for table in doc.tables:
        for row in table.rows:
            row_cells = [cell.text.strip() for cell in row.cells if cell.text.strip()]
            if row_cells:
                # Deduplicate identical adjacent cells (often caused by merged cells)
                unique_cells = []
                for c in row_cells:
                    if not unique_cells or c != unique_cells[-1]:
                        unique_cells.append(c)
                paragraphs_text.append(" | ".join(unique_cells))

    if not paragraphs_text:
        warnings.append("Document appears empty or contains no readable text paragraphs.")

    raw_text = "\n\n".join(paragraphs_text)
    return raw_text, warnings


def extract_contact_info(text: str) -> Dict[str, Any]:
    """Extract contact details without treating email-provider domains as URLs."""
    text = normalize_text_encoding(text or "")
    lines = [line.strip() for line in text.split("\n") if line.strip() and not line.startswith("--- Page Break")]
    top_chunk = "\n".join(lines[:20])

    email_matches = list(EMAIL_PATTERN.finditer(top_chunk)) or list(EMAIL_PATTERN.finditer(text))
    email = email_matches[0].group(0) if email_matches else None
    email_domains = {m.group(0).rsplit("@", 1)[-1].lower() for m in email_matches}

    phone_match = PHONE_PATTERN.search(top_chunk) or PHONE_PATTERN.search(text)
    phone = phone_match.group(0).strip() if phone_match else None

    # Remove full email addresses before URL scanning. Exclude common mail-provider domains,
    # including a stray "gmail.com" next to an email in extracted text.
    url_scan_text = EMAIL_PATTERN.sub(" ", "\n".join(lines[:6]))
    excluded_domains = {
        "gmail.com", "googlemail.com", "yahoo.com", "yahoo.co.in", "outlook.com",
        "hotmail.com", "live.com", "icloud.com", "proton.me", "protonmail.com",
        "rediffmail.com", "aol.com", "mail.com", "zoho.com",
    } | email_domains
    urls: List[str] = []
    for match in URL_PATTERN.finditer(url_scan_text):
        candidate = match.group(0).strip().rstrip(".,;)")
        host = candidate.lower().removeprefix("https://").removeprefix("http://").removeprefix("www.").split("/", 1)[0]
        if host in excluded_domains or "@" in candidate:
            continue
        source_line = url_scan_text[:match.start()].splitlines()[-1] if url_scan_text[:match.start()].splitlines() else ""
        current_line = url_scan_text.splitlines()[0] if "\n" not in url_scan_text else ""
        # Unprefixed domains are only treated as contact URLs when a path is present or the
        # same line has contact separators. This prevents B.Tech / Next.js from becoming URLs.
        explicit = candidate.lower().startswith(("http://", "https://", "www."))
        has_path = "/" in candidate
        context_line = next((ln for ln in url_scan_text.splitlines() if candidate in ln), "")
        contact_like = bool(EMAIL_PATTERN.search(context_line) or PHONE_PATTERN.search(context_line) or "|" in context_line or "•" in context_line)
        if not (explicit or has_path or contact_like):
            continue
        if candidate not in urls:
            urls.append(candidate)

    name = None
    name_uncertain = True
    for line in lines[:5]:
        clean_line = re.sub(r"[^a-zA-Z\s.-]", "", line).strip()
        words = clean_line.split()
        if 2 <= len(words) <= 4 and "@" not in line and not line.lower().startswith(("http", "www", "resume", "curriculum")):
            name = clean_line
            name_uncertain = False
            break
    if not name and lines:
        name = lines[0][:50]
        name_uncertain = True

    return {
        "name": name,
        "email": email,
        "phone": phone,
        "urls": urls,
        "location": None,
        "uncertainty": {"name": name_uncertain, "email": email is None, "phone": phone is None},
    }


def _heading_prefix(line: str) -> Optional[Tuple[str, str]]:
    """Return (section, content-after-heading) for a standalone or inline heading prefix."""
    candidate = normalize_text_encoding(line or "").strip()
    candidate = re.sub(r"^\s*(?:[•*#]+|\d+[.)])\s*", "", candidate)
    candidate = re.sub(r"\s*\(\s*page\s+\d+\s*\)\s*$", "", candidate, flags=re.I).strip()
    for section, pattern in SECTION_PATTERNS.items():
        # Full standalone header
        if pattern.match(candidate.strip(" :：|-–—_#*")):
            return section, ""
    # Heading followed by content on the same PDF text line.
    for section, alias in _SECTION_ALIASES:
        alias_regex = re.escape(alias).replace(r"\ ", r"\s+")
        match = re.match(rf"^\s*{alias_regex}\s*(?:[:：,|]\s*|\s+[|–—-]\s+)(.*)$", candidate, re.I)
        if match:
            return section, match.group(1).strip()
    return None


def _find_inline_heading(line: str) -> Optional[Tuple[int, int, str, str]]:
    """Find a likely section label embedded after a separator in a long extracted line."""
    candidates = []
    for section, alias in _SECTION_ALIASES:
        alias_regex = re.escape(alias).replace(r"\ ", r"\s+")
        pattern = re.compile(rf"(?<!\w)({alias_regex})(?=\s*[:：,|])", re.I)
        for match in pattern.finditer(line):
            if match.start() == 0:
                continue
            prefix = line[:match.start()]
            # Inline headings should be separated from preceding text and are commonly uppercase.
            if not prefix or prefix[-1] not in ",;| \t":
                continue
            matched_text = match.group(1)
            after = line[match.end():]
            # Require a clear delimiter immediately following the heading.
            delim = re.match(r"\s*([:：,|])\s*", after)
            if not delim:
                continue
            # Avoid interpreting ordinary prose as a section: require an uppercase heading or
            # explicit comma/pipe-separated title-case heading.
            is_upper_heading = matched_text.upper() == matched_text
            if not is_upper_heading and prefix.rstrip()[-1:] not in ",;|":
                continue
            candidates.append((match.start(), match.end() + delim.end(), section, alias))
    if not candidates:
        return None
    candidates.sort(key=lambda item: (item[0], -(item[1] - item[0])))
    # Choose earliest and longest overlap at that position.
    earliest = candidates[0][0]
    same_start = [c for c in candidates if c[0] == earliest]
    return max(same_start, key=lambda item: item[1] - item[0])


def _unique_strings(items: List[str]) -> List[str]:
    out: List[str] = []
    seen = set()
    for item in items:
        value = normalize_text_encoding(item).strip(" \t,;|•·")
        if value and value.casefold() not in seen:
            seen.add(value.casefold())
            out.append(value)
    return out


def _parse_skill_categories(skill_lines: List[str]) -> Tuple[List[str], List[Dict[str, Any]]]:
    """Extract categorized skill labels while preserving the flat skill list used by review UI."""
    category_aliases = [
        "Programming Languages", "Languages", "Frontend", "Backend", "Web Development",
        "Generative AI & NLP", "Generative AI and NLP", "Machine Learning", "Data Analysis",
        "Data", "Databases", "Database Management & Cloud Computing", "Developer Tools",
        "Tools", "Fundamentals", "Working knowledge", "Cloud Computing", "Frameworks",
    ]
    alias_re = "|".join(re.escape(a).replace(r"\ ", r"\s+") for a in sorted(category_aliases, key=len, reverse=True))
    label_re = re.compile(rf"(?<!\w)({alias_re})\s*:\s*", re.I)
    categories: List[Dict[str, Any]] = []
    flat: List[str] = []
    uncategorized: List[str] = []

    for line in skill_lines:
        text = normalize_text_encoding(line).strip()
        if not text:
            continue
        matches = list(label_re.finditer(text))
        if not matches:
            uncategorized.extend(t.strip() for t in re.split(r"[,;|•·\u2022\u2023\u25e6\u25aa]", text) if t.strip())
            continue
        for idx, match in enumerate(matches):
            stop = matches[idx + 1].start() if idx + 1 < len(matches) else len(text)
            value_text = text[match.end():stop].strip(" ,;|•·")
            skills = _unique_strings(re.split(r"[,;|•·\u2022\u2023\u25e6\u25aa]", value_text))
            category_name = match.group(1).strip()
            existing = next((c for c in categories if c["category"].casefold() == category_name.casefold()), None)
            if existing is None:
                existing = {"category": category_name, "skills": []}
                categories.append(existing)
            existing["skills"] = _unique_strings(existing["skills"] + skills)
            flat.extend(skills)

    uncategorized = _unique_strings(uncategorized)
    if uncategorized:
        categories.append({"category": "Technical Skills", "skills": uncategorized})
        flat.extend(uncategorized)
    flat = _unique_strings(flat)
    if not categories and flat:
        categories = [{"category": "Technical Skills", "skills": flat}]
    return flat, categories


def parse_structured_profile(raw_text: str, initial_warnings: List[str]) -> Dict[str, Any]:
    """Parse resume sections conservatively, including common heading variants and inline headings."""
    warnings = list(initial_warnings)
    raw_text = normalize_text_encoding(raw_text or "")
    contact = extract_contact_info(raw_text)

    sections: Dict[str, List[str]] = {
        "summary": [], "experience": [], "education": [], "skills": [],
        "projects": [], "certifications": [], "other": [],
    }
    current_section = "preamble"

    def append_current(text: str) -> None:
        value = normalize_text_encoding(text).strip()
        if not value or value.startswith("--- Page Break") or current_section == "preamble":
            return
        sections[current_section].append(value)

    for raw_line in raw_text.splitlines():
        line = normalize_text_encoding(raw_line).strip()
        if not line or line.startswith("--- Page Break"):
            continue

        prefix = _heading_prefix(line)
        if prefix:
            current_section, remainder = prefix
            if remainder:
                # Process an inline heading further along the same extracted text block.
                pending = remainder
                while pending:
                    inline = _find_inline_heading(pending)
                    if not inline:
                        append_current(pending)
                        break
                    idx, after_idx, next_section, _ = inline
                    append_current(pending[:idx].rstrip(" ,;|"))
                    current_section = next_section
                    pending = pending[after_idx:].strip()
            continue

        pending = line
        while pending:
            inline = _find_inline_heading(pending)
            if not inline:
                append_current(pending)
                break
            idx, after_idx, next_section, _ = inline
            append_current(pending[:idx].rstrip(" ,;|"))
            current_section = next_section
            pending = pending[after_idx:].strip()

    skills_list, skill_categories = _parse_skill_categories(sections["skills"])

    # Certs are often comma-separated on one extracted line; split conservatively on list delimiters.
    certifications: List[str] = []
    for item in sections["certifications"]:
        clean = re.sub(r"^certifications?\s*:\s*", "", item, flags=re.I).strip()
        certifications.extend(part.strip() for part in re.split(r"[;|\u2022\u2023\u25e6\u25aa\u00b7]+|,\s*(?=[A-Z])", clean) if part.strip())
    certifications = _unique_strings(certifications)

    # Avoid repeating contact/header material under Additional Information.
    other = []
    contact_values = {str(v).strip().casefold() for v in [contact.get("name"), contact.get("email"), contact.get("phone")] if v}
    contact_urls = {str(v).strip().casefold() for v in contact.get("urls", [])}
    for item in sections["other"]:
        candidate = item.strip()
        if candidate.casefold() in contact_values or candidate.casefold() in contact_urls:
            continue
        if EMAIL_PATTERN.fullmatch(candidate) or PHONE_PATTERN.fullmatch(candidate):
            continue
        other.append(candidate)

    summary_text = "\n".join(sections["summary"]).strip() or None
    if not sections["experience"]:
        warnings.append("No distinct experience section header was recognized.")
    if not sections["education"]:
        warnings.append("No distinct education section header was recognized.")
    if not skills_list:
        warnings.append("No distinct skills section header was recognized.")

    return {
        "contact": contact,
        "summary": summary_text,
        "experience": sections["experience"],
        "education": sections["education"],
        "skills": skills_list,
        "skill_categories": skill_categories,
        "projects": sections["projects"],
        "certifications": certifications,
        "other": other,
        "warnings": list(dict.fromkeys(warnings)),
    }


def parse_resume_document(content: bytes, filename: str) -> Tuple[str, Dict[str, Any]]:
    """Primary entrypoint: validates, extracts, and structures a resume document.
    
    Returns:
        Tuple of (raw_text, structured_profile)
    """
    ext = Path(filename).suffix.lower()
    file_type = validate_file_signatures(content, ext)

    if file_type == "pdf":
        raw_text, warnings = extract_text_from_pdf(content)
    elif file_type == "docx":
        raw_text, warnings = extract_text_from_docx(content)
    else:
        raise UnsupportedFileTypeError(f"Unsupported document format '{ext}'")

    raw_text = normalize_text_encoding(raw_text)
    structured = parse_structured_profile(raw_text, warnings)
    return raw_text, structured
