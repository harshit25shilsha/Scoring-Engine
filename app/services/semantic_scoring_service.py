import asyncio
import json
from datetime import datetime, timezone
from typing import Optional, Dict, Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.config.logging import logger
from app.database.models import CandidateJobScore, ResumeProcessed, JobProcessed
from app.llm.semantic_matcher import SemanticMatcher

from app.scoring.similarity import blend_fallback_score

class SemanticScoringService:
    def __init__(self, db: AsyncSession, matcher: Optional[SemanticMatcher] = None):
        """Create service.

        Args:
            db: async SQLAlchemy session
            matcher: optional injectable `SemanticMatcher` for easier testing
        """
        self.db = db
        self.matcher = matcher or SemanticMatcher()

    async def _compare(self, candidate_structured: Dict[str, Any], job_structured: Dict[str, Any]) -> Dict[str, Any]:
        """Run matcher.compare in a thread to avoid blocking the event loop."""
        return await asyncio.to_thread(self.matcher.compare, candidate_structured, job_structured) or {}

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

        candidate_ids = [s.candidate_id for s in eligible_for_llm]
        resumes_map = {}
        if candidate_ids:
            res_result = await self.db.execute(
                select(ResumeProcessed).where(ResumeProcessed.candidate_id.in_(candidate_ids))
            )
            fetched_resumes = res_result.scalars().all()
            resumes_map = {r.candidate_id: r for r in fetched_resumes}

        # Claim and process each eligible candidate one-at-a-time using FOR UPDATE SKIP LOCKED
        # This prevents duplicate work across concurrent workers by letting the DB lock the row.
        fallback_scored = 0
        for score_row in eligible_for_llm:
            try:
                # Try to atomically claim this candidate row. If another worker has locked it,
                # skip it (SKIP LOCKED). Use existing transaction if present to avoid nested begins.
                claim_q = (
                    select(CandidateJobScore)
                    .where(
                        CandidateJobScore.id == score_row.id,
                        CandidateJobScore.semantic_score.is_(None),
                    )
                    .with_for_update(skip_locked=True)
                )

                claim_res = await self.db.execute(claim_q)
                claimed = claim_res.scalar_one_or_none()
                if claimed is None:
                    continue

                resume = resumes_map.get(claimed.candidate_id)
                if resume is None or not resume.structured_json:
                    llm_failed += 1
                    logger.warning(
                        f"[semantic-score] missing or empty resume for candidate={claimed.candidate_id} job={job_id}"
                    )
                    await self.db.rollback()
                    continue

                try:
                    candidate_structured = json.loads(resume.structured_json)
                except json.JSONDecodeError:
                    llm_failed += 1
                    logger.exception(
                        f"[semantic-score] invalid resume JSON for candidate={claimed.candidate_id} job={job_id}"
                    )
                    await self.db.rollback()
                    continue

                try:
                    semantic_result = await self._compare(candidate_structured, job_structured)

                    claimed.semantic_score = float(semantic_result.get("semantic_score", 0))
                    claimed.strengths = json.dumps(semantic_result.get("strengths", []))
                    claimed.weaknesses = json.dumps(semantic_result.get("weaknesses", []))
                    claimed.recommendation = semantic_result.get("recommendation")
                    claimed.llm_reviewed = True
                    claimed.score_source = "llm_reviewed"

                    existing_missing = json.loads(claimed.missing_skills or "[]")
                    seen_lower = set()
                    deduped_missing = []
                    for skill in existing_missing:
                        key = skill.strip().lower()
                        if key not in seen_lower:
                            seen_lower.add(key)
                            deduped_missing.append(skill)
                    claimed.missing_skills = json.dumps(deduped_missing)

                    claimed.generated_at = datetime.now(timezone.utc)

                    await self.db.commit()
                    llm_reviewed += 1
                    logger.info(
                        f"[semantic-score] candidate={claimed.candidate_id} job={job_id} "
                        f"LLM-reviewed semantic_score={claimed.semantic_score}"
                    )
                except Exception as e:
                    llm_failed += 1
                    await self.db.rollback()
                    logger.exception(
                        f"[semantic-score] candidate={claimed.candidate_id} job={job_id} failed: {e}"
                    )

            except Exception:
                logger.exception(
                    f"[semantic-score] unexpected error claiming/processing candidate={score_row.candidate_id} job={job_id}"
                )

            await asyncio.sleep(settings.GROQ_BATCH_DELAY_SECONDS)

        # Apply fallback scores for remaining candidates (no LLM review).
        
        for score_row in fallback_candidates:
            try:
                similarity = score_row.embedding_similarity or 0.0
                rule = score_row.rule_score or 0.0
                score_row.semantic_score = blend_fallback_score(score_row.embedding_similarity, score_row.rule_score)
                
                score_row.recommendation = (
                    "Not selected for detailed AI review this cycle (outside top-ranked "
                    "candidates by rule + embedding similarity). Score blends resume-to-job "
                    "semantic similarity with rule-based match, not a full LLM assessment."
                )
                score_row.llm_reviewed = False
                score_row.generated_at = datetime.now(timezone.utc)
                score_row.score_source = "embedding_fallback"
                await self.db.commit()
                fallback_scored += 1
            except Exception:
                await self.db.rollback()
                logger.exception(
                    f"[semantic-score] fallback scoring failed for candidate={score_row.candidate_id} job={job_id}"
                )

        summary = {
            "job_id": job_id,
            "status": "completed",
            "llm_reviewed": llm_reviewed,
            "llm_failed": llm_failed,
            "fallback_scored": fallback_scored,
        }
        logger.info(f"[semantic-score] job={job_id} cycle complete — {summary}")
        return summary