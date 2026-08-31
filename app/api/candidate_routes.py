import json

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models import CandidateRaw, CandidateJobScore
from app.database.session import get_postgres_session
from app.schemas.candidate import CandidateResponse

router = APIRouter(prefix="/candidate", tags=["candidates"])


@router.get(
    "/{candidate_id}",
    response_model=CandidateResponse,
    summary="Get candidate by id",
    description="Frontend or backend read access endpoint. Requires a key with scope 'read' or 'read_write'.",
)
async def get_candidate(
    candidate_id: int,
    db: AsyncSession = Depends(get_postgres_session),
):
    candidate = await db.get(CandidateRaw, candidate_id)
    if candidate is None:
        raise HTTPException(status_code=404, detail="Candidate not found")
    return candidate


@router.get(
    "/{candidate_id}/scores",
    summary="Get candidate score history",
    description="Read access endpoint for candidate score results. Requires a key with scope 'read' or 'read_write'.",
)
async def get_candidate_scores(
    candidate_id: int,
    db: AsyncSession = Depends(get_postgres_session),
):
    candidate = await db.get(CandidateRaw, candidate_id)
    if candidate is None:
        raise HTTPException(status_code=404, detail="Candidate not found")

    result = await db.execute(
        select(CandidateJobScore)
        .where(
            CandidateJobScore.candidate_id == candidate_id,
            CandidateJobScore.overall_score.is_not(None),
        )
        .order_by(CandidateJobScore.overall_score.desc())
    )
    scores = result.scalars().all()

    return {
        "candidate_id": candidate_id,
        "total_jobs_scored": len(scores),
        "results": [
            {
                "job_id": s.job_id,
                "overall_score": s.overall_score,
                "rule_score": s.rule_score,
                "semantic_score": s.semantic_score,
                "matched_skills": json.loads(s.matched_skills or "[]"),
                "missing_skills": json.loads(s.missing_skills or "[]"),
                "recommendation": s.recommendation,
            }
            for s in scores
        ],
    }