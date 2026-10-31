"""Improvement Studio API router.

Provides endpoints to generate, review, accept, reject, edit, and restore
grounded resume improvement suggestions within the active session.
Phase 8 adds AI-powered rewriting via the local Ollama provider.
"""

import json
import logging
from typing import Optional
from fastapi import (
    APIRouter,
    Cookie,
    Depends,
    HTTPException,
    Query,
    status,
)
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database import get_db
from app.models.improvement import ImprovementSuggestion
from app.models.resume import UploadedResume
from app.schemas.improvement import (
    AIProviderStatusResponse,
    AIRewriteRequest,
    BatchAcceptRequest,
    BatchAcceptResponse,
    ImprovementSuggestionSchema,
    ImprovementSummaryResponse,
    UpdateSuggestionRequest,
)
from app.services.improvement_service import (
    IMPROVEMENT_DISCLAIMER,
    StaleContentError,
    apply_suggestion_to_resume,
    generate_improvement_opportunities,
    restore_original_in_resume,
)
from app.services.session_service import get_session_by_token
from app.providers import (
    get_llm_provider,
    OllamaUnavailableError,
    ModelNotFoundError,
    OllamaTimeoutError,
    OllamaGenerationError,
    LLMOutputValidationError,
    RewritePromptInput,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/improvement", tags=["Improvement Studio"])


def _build_summary_response(suggestions: list[ImprovementSuggestion]) -> ImprovementSummaryResponse:
    accepted = sum(1 for s in suggestions if s.status == "accepted")
    rejected = sum(1 for s in suggestions if s.status == "rejected")
    pending = sum(1 for s in suggestions if s.status in ["identified", "edited"])
    return ImprovementSummaryResponse(
        total_count=len(suggestions),
        accepted_count=accepted,
        rejected_count=rejected,
        pending_count=pending,
        suggestions=[ImprovementSuggestionSchema.model_validate(s) for s in suggestions],
        disclaimer=IMPROVEMENT_DISCLAIMER,
    )


@router.post(
    "/generate",
    response_model=ImprovementSummaryResponse,
    status_code=status.HTTP_200_OK,
    summary="Generate improvement suggestions for active resume",
)
async def generate_improvements(
    force_regenerate: bool = Query(default=False),
    resumind_session: Optional[str] = Cookie(default=None, alias=settings.SESSION_COOKIE_NAME),
    db: AsyncSession = Depends(get_db),
):
    """Generates grounded improvement suggestions for the active session's resume."""
    if not resumind_session:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Session missing or expired.",
        )

    session = await get_session_by_token(db, resumind_session)
    if not session:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Session missing or expired.",
        )

    stmt_resume = (
        select(UploadedResume)
        .where(UploadedResume.session_id == session.id)
        .order_by(desc(UploadedResume.created_at))
    )
    res_resume = await db.execute(stmt_resume)
    resume = res_resume.scalars().first()

    if not resume:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No resume document found in the active session. Upload a resume first.",
        )

    # Check for existing suggestions
    stmt_existing = (
        select(ImprovementSuggestion)
        .where(
            ImprovementSuggestion.session_id == session.id,
            ImprovementSuggestion.resume_id == resume.id,
        )
        .order_by(ImprovementSuggestion.created_at)
    )
    existing_res = await db.execute(stmt_existing)
    existing_suggestions = list(existing_res.scalars().all())

    if existing_suggestions and not force_regenerate:
        return _build_summary_response(existing_suggestions)

    # If force_regenerate, purge existing suggestions
    if existing_suggestions and force_regenerate:
        for s in existing_suggestions:
            await db.delete(s)
        await db.commit()

    # Generate grounded opportunities from reviewed structured data
    opportunities = generate_improvement_opportunities(resume.structured_data)

    new_entities: list[ImprovementSuggestion] = []
    for opp in opportunities:
        entity = ImprovementSuggestion(
            session_id=session.id,
            resume_id=resume.id,
            section=opp["section"],
            item_index=opp["item_index"],
            category=opp["category"],
            original_text=opp["original_text"],
            proposed_text=opp["proposed_text"],
            explanation=opp["explanation"],
            status="identified",
        )
        db.add(entity)
        new_entities.append(entity)

    await db.commit()
    for entity in new_entities:
        await db.refresh(entity)

    return _build_summary_response(new_entities)


@router.get(
    "",
    response_model=ImprovementSummaryResponse,
    summary="List improvement suggestions for active resume",
)
async def get_improvements(
    resumind_session: Optional[str] = Cookie(default=None, alias=settings.SESSION_COOKIE_NAME),
    db: AsyncSession = Depends(get_db),
):
    """Retrieves all generated improvement opportunities for the active resume."""
    if not resumind_session:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Session missing or expired.",
        )

    session = await get_session_by_token(db, resumind_session)
    if not session:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Session missing or expired.",
        )

    stmt_resume = (
        select(UploadedResume)
        .where(UploadedResume.session_id == session.id)
        .order_by(desc(UploadedResume.created_at))
    )
    res_resume = await db.execute(stmt_resume)
    resume = res_resume.scalars().first()

    if not resume:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No resume document found in the active session.",
        )

    stmt = (
        select(ImprovementSuggestion)
        .where(
            ImprovementSuggestion.session_id == session.id,
            ImprovementSuggestion.resume_id == resume.id,
        )
        .order_by(ImprovementSuggestion.created_at)
    )
    res = await db.execute(stmt)
    suggestions = list(res.scalars().all())

    return _build_summary_response(suggestions)


@router.put(
    "/{suggestion_id}",
    response_model=ImprovementSuggestionSchema,
    summary="Accept, reject, or edit an improvement suggestion",
)
async def update_suggestion(
    suggestion_id: str,
    payload: UpdateSuggestionRequest,
    resumind_session: Optional[str] = Cookie(default=None, alias=settings.SESSION_COOKIE_NAME),
    db: AsyncSession = Depends(get_db),
):
    """Updates a suggestion's status. If accepted, applies the change to the canonical resume data."""
    if not resumind_session:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Session missing or expired.",
        )

    session = await get_session_by_token(db, resumind_session)
    if not session:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Session missing or expired.",
        )

    stmt_resume = (
        select(UploadedResume)
        .where(UploadedResume.session_id == session.id)
        .order_by(desc(UploadedResume.created_at))
    )
    res_resume = await db.execute(stmt_resume)
    resume = res_resume.scalars().first()

    if not resume:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No resume document found in the active session.",
        )

    # Find suggestion scoped strictly to this session and resume
    stmt_sug = select(ImprovementSuggestion).where(
        ImprovementSuggestion.id == suggestion_id,
        ImprovementSuggestion.session_id == session.id,
        ImprovementSuggestion.resume_id == resume.id,
    )
    res_sug = await db.execute(stmt_sug)
    suggestion = res_sug.scalars().first()

    if not suggestion:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Improvement suggestion not found.",
        )

    action = payload.action.lower()

    if action == "accept":
        text_to_apply = (
            payload.user_edited_text.strip()
            if payload.user_edited_text
            else (suggestion.user_edited_text or suggestion.proposed_text)
        )
        try:
            updated_structured_data = apply_suggestion_to_resume(
                structured_data=resume.structured_data,
                section=suggestion.section,
                item_index=suggestion.item_index,
                original_text=suggestion.original_text,
                replacement_text=text_to_apply,
            )
            resume.structured_data = updated_structured_data
        except StaleContentError as e:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=str(e),
            )

        suggestion.status = "accepted"
        if payload.user_edited_text:
            suggestion.user_edited_text = payload.user_edited_text.strip()

    elif action == "reject":
        suggestion.status = "rejected"

    elif action == "edit":
        if not payload.user_edited_text:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Edited text must not be empty.",
            )
        suggestion.user_edited_text = payload.user_edited_text.strip()
        suggestion.status = "edited"

    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported action '{payload.action}'. Use 'accept', 'reject', or 'edit'.",
        )

    await db.commit()
    await db.refresh(suggestion)
    return suggestion


@router.post(
    "/batch-accept",
    response_model=BatchAcceptResponse,
    summary="Batch accept high-confidence recommendations",
)
async def batch_accept_suggestions(
    payload: BatchAcceptRequest,
    resumind_session: Optional[str] = Cookie(default=None, alias=settings.SESSION_COOKIE_NAME),
    db: AsyncSession = Depends(get_db),
):
    """Batch accepts high-confidence suggestions that do not contain unfilled placeholders."""
    if not resumind_session:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Session missing or expired.",
        )

    session = await get_session_by_token(db, resumind_session)
    if not session:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Session missing or expired.",
        )

    stmt_resume = (
        select(UploadedResume)
        .where(UploadedResume.session_id == session.id)
        .order_by(desc(UploadedResume.created_at))
    )
    res_resume = await db.execute(stmt_resume)
    resume = res_resume.scalars().first()

    if not resume:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No resume document found in the active session.",
        )

    stmt_sugs = (
        select(ImprovementSuggestion)
        .where(
            ImprovementSuggestion.session_id == session.id,
            ImprovementSuggestion.resume_id == resume.id,
        )
        .order_by(ImprovementSuggestion.created_at)
    )
    res_sugs = await db.execute(stmt_sugs)
    all_suggestions = list(res_sugs.scalars().all())

    accepted_count = 0
    skipped_count = 0

    for suggestion in all_suggestions:
        if suggestion.status not in ("identified", "edited"):
            continue

        if payload.category and suggestion.category != payload.category:
            continue

        replacement = (
            suggestion.user_edited_text.strip()
            if suggestion.user_edited_text
            else suggestion.proposed_text
        )

        # Check if placeholders exist
        if payload.only_without_placeholders and ("[" in replacement and "]" in replacement):
            skipped_count += 1
            continue

        try:
            updated_structured_data = apply_suggestion_to_resume(
                structured_data=resume.structured_data,
                section=suggestion.section,
                item_index=suggestion.item_index,
                original_text=suggestion.original_text,
                replacement_text=replacement,
            )
            resume.structured_data = updated_structured_data
            suggestion.status = "accepted"
            accepted_count += 1
        except StaleContentError:
            skipped_count += 1

    await db.commit()
    for s in all_suggestions:
        await db.refresh(s)

    return BatchAcceptResponse(
        accepted_count=accepted_count,
        skipped_count=skipped_count,
        suggestions=[ImprovementSuggestionSchema.model_validate(s) for s in all_suggestions],
        message=f"Successfully applied {accepted_count} suggestions ({skipped_count} skipped).",
    )


@router.post(
    "/{suggestion_id}/restore",
    response_model=ImprovementSuggestionSchema,
    summary="Restore original text and undo an accepted suggestion",
)
async def restore_suggestion(
    suggestion_id: str,
    resumind_session: Optional[str] = Cookie(default=None, alias=settings.SESSION_COOKIE_NAME),
    db: AsyncSession = Depends(get_db),
):
    """Reverts an accepted suggestion by restoring the original text into the resume."""
    if not resumind_session:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Session missing or expired.",
        )

    session = await get_session_by_token(db, resumind_session)
    if not session:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Session missing or expired.",
        )

    stmt_resume = (
        select(UploadedResume)
        .where(UploadedResume.session_id == session.id)
        .order_by(desc(UploadedResume.created_at))
    )
    res_resume = await db.execute(stmt_resume)
    resume = res_resume.scalars().first()

    if not resume:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No resume document found in the active session.",
        )

    stmt_sug = select(ImprovementSuggestion).where(
        ImprovementSuggestion.id == suggestion_id,
        ImprovementSuggestion.session_id == session.id,
        ImprovementSuggestion.resume_id == resume.id,
    )
    res_sug = await db.execute(stmt_sug)
    suggestion = res_sug.scalars().first()

    if not suggestion:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Improvement suggestion not found.",
        )

    if suggestion.status == "accepted":
        try:
            updated_structured_data = restore_original_in_resume(
                structured_data=resume.structured_data,
                section=suggestion.section,
                item_index=suggestion.item_index,
                original_text=suggestion.original_text,
            )
            resume.structured_data = updated_structured_data
        except StaleContentError as e:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=str(e),
            )

    suggestion.status = "identified"
    suggestion.user_edited_text = None

    await db.commit()
    await db.refresh(suggestion)
    return suggestion


# ── Phase 8: AI Provider Endpoints ───────────────────────────────────────────

@router.get(
    "/provider/status",
    response_model=AIProviderStatusResponse,
    summary="Check local AI provider availability and model readiness",
)
async def get_provider_status(
    resumind_session: Optional[str] = Cookie(default=None, alias=settings.SESSION_COOKIE_NAME),
):
    """Checks whether the configured local Ollama provider and model are operational."""
    if not resumind_session:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Session missing or expired.",
        )
    provider = get_llm_provider()
    health = await provider.check_health()
    return AIProviderStatusResponse(
        available=health.available,
        provider="ollama",
        model=health.model,
        status_message=health.status_message,
        installed_models=health.installed_models,
    )


@router.post(
    "/{suggestion_id}/rewrite",
    response_model=ImprovementSuggestionSchema,
    summary="Generate an AI-powered rewrite proposal for an existing suggestion",
)
async def generate_ai_rewrite(
    suggestion_id: str,
    payload: AIRewriteRequest,
    resumind_session: Optional[str] = Cookie(default=None, alias=settings.SESSION_COOKIE_NAME),
    db: AsyncSession = Depends(get_db),
):
    """Calls the local Ollama provider to produce a structured rewrite proposal for
    a specific rule-based suggestion. The proposal is saved to `proposed_text` but
    NOT automatically accepted — it still requires explicit user Accept action.
    """
    if not resumind_session:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Session missing or expired.",
        )

    session = await get_session_by_token(db, resumind_session)
    if not session:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Session missing or expired.",
        )

    # Load session's resume
    stmt_resume = (
        select(UploadedResume)
        .where(UploadedResume.session_id == session.id)
        .order_by(desc(UploadedResume.created_at))
    )
    res_resume = await db.execute(stmt_resume)
    resume = res_resume.scalars().first()

    if not resume:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No resume document found in the active session.",
        )

    # Load suggestion scoped strictly to this session and resume
    stmt_sug = select(ImprovementSuggestion).where(
        ImprovementSuggestion.id == suggestion_id,
        ImprovementSuggestion.session_id == session.id,
        ImprovementSuggestion.resume_id == resume.id,
    )
    res_sug = await db.execute(stmt_sug)
    suggestion = res_sug.scalars().first()

    if not suggestion:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Improvement suggestion not found.",
        )

    # Verify suggestion text still corresponds to current resume content
    structured_data = resume.structured_data or {}
    section_items = structured_data.get(suggestion.section, [])
    if suggestion.section != "summary" and isinstance(section_items, list):
        idx = suggestion.item_index
        if idx is not None and idx < len(section_items):
            current_text = section_items[idx]
            if (
                current_text.strip() != suggestion.original_text.strip()
                and current_text.strip() != suggestion.proposed_text.strip()
            ):
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="Resume content has changed since this suggestion was generated. Regenerate suggestions.",
                )

    # Build surrounding context bullets (other lines in same section for richer prompt)
    surrounding_bullets = []
    if isinstance(section_items, list) and suggestion.item_index is not None:
        surrounding_bullets = [
            b for i, b in enumerate(section_items)
            if i != suggestion.item_index and isinstance(b, str) and b.strip()
        ][:3]

    # Gather candidate skills as optional context
    candidate_skills = []
    skills_raw = structured_data.get("skills", [])
    if isinstance(skills_raw, list):
        candidate_skills = [str(s) for s in skills_raw if s][:20]
    elif isinstance(skills_raw, str):
        candidate_skills = [s.strip() for s in skills_raw.split(",") if s.strip()][:20]

    # Optional: use any stored job description from resume context
    job_description_context = None

    # Invoke local AI provider
    provider = get_llm_provider()

    try:
        rewrite_input = RewritePromptInput(
            original_text=suggestion.original_text,
            section=suggestion.section,
            category=suggestion.category,
            explanation=suggestion.explanation,
            surrounding_bullets=surrounding_bullets,
            job_description=job_description_context,
            candidate_skills=candidate_skills,
        )
        result = await provider.generate_rewrite(rewrite_input)

    except (OllamaUnavailableError, ModelNotFoundError) as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Local AI provider unavailable: {e}",
        )
    except OllamaTimeoutError as e:
        raise HTTPException(
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            detail=f"AI rewrite timed out: {e}",
        )
    except LLMOutputValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=f"AI generated response failed validation: {e}",
        )
    except OllamaGenerationError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"AI generation error: {e}",
        )
    except Exception as e:
        logger.error("Unexpected AI rewrite error: %s", e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred during AI rewriting.",
        )

    # Update suggestion with the AI proposal — NOT auto-accepted
    suggestion.proposed_text = result.rewritten_text
    suggestion.explanation = result.change_explanation or suggestion.explanation
    suggestion.is_ai_generated = True
    suggestion.ai_model = result.model_name
    suggestion.preserved_facts = json.dumps(result.preserved_facts)
    suggestion.potential_new_claims = json.dumps(result.potential_new_claims)
    suggestion.needs_user_verification = result.needs_user_verification
    # Reset to identified so the user consciously accepts or rejects the new AI proposal
    suggestion.status = "identified"
    suggestion.user_edited_text = None

    await db.commit()
    await db.refresh(suggestion)
    return suggestion
