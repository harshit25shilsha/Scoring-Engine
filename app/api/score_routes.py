from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.session import get_postgres_session
from app.services.rule_scoring_service import RuleScoringService
from app.services.semantic_scoring_service import SemanticScoringService
from app.services.final_scoring_service import FinalScoringService

from app.core.rate_limit import try_acquire_rescore_lock, release_rescore_lock
from app.core.token_budget import get_remaining_budget,get_used_today,DAILY_TOKEN_LIMIT

router = APIRouter(tags=["scoring"])



@router.post(
    "/generate-score/{job_id}",
    summary="Generate rule score",
    description="Backend/system endpoint. Requires a key with scope 'read_write'. This is not available to frontend 'read' keys.",
)
async def generate_score(
    job_id: int,
    db: AsyncSession = Depends(get_postgres_session),
):
    service = RuleScoringService(db)
    return await service.score_job_against_all_candidates(job_id)



@router.post(
    "/generate-semantic-score/{job_id}",
    summary="Generate semantic score",
    description="Backend/system endpoint. Requires a key with scope 'read_write'.",
)
async def generate_semantic_score(
    job_id: int,
    db: AsyncSession = Depends(get_postgres_session),
):
    service = SemanticScoringService(db)
    
    return await service.generate_semantic_scores_for_job(job_id)

@router.post(
    "/finalize-score/{job_id}",
    summary="Finalize score",
    description="Backend/system endpoint. Requires a key with scope 'read_write'.",
)
async def finalize_score(
    job_id: int,
    db: AsyncSession = Depends(get_postgres_session),
):
    service = FinalScoringService(db)
    return await service.finalize_scores_for_job(job_id)



@router.get(
    "/jobs/{job_id}/candidates",
    summary="Get ranked candidates",
    description="Read access endpoint for candidate rankings. Requires a key with scope 'read' or 'read_write'.",
)
async def get_ranked_candidates(
    job_id: int,
    page: int = 1,
    page_size: int = 20,
    min_score: float | None = None,
    sort_by: str = "overall_score",
    sort_order: str = "desc",
    db: AsyncSession = Depends(get_postgres_session),
):
    service = FinalScoringService(db)
    return await service.get_ranked_candidates(
        job_id, page, page_size, min_score, sort_by, sort_order
    )
    


@router.get(
    "/groq-budget",
    summary="Get Groq budget status",
    description="Read access endpoint for token budget status. Requires a key with scope 'read' or 'read_write'.",
)
async def get_groq_budget_status():
    used = get_used_today()
    remaining = get_remaining_budget()
    return {
        "daily_limit": DAILY_TOKEN_LIMIT,
        "used_today": used,
        "remaining": remaining,
        "percent_used": round((used / DAILY_TOKEN_LIMIT) * 100, 1) if DAILY_TOKEN_LIMIT else 0,
    }