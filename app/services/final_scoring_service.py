import json
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.config.logging import logger
from app.database.models import CandidateJobScore
from app.core.cache import get_cached_ranked_candidates, set_cached_ranked_candidates, invalidate_ranked_candidates_cache


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
        await invalidate_ranked_candidates_cache(job_id)

        return {"job_id": job_id, "status": "completed", "finalized": updated}

    async def override_candidate_score(
        self, candidate_id: int, job_id: int, override_score: float, note: str, overridden_by: str
    ) -> dict:
        result = await self.db.execute(
            select(CandidateJobScore).where(
                CandidateJobScore.candidate_id == candidate_id,
                CandidateJobScore.job_id == job_id,
            )
        )
        score_row = result.scalar_one_or_none()

        if score_row is None:
            return {"status": "not_found", "candidate_id": candidate_id, "job_id": job_id}

        score_row.override_score = override_score
        score_row.override_note = note
        score_row.overridden_by = overridden_by
        score_row.score_source = "manual_override"
        score_row.overridden_at = datetime.now(timezone.utc)
        await self.db.commit()

        logger.info(
            f"[override] candidate={candidate_id} job={job_id} "
            f"override_score={override_score} by={overridden_by}"
        )

        await invalidate_ranked_candidates_cache(job_id)

        return {
            "status": "completed",
            "candidate_id": candidate_id,
            "job_id": job_id,
            "override_score": override_score,
            "override_note": note,
            "overridden_by": overridden_by,
            "score_source":"manual_override",
        }

    async def get_ranked_candidates(
        self,
        job_id: int,
        page: int = 1,
        page_size: int = 20,
        min_score: float | None = None,
        sort_by: str = "overall_score",
        sort_order: str = "desc",
    ) -> dict:
        cached = await get_cached_ranked_candidates(job_id, page, page_size, min_score, sort_by, sort_order)
        if cached is not None:
            logger.info(f"[cache] hit for job={job_id} page={page}")
            return cached

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
                "override_score": s.override_score,
                "override_note": s.override_note,
                "overridden_by": s.overridden_by,
                "score_source": s.score_source,
                "matched_skills": json.loads(s.matched_skills or "[]"),
                "missing_skills": json.loads(s.missing_skills or "[]"),
                "evidence": json.loads(s.evidence or "{}"),
                "strengths": json.loads(s.strengths or "[]"),
                "weaknesses": json.loads(s.weaknesses or "[]"),
                "recommendation": s.recommendation,
            }
            for s in paginated
        ]

        response = {
            "job_id": job_id,
            "total_candidates": total,
            "page": page,
            "page_size": page_size,
            "total_pages": (total + page_size - 1) // page_size,
            "results": results,
        }

        await set_cached_ranked_candidates(job_id, page, page_size, min_score, sort_by, sort_order, response)
        return response
