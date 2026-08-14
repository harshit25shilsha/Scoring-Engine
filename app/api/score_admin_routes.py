from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.session import get_postgres_session
from app.database.models import ApiKey
from app.core.auth import require_admin_scope
from app.core.rate_limit import try_acquire_rescore_lock, release_rescore_lock
from app.core.token_budget import has_sufficient_budget, get_remaining_budget
from app.services.rule_scoring_service import RuleScoringService
from app.services.semantic_scoring_service import SemanticScoringService
from app.services.final_scoring_service import FinalScoringService
from app.schemas.score_override import ScoreOverrideRequest



router = APIRouter(tags=["scoring-admin"])


@router.post("/jobs/{job_id}/rescore")
async def rescore_job_now(
    job_id: int,
    db: AsyncSession = Depends(get_postgres_session),
):
    if not has_sufficient_budget():
        remaining = get_remaining_budget()
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Insufficient Groq token budget remaining today ({remaining} tokens). Try again tomorrow.",
        )

    acquired = await try_acquire_rescore_lock(job_id)
    if not acquired:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Job {job_id} was rescored recently. Please wait before retrying.",
        )

    try:
        rule_service = RuleScoringService(db)
        semantic_service = SemanticScoringService(db)
        final_service = FinalScoringService(db)

        rule_result = await rule_service.score_job_against_all_candidates(job_id)
        semantic_result = await semantic_service.generate_semantic_scores_for_job(job_id)
        final_result = await final_service.finalize_scores_for_job(job_id)

        return {
            "job_id": job_id,
            "status": "completed",
            "rule": rule_result,
            "semantic": semantic_result,
            "final": final_result,
        }
    finally:
        await release_rescore_lock(job_id)


@router.patch("/candidate/{candidate_id}/scores/{job_id}")
async def override_score(
    candidate_id: int,
    job_id: int,
    payload: ScoreOverrideRequest,
    key_row: ApiKey = Depends(require_admin_scope),
    db: AsyncSession = Depends(get_postgres_session),
):
    final_service = FinalScoringService(db)
    result = await final_service.override_candidate_score(
        candidate_id=candidate_id,
        job_id=job_id,
        override_score=payload.override_score,
        note=payload.note,
        overridden_by=key_row.name,
    )

    if result["status"] == "not_found":
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No score found for candidate={candidate_id} job={job_id}",
        )

    return result