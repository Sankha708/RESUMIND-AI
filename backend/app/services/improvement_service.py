"""Improvement Opportunity Generation and Revision Service.

Generates grounded, rule-based resume improvement opportunities from reviewed
resume content and ATS diagnostic patterns.
Strictly non-generative: zero hallucinated metrics, zero fabricated employers
or achievements, and transparent editable placeholders like
'[Add verified metric if available]'.
"""

from __future__ import annotations

import re
from typing import Any, Dict, List, Optional, Set, Tuple
from app.services.scoring_service import ACTION_VERBS, METRIC_REGEX, PASSIVE_STARTERS

IMPROVEMENT_DISCLAIMER: str = (
    "RESUMIND AI Improvement Studio combines rule-based structural guidance with optional local AI-powered rewriting. "
    "Rule-based suggestions are grounded in your actual resume text. "
    "AI-generated proposals require explicit Accept/Reject review — they are never applied automatically. "
    "You retain complete editorial control. Verify all AI-generated text before acceptance."
)

VERB_SYNONYMS: Dict[str, List[str]] = {
    "developed": ["engineered", "architected", "constructed", "spearheaded", "formulated"],
    "built": ["constructed", "engineered", "designed", "implemented", "deployed"],
    "created": ["authored", "originated", "established", "instituted", "conceived"],
    "managed": ["orchestrated", "directed", "administered", "guided", "coordinated"],
    "led": ["spearheaded", "directed", "championed", "guided", "mentored"],
    "worked": ["collaborated", "engineered", "partnered", "executed", "delivered"],
}


class StaleContentError(Exception):
    """Raised when target resume content has changed since suggestion was generated."""
    pass


def suggest_action_verb_replacement(bullet: str) -> Optional[Tuple[str, str]]:
    """Identifies passive starters and proposes active replacements without altering content."""
    lower_bullet = bullet.lower().strip()
    clean_bullet = bullet.strip().lstrip("•-*–— ").strip()

    for starter in PASSIVE_STARTERS:
        if lower_bullet.startswith(starter):
            remainder = clean_bullet[len(starter):].strip()
            # If remainder starts with "-ing" verb, convert to past tense:
            words = remainder.split()
            if words:
                first = words[0].lower()
                verb_candidate = first
                # Common gerund conversions
                if first.endswith("ing"):
                    base = first[:-3]
                    if base.endswith("ll") or base.endswith("ss") or base.endswith("tt"):
                        past = base[:-1] + "ed"
                    elif base.endswith("iz"):
                        past = base + "ed"
                    elif base.endswith("at"):
                        past = base + "ed"
                    else:
                        past = base + "ed"
                    # Check if valid past tense or in action verbs
                    if past in ACTION_VERBS:
                        verb_candidate = past
                    elif base + "d" in ACTION_VERBS:
                        verb_candidate = base + "d"
                    else:
                        verb_candidate = "Engineered"

                rest = " ".join(words[1:]) if len(words) > 1 else ""
                proposed = f"{verb_candidate.capitalize()} {rest}".strip()
                return (
                    f"Passive starter '{starter.title()}' weakens personal agency. Lead directly with an action verb.",
                    proposed,
                )

            # Fallback direct active verb
            return (
                f"Passive starter '{starter.title()}' weakens impact. Lead directly with an active verb.",
                f"Delivered {remainder}",
            )

    return None


def generate_opportunities_for_bullet(
    bullet: str,
    section: str,
    item_index: int,
    seen_first_words: Dict[str, int],
) -> List[Dict[str, Any]]:
    """Analyzes a single bullet statement and returns grounded improvement opportunities."""
    clean_bullet = bullet.strip().lstrip("•-*–— ").strip()
    words = [w.strip(".,;:•-–—()[]*\"'") for w in clean_bullet.split()]
    words = [w for w in words if w]
    word_count = len(words)

    # Ignore empty or single-character items
    if word_count < 2:
        return []

    opportunities: List[Dict[str, Any]] = []

    # 1. Check for Passive Starters
    passive_res = suggest_action_verb_replacement(clean_bullet)
    if passive_res:
        explanation, proposed = passive_res
        opportunities.append({
            "section": section,
            "item_index": item_index,
            "category": "action_verb",
            "original_text": bullet,
            "proposed_text": proposed,
            "explanation": explanation,
        })
        return opportunities  # Prioritize fixing passive start first

    # 2. Check for Overly Dense / Run-On Bullets (> 32 words)
    if word_count > 32:
        # Suggest tightening without losing factual items
        conjunctions = [", resulting in", ", which led to", ", and also", " while "]
        split_point = -1
        for conj in conjunctions:
            pos = clean_bullet.find(conj)
            if pos != -1 and 15 < len(clean_bullet[:pos].split()) < 30:
                split_point = pos
                break

        if split_point != -1:
            part1 = clean_bullet[:split_point].strip().rstrip(".") + "."
            part2 = clean_bullet[split_point + 1:].strip()
            part2 = part2[0].upper() + part2[1:] if part2 else ""
            proposed = f"{part1} {part2}"
        else:
            proposed = clean_bullet

        opportunities.append({
            "section": section,
            "item_index": item_index,
            "category": "brevity_readability",
            "original_text": bullet,
            "proposed_text": proposed,
            "explanation": f"Bullet is {word_count} words long. Modern ATS systems and hiring managers favor concise, focused statements (12–30 words).",
        })
        return opportunities

    # 3. Check for Very Short / Vague Bullet (< 6 words)
    if word_count < 6 and not any(w in clean_bullet.lower() for w in ["present", "current", "jan", "feb", "202"]):
        opportunities.append({
            "section": section,
            "item_index": item_index,
            "category": "scope_clarity",
            "original_text": bullet,
            "proposed_text": f"{clean_bullet.rstrip('.')} utilizing [specific technologies/tools] to [deliver business outcome].",
            "explanation": "Brief statement lacks technical context and outcomes. Specify the tools used and the end objective.",
        })
        return opportunities

    # 4. Check for Repetitive Action Verbs across resume
    first_word = words[0].lower()
    if seen_first_words.get(first_word, 0) >= 2 and first_word in VERB_SYNONYMS:
        synonyms = VERB_SYNONYMS[first_word]
        # Pick synonym not yet heavily used
        alt_verb = synonyms[(seen_first_words[first_word] - 2) % len(synonyms)]
        rest = " ".join(words[1:])
        proposed = f"{alt_verb.capitalize()} {rest}"
        opportunities.append({
            "section": section,
            "item_index": item_index,
            "category": "repetition",
            "original_text": bullet,
            "proposed_text": proposed,
            "explanation": f"The verb '{first_word.capitalize()}' is used multiple times across your experience. Diversify with high-impact synonyms.",
        })
        return opportunities

    # 5. Check for Missing Quantifiable Metric (Impact Placeholder)
    has_metric = bool(METRIC_REGEX.search(clean_bullet))
    if not has_metric:
        # Weave an explicit, honest placeholder
        proposed = f"{clean_bullet.rstrip('.')} [resulting in +__% efficiency / supporting __ users]."
        opportunities.append({
            "section": section,
            "item_index": item_index,
            "category": "quantifiable_impact",
            "original_text": bullet,
            "proposed_text": proposed,
            "explanation": "Statement describes task activities without quantifiable results. Weave in verifiable metrics (e.g. % improvement, latency reduction, volume) using the editable placeholder.",
        })

    return opportunities


def generate_improvement_opportunities(
    structured_data: Dict[str, Any],
) -> List[Dict[str, Any]]:
    """Analyzes reviewed resume structured data and generates prioritized opportunities."""
    all_opportunities: List[Dict[str, Any]] = []
    seen_first_words: Dict[str, int] = {}

    # Inspect Experience Section
    experience_list = structured_data.get("experience") or []
    for idx, bullet in enumerate(experience_list):
        if not isinstance(bullet, str) or not bullet.strip():
            continue
        clean = bullet.strip().lstrip("•-*–— ").strip()
        first_w = clean.split()[0].lower() if clean.split() else ""
        if first_w:
            seen_first_words[first_w] = seen_first_words.get(first_w, 0) + 1

        opps = generate_opportunities_for_bullet(bullet, "experience", idx, seen_first_words)
        all_opportunities.extend(opps)

    # Inspect Projects Section
    projects_list = structured_data.get("projects") or []
    for idx, bullet in enumerate(projects_list):
        if not isinstance(bullet, str) or not bullet.strip():
            continue
        clean = bullet.strip().lstrip("•-*–— ").strip()
        first_w = clean.split()[0].lower() if clean.split() else ""
        if first_w:
            seen_first_words[first_w] = seen_first_words.get(first_w, 0) + 1

        opps = generate_opportunities_for_bullet(bullet, "projects", idx, seen_first_words)
        all_opportunities.extend(opps)

    # Inspect Summary Section
    summary = structured_data.get("summary")
    if summary and isinstance(summary, str) and 15 <= len(summary.split()) <= 40:
        if not METRIC_REGEX.search(summary):
            clean_sum = summary.strip().rstrip(".")
            all_opportunities.append({
                "section": "summary",
                "item_index": None,
                "category": "scope_clarity",
                "original_text": summary,
                "proposed_text": f"{clean_sum} with core expertise in [Key Domains/Technologies] and track record of [Key Achievement/Impact].",
                "explanation": "Strengthen your professional summary with concrete domain specializations and a signature achievement placeholder.",
            })

    # Return up to 10 high-value, distinct opportunities
    return all_opportunities[:10]


def apply_suggestion_to_resume(
    structured_data: Dict[str, Any],
    section: str,
    item_index: Optional[int],
    original_text: str,
    replacement_text: str,
) -> Dict[str, Any]:
    """Applies an accepted improvement to the canonical resume structured data.
    
    Verifies that the target content has not drifted before applying.
    """
    updated_data = dict(structured_data)

    if section == "summary":
        current = updated_data.get("summary")
        if current and current.strip() != original_text.strip() and current.strip() != replacement_text.strip():
            raise StaleContentError("Summary content has changed since the suggestion was created.")
        updated_data["summary"] = replacement_text
        return updated_data

    if section in ["experience", "projects"]:
        items = list(updated_data.get(section) or [])
        if item_index is None or item_index >= len(items):
            raise StaleContentError(f"Target {section} index {item_index} is out of bounds.")

        current = items[item_index]
        if current.strip() != original_text.strip() and current.strip() != replacement_text.strip():
            raise StaleContentError(f"Target {section} item content has drifted from original.")

        items[item_index] = replacement_text
        updated_data[section] = items
        return updated_data

    raise StaleContentError(f"Unsupported section '{section}' for direct improvement application.")


def restore_original_in_resume(
    structured_data: Dict[str, Any],
    section: str,
    item_index: Optional[int],
    original_text: str,
) -> Dict[str, Any]:
    """Restores the original text into the canonical resume structured data."""
    updated_data = dict(structured_data)
    if section == "summary":
        updated_data["summary"] = original_text
        return updated_data
    if section in ["experience", "projects"]:
        items = list(updated_data.get(section) or [])
        if item_index is not None and item_index < len(items):
            items[item_index] = original_text
            updated_data[section] = items
            return updated_data
    return updated_data
