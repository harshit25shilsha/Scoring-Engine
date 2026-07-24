from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.session import get_postgres_session
from app.services.rule_scoring_service import RuleScoringService

router = APIRouter(tags=["scoring"])


@router.post("/generate-score/{job_id}")
async def generate_score(
    job_id: int,
    db: AsyncSession = Depends(get_postgres_session),
):
    service = RuleScoringService(db)
    return await service.score_job_against_all_candidates(job_id)