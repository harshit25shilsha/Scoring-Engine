import asyncio
import json
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.config.logging import logger
from app.database.models import CandidateJobScore, ResumeProcessed, JobProcessed
from app.llm.semantic_matcher import SemanticMatcher


class SemanticScoringService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.matcher = SemanticMatcher()

    async def generate_semantic_scores_for_job(self, job_id: int) -> dict:

        job_processed = await self.db.get(JobProcessed, job_id)
        if job_processed is None or not job_processed.structured_json:
            return {"job_id": job_id, "status": "job_not_ready"}

        job_structured = json.loads(job_processed.structured_json)

        result = await self.db.execute(
            select(CandidateJobScore).where(
                CandidateJobScore.job_id == job_id,
                CandidateJobScore.rule_score.is_not(None),
                CandidateJobScore.semantic_score.is_(None),
            )
        )
        pending_scores = result.scalars().all()

        logger.info(f"[semantic-score] job={job_id} pending={len(pending_scores)}")

        succeeded, failed = 0, 0

        for score_row in pending_scores:
            resume = await self.db.get(ResumeProcessed, score_row.candidate_id)
            if resume is None or not resume.structured_json:
                failed += 1
                continue

            try:
                candidate_structured = json.loads(resume.structured_json)
                semantic_result = self.matcher.compare(candidate_structured, job_structured)

                score_row.semantic_score = float(semantic_result.get("semantic_score", 0))
                score_row.strengths = json.dumps(semantic_result.get("strengths", []))
                score_row.weaknesses = json.dumps(semantic_result.get("weaknesses", []))
                score_row.recommendation = semantic_result.get("recommendation")

                # merge LLM-identified missing skills with rule-based missing skills
                existing_missing = json.loads(score_row.missing_skills or "[]")
                llm_missing = semantic_result.get("missing_skills", [])

                seen_lower = set()
                merged_missing = []
                for skill in existing_missing + llm_missing:
                    key = skill.strip().lower()
                    if key not in seen_lower:
                        seen_lower.add(key)
                        merged_missing.append(skill)

                score_row.missing_skills = json.dumps(merged_missing)

                score_row.generated_at = datetime.now(timezone.utc)
                await self.db.commit()

                succeeded += 1
                logger.info(
                    f"[semantic-score] candidate={score_row.candidate_id} job={job_id} "
                    f"semantic_score={score_row.semantic_score}"
                )

            except Exception as e:
                failed += 1
                logger.error(
                    f"[semantic-score] candidate={score_row.candidate_id} job={job_id} failed: {e}"
                )

            await asyncio.sleep(settings.GROQ_BATCH_DELAY_SECONDS)

        summary = {
            "job_id": job_id,
            "status": "completed",
            "total_pending": len(pending_scores),
            "succeeded": succeeded,
            "failed": failed,
        }
        logger.info(f"[semantic-score] job={job_id} complete — {summary}")
        return summary