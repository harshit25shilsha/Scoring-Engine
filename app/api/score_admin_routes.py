from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.session import get_postgres_session
from app.core.rate_limit import try_acquire_rescore_lock, release_rescore_lock
from app.core.token_budget import has_sufficient_budget, get_remaining_budget
from app.services.rule_scoring_service import RuleScoringService
from app.services.semantic_scoring_service import SemanticScoringService
from app.services.final_scoring_service import FinalScoringService

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