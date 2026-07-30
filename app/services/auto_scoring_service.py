from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text

from app.config import settings
from app.config.logging import logger
from app.database.models import JobRaw, ResumeProcessed, CandidateJobScore
from app.services.rule_scoring_service import RuleScoringService
from app.services.semantic_scoring_service import SemanticScoringService
from app.services.final_scoring_service import FinalScoringService


class AutoScoringService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.rule_service = RuleScoringService(db)
        self.semantic_service = SemanticScoringService(db)
        self.final_service = FinalScoringService(db)

    async def find_jobs_needing_scoring(self, limit: int) -> list[int]:
        query = text("""
            SELECT jr.job_id,
                   COALESCE(unscored.remaining, 0) + COALESCE(never_scored.missing, 0) AS total_remaining
            FROM jobs_raw jr
            LEFT JOIN (
                SELECT job_id, COUNT(*) AS remaining
                FROM candidate_job_scores
                WHERE overall_score IS NULL
                GROUP BY job_id
            ) unscored ON unscored.job_id = jr.job_id
            LEFT JOIN (
                SELECT jr2.job_id, COUNT(rp.candidate_id) AS missing
                FROM jobs_raw jr2
                CROSS JOIN resume_processed rp
                WHERE rp.structured_json IS NOT NULL
                  AND NOT EXISTS (
                      SELECT 1 FROM candidate_job_scores cjs
                      WHERE cjs.job_id = jr2.job_id AND cjs.candidate_id = rp.candidate_id
                  )
                GROUP BY jr2.job_id
            ) never_scored ON never_scored.job_id = jr.job_id
            WHERE jr.jd_processed = true
              AND (COALESCE(unscored.remaining, 0) + COALESCE(never_scored.missing, 0)) > 0
            ORDER BY total_remaining ASC
            LIMIT :limit
        """)
        result = await self.db.execute(query, {"limit": limit})
        return [row[0] for row in result.all()]


    async def run_scoring_cycle(self) -> dict:
        job_ids = await self.find_jobs_needing_scoring(settings.MAX_JOBS_PER_SCORING_CYCLE)

        if not job_ids:
            logger.info("[auto-score] no jobs pending scoring this cycle")
            return {"jobs_processed": 0, "details": []}

        logger.info(f"[auto-score] cycle processing jobs (fewest remaining first): {job_ids}")

        details = []
        for job_id in job_ids:
            try:
                rule_result = await self.rule_service.score_job_against_all_candidates(job_id)
                semantic_result = await self.semantic_service.generate_semantic_scores_for_job(job_id)
                final_result = await self.final_service.finalize_scores_for_job(job_id)

                details.append({
                    "job_id": job_id,
                    "rule": rule_result,
                    "semantic": semantic_result,
                    "final": final_result,
                })
                logger.info(f"[auto-score] job={job_id} scoring cycle complete")

            except Exception as e:
                await self.db.rollback()
                logger.error(f"[auto-score] job={job_id} scoring cycle failed: {e}")
                details.append({"job_id": job_id, "error": str(e)})

        return {"jobs_processed": len(job_ids), "details": details}