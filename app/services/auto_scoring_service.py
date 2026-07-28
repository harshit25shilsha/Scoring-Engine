from sqlalchemy import select, exists
from sqlalchemy.ext.asyncio import AsyncSession

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
        
        result = await self.db.execute(
            select(JobRaw.job_id).where(JobRaw.jd_processed.is_(True))
        )
        all_ready_job_ids = [row[0] for row in result.all()]

        pending_job_ids = []
        for job_id in all_ready_job_ids:
            has_unscored = await self.db.execute(
                select(
                    exists().where(
                        ResumeProcessed.structured_json.is_not(None),
                        ~exists().where(
                            CandidateJobScore.candidate_id == ResumeProcessed.candidate_id,
                            CandidateJobScore.job_id == job_id,
                            CandidateJobScore.overall_score.is_not(None),
                        ),
                    )
                )
            )
            if has_unscored.scalar():
                pending_job_ids.append(job_id)
            if len(pending_job_ids) >= limit:
                break

        return pending_job_ids

    async def run_scoring_cycle(self) -> dict:
        job_ids = await self.find_jobs_needing_scoring(settings.MAX_JOBS_PER_SCORING_CYCLE)

        if not job_ids:
            logger.info("[auto-score] no jobs pending scoring this cycle")
            return {"jobs_processed": 0, "details": []}

        logger.info(f"[auto-score] cycle processing jobs: {job_ids}")

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
    
