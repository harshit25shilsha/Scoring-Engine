from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.session import get_postgres_session
from app.services.rule_scoring_service import RuleScoringService
from app.services.semantic_scoring_service import SemanticScoringService
from app.services.final_scoring_service import FinalScoringService
router = APIRouter(tags=["scoring"])


@router.post("/generate-score/{job_id}")
async def generate_score(
    job_id: int,
    db: AsyncSession = Depends(get_postgres_session),
):
    service = RuleScoringService(db)
    return await service.score_job_against_all_candidates(job_id)

@router.post("/generate-semantic-score/{job_id}")
async def generate_semantic_score(
    job_id: int,
    db: AsyncSession = Depends(get_postgres_session),
):
    service = SemanticScoringService(db)
    
    return await service.generate_semantic_scores_for_job(job_id)

@router.post("/finalize-score/{job_id}")
async def finalize_score(
    job_id: int,
    db: AsyncSession = Depends(get_postgres_session),
):
    service = FinalScoringService(db)
    return await service.finalize_scores_for_job(job_id)


@router.get("/jobs/{job_id}/candidates")
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