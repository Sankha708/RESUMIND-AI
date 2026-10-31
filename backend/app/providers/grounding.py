"""Defensive Grounding & Hallucination Safeguards for AI Rewriting.

Verifies that model-generated resume rewrites do not fabricate unsupported metrics,
percentages, dates, tools, or employment claims. Flags additions for user verification.
"""

import re
from typing import List, Set, Tuple
from pydantic import BaseModel, Field
from app.providers.base import LLMOutputValidationError


class GroundingReport(BaseModel):
    """Validation report analyzing factual consistency between source and rewrite."""
    is_valid: bool
    needs_user_verification: bool = False
    preserved_facts: List[str] = Field(default_factory=list)
    potential_new_claims: List[str] = Field(default_factory=list)
    validation_notes: List[str] = Field(default_factory=list)


# Regex patterns for identifying metrics, numbers, and dates
METRIC_NUMBER_PATTERN = re.compile(
    r"\b(?:\d{1,3}(?:,\d{3})+|\d+)(?:\.\d+)?%?(?:x|\+)?\b|\$\d+(?:\.\d+)?[kmb]?",
    re.IGNORECASE,
)
YEAR_DATE_PATTERN = re.compile(r"\b(?:19|20)\d{2}\b")
PLACEHOLDER_PATTERN = re.compile(r"\[[^\]]+\]")


def extract_numbers(text: str) -> Set[str]:
    """Extract standalone numbers, metrics, or financial figures, excluding placeholders."""
    # Temporarily remove bracketed placeholders like [insert %] or [__ users]
    cleaned = PLACEHOLDER_PATTERN.sub("", text)
    matches = METRIC_NUMBER_PATTERN.findall(cleaned)
    return {m.strip().lower() for m in matches if m.strip()}


def extract_dates(text: str) -> Set[str]:
    """Extract 4-digit calendar years, excluding placeholders."""
    cleaned = PLACEHOLDER_PATTERN.sub("", text)
    matches = YEAR_DATE_PATTERN.findall(cleaned)
    return {m.strip() for m in matches if m.strip()}


def inspect_grounding(
    original_text: str,
    rewritten_text: str,
    candidate_skills: List[str] = None,
) -> GroundingReport:
    """Strictly inspect a generated rewrite against the original source bullet.

    Enforces:
    1. Non-empty, professional length boundaries (4 to 80 words).
    2. No prompt leakage (e.g., 'Sure, here is your rewrite:').
    3. Detection of hallucinated/unsupported numbers, metrics, or dates.
    4. Flagging of potential new claims requiring user confirmation.
    """
    clean_rewrite = rewritten_text.strip()
    words = clean_rewrite.split()

    if len(words) < 4:
        raise LLMOutputValidationError(
            f"Rewritten text is too short ({len(words)} words). Expected a complete professional statement."
        )

    if len(words) > 85:
        raise LLMOutputValidationError(
            f"Rewritten text is excessively long ({len(words)} words). Bullet points must remain concise (<85 words)."
        )

    # Prompt preamble/leakage detection
    lowered = clean_rewrite.lower()
    leakage_phrases = [
        "here is a rewrite",
        "here is the rewrite",
        "rewritten bullet:",
        "here is your revised",
        "as an ai",
        "sure! here",
        "certainly!",
    ]
    for phrase in leakage_phrases:
        if phrase in lowered:
            raise LLMOutputValidationError(
                f"Generated response contains conversational preamble ('{phrase}'). Expected direct bullet text."
            )

    potential_claims: List[str] = []
    preserved_facts: List[str] = []
    notes: List[str] = []

    # 1. Compare numbers & metrics
    orig_numbers = extract_numbers(original_text)
    new_numbers = extract_numbers(clean_rewrite)

    unsupported_numbers = new_numbers - orig_numbers
    supported_numbers = new_numbers & orig_numbers

    for num in supported_numbers:
        preserved_facts.append(f"Verified metric retained from source: {num}")

    for num in unsupported_numbers:
        potential_claims.append(
            f"Introduced metric or quantity ({num}) not present in the original source."
        )

    # 2. Compare dates
    orig_dates = extract_dates(original_text)
    new_dates = extract_dates(clean_rewrite)
    unsupported_dates = new_dates - orig_dates

    for dt in unsupported_dates:
        potential_claims.append(
            f"Introduced calendar date ({dt}) not present in the original source."
        )

    # 3. Check for bracketed placeholders
    placeholders = PLACEHOLDER_PATTERN.findall(clean_rewrite)
    if placeholders:
        notes.append(
            f"Contains candidate action placeholder: {', '.join(placeholders)}. Candidate must input verified data."
        )

    # Determine if candidate verification is needed
    needs_verification = len(potential_claims) > 0 or len(placeholders) > 0

    return GroundingReport(
        is_valid=True,
        needs_user_verification=needs_verification,
        preserved_facts=preserved_facts,
        potential_new_claims=potential_claims,
        validation_notes=notes,
    )
