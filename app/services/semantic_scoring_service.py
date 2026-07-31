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

        if not pending_scores:
            return {"job_id": job_id, "status": "completed", "llm_reviewed": 0, "fallback_scored": 0}

        # Rank by combined signal: rule_score + embedding_similarity (equal weight)
        # so strong candidates the rule engine underrates can still surface via embeddings.
        def ranking_key(score_row):
            rule = score_row.rule_score or 0
            sim = score_row.embedding_similarity or 0
            return (rule + sim) / 2

        ranked = sorted(pending_scores, key=ranking_key, reverse=True)

        eligible_for_llm = [
            s for s in ranked
            if (s.rule_score or 0) >= settings.SEMANTIC_REVIEW_MIN_RULE_SCORE
        ][: settings.SEMANTIC_REVIEW_TOP_N_PER_JOB]

        eligible_ids = {s.id for s in eligible_for_llm}
        fallback_candidates = [s for s in ranked if s.id not in eligible_ids]

        logger.info(
            f"[semantic-score] job={job_id} total_pending={len(pending_scores)} "
            f"llm_review={len(eligible_for_llm)} fallback={len(fallback_candidates)}"
        )

        llm_reviewed, llm_failed = 0, 0

        for score_row in eligible_for_llm:
            resume = await self.db.get(ResumeProcessed, score_row.candidate_id)
            if resume is None or not resume.structured_json:
                llm_failed += 1
                continue

            try:
                candidate_structured = json.loads(resume.structured_json)
                semantic_result = self.matcher.compare(candidate_structured, job_structured)

                score_row.semantic_score = float(semantic_result.get("semantic_score", 0))
                score_row.strengths = json.dumps(semantic_result.get("strengths", []))
                score_row.weaknesses = json.dumps(semantic_result.get("weaknesses", []))
                score_row.recommendation = semantic_result.get("recommendation")
                score_row.llm_reviewed = True

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

                llm_reviewed += 1
                logger.info(
                    f"[semantic-score] candidate={score_row.candidate_id} job={job_id} "
                    f"LLM-reviewed semantic_score={score_row.semantic_score}"
                )

            except Exception as e:
                await self.db.rollback()
                llm_failed += 1
                logger.error(
                    f"[semantic-score] candidate={score_row.candidate_id} job={job_id} failed: {e}"
                )

            await asyncio.sleep(settings.GROQ_BATCH_DELAY_SECONDS)

        # Fallback: honest, embedding-derived score for candidates outside the review shortlist —
        # not a fake number, and clearly labeled as not LLM-reviewed.
        fallback_scored = 0
        for score_row in fallback_candidates:
            score_row.semantic_score = score_row.embedding_similarity or 0.0
            score_row.recommendation = (
                "Not selected for detailed AI review this cycle (outside top-ranked "
                "candidates by rule + embedding similarity). Score reflects resume-to-job "
                "semantic similarity only, not a full LLM assessment."
            )
            score_row.llm_reviewed = False
            score_row.generated_at = datetime.now(timezone.utc)
            fallback_scored += 1

        await self.db.commit()

        summary = {
            "job_id": job_id,
            "status": "completed",
            "llm_reviewed": llm_reviewed,
            "llm_failed": llm_failed,
            "fallback_scored": fallback_scored,
        }
        logger.info(f"[semantic-score] job={job_id} cycle complete — {summary}")
        return summary