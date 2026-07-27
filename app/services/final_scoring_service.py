import json
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.config.logging import logger
from app.database.models import CandidateJobScore


class FinalScoringService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def finalize_scores_for_job(self, job_id: int) -> dict:
        
        result = await self.db.execute(
            select(CandidateJobScore).where(
                CandidateJobScore.job_id == job_id,
                CandidateJobScore.rule_score.is_not(None),
                CandidateJobScore.semantic_score.is_not(None),
            )
        )
        scores = result.scalars().all()

        updated = 0
        for score_row in scores:
            overall = (
                score_row.rule_score * settings.RULE_SCORE_WEIGHT
                + score_row.semantic_score * settings.SEMANTIC_SCORE_WEIGHT
            )
            score_row.overall_score = round(overall, 2)
            score_row.generated_at = datetime.now(timezone.utc)
            updated += 1

        await self.db.commit()
        logger.info(f"[final-score] job={job_id} finalized={updated}")
        return {"job_id": job_id, "status": "completed", "finalized": updated}

    async def get_ranked_candidates(
        self,
        job_id: int,
        page: int = 1,
        page_size: int = 20,
        min_score: float | None = None,
        sort_by: str = "overall_score",
        sort_order: str = "desc",
    ) -> dict:
        query = select(CandidateJobScore).where(
            CandidateJobScore.job_id == job_id,
            CandidateJobScore.overall_score.is_not(None),
        )

        if min_score is not None:
            query = query.where(CandidateJobScore.overall_score >= min_score)

        sort_column_map = {
            "overall_score": CandidateJobScore.overall_score,
            "rule_score": CandidateJobScore.rule_score,
            "semantic_score": CandidateJobScore.semantic_score,
            "experience_score": CandidateJobScore.experience_score,
        }
        sort_column = sort_column_map.get(sort_by, CandidateJobScore.overall_score)
        query = query.order_by(
            sort_column.desc() if sort_order == "desc" else sort_column.asc()
        )

        count_result = await self.db.execute(query)
        all_matching = count_result.scalars().all()
        total = len(all_matching)

        offset = (page - 1) * page_size
        paginated = all_matching[offset : offset + page_size]

        results = [
            {
                "candidate_id": s.candidate_id,
                "overall_score": s.overall_score,
                "rule_score": s.rule_score,
                "semantic_score": s.semantic_score,
                "skills_score": s.skills_score,
                "experience_score": s.experience_score,
                "education_score": s.education_score,
                "location_score": s.location_score,
                "matched_skills": json.loads(s.matched_skills or "[]"),
                "missing_skills": json.loads(s.missing_skills or "[]"),
                "strengths": json.loads(s.strengths or "[]"),
                "weaknesses": json.loads(s.weaknesses or "[]"),
                "recommendation": s.recommendation,
            }
            for s in paginated
        ]

        return {
            "job_id": job_id,
            "total_candidates": total,
            "page": page,
            "page_size": page_size,
            "total_pages": (total + page_size - 1) // page_size,
            "results": results,
        }