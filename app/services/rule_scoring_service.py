import json
from datetime import datetime, timezone

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.config.logging import logger
from app.database.models import (
    CandidateRaw, JobRaw, ResumeProcessed, JobProcessed, CandidateJobScore,
)
from app.scoring.rule_engine import (
    score_skills, score_experience, score_education, score_location,
)
from app.scoring.similarity import similarity_to_percentage


class RuleScoringService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def score_job_against_all_candidates(self, job_id: int) -> dict:
        job_raw = await self.db.get(JobRaw, job_id)
        job_processed = await self.db.get(JobProcessed, job_id)

        if job_raw is None or job_processed is None or not job_processed.structured_json:
            return {"job_id": job_id, "status": "job_not_ready"}

        job_structured = json.loads(job_processed.structured_json)

        result = await self.db.execute(
            select(ResumeProcessed).where(ResumeProcessed.structured_json.is_not(None))
        )
        resumes = result.scalars().all()

        candidate_ids = [r.candidate_id for r in resumes]
        candidates_result = await self.db.execute(
            select(CandidateRaw).where(CandidateRaw.candidate_id.in_(candidate_ids))
        )
        candidates_by_id = {c.candidate_id: c for c in candidates_result.scalars().all()}

        # Bulk, Postgres-native similarity for ALL candidates in one query,
        # instead of one Python cosine_similarity() call per candidate.
        similarities_by_candidate = await self._fetch_bulk_similarities(job_processed.embedding)

        scored, skipped = 0, 0

        for resume in resumes:
            candidate_id_for_log = resume.candidate_id
            candidate_raw = candidates_by_id.get(resume.candidate_id)

            if candidate_raw is None:
                skipped += 1
                continue

            try:
                raw_similarity = similarities_by_candidate.get(resume.candidate_id)
                embedding_sim_pct = (
                    similarity_to_percentage(raw_similarity) if raw_similarity is not None else None
                )

                await self._score_pair(
                    candidate_raw, resume, job_raw, job_structured, embedding_sim_pct
                )
                scored += 1
            except Exception as e:
                await self.db.rollback()
                logger.error(
                    f"[rule-score] candidate={candidate_id_for_log} job={job_id} failed: {e}"
                )
                skipped += 1

        logger.info(f"[rule-score] job={job_id} scored={scored} skipped={skipped}")
        return {"job_id": job_id, "status": "completed", "scored": scored, "skipped": skipped}

    async def _fetch_bulk_similarities(self, job_embedding) -> dict[int, float]:
        """
        Single Postgres-native query computing cosine similarity between the job's
        embedding and EVERY candidate's embedding at once, using pgvector's <=> operator.
        Returns {candidate_id: similarity} for all structured, embedded candidates.
        """
        if job_embedding is None:
            return {}

        # pgvector over asyncpg expects the vector as a literal string like '[0.1,0.2,...]'
        job_embedding_str = "[" + ",".join(str(float(x)) for x in job_embedding) + "]"

        query = text("""
            SELECT candidate_id, 1 - (embedding <=> CAST(:job_embedding AS vector)) AS similarity
            FROM resume_processed
            WHERE structured_json IS NOT NULL AND embedding IS NOT NULL
        """)
        result = await self.db.execute(query, {"job_embedding": job_embedding_str})
        return {row[0]: row[1] for row in result.all()}

    async def _score_pair(self, candidate_raw, resume, job_raw, job_structured, embedding_sim_pct):
        candidate_structured = json.loads(resume.structured_json)

        skills_result = score_skills(
            candidate_skills=candidate_structured.get("skills", []),
            required_skills=job_structured.get("required_skills", []),
        )

        exp_score = score_experience(
            candidate_years=candidate_structured.get("total_experience_years"),
            min_years=job_structured.get("minimum_experience_years"),
            max_years=job_structured.get("maximum_experience_years"),
        )

        edu_score = score_education(
            candidate_education=candidate_structured.get("education", []),
            required_education=job_structured.get("education_requirements", []),
        )

        loc_score = score_location(
            candidate_city=candidate_raw.city,
            candidate_state=candidate_raw.state,
            candidate_country=candidate_raw.country,
            job_city=job_raw.city,
            job_state=job_raw.state,
            job_country=job_raw.country,
            job_location_text=job_raw.job_location,
            work_type=job_raw.work_type,
        )

        rule_score = (
            skills_result["score"] * settings.SKILLS_WEIGHT
            + exp_score * settings.EXPERIENCE_WEIGHT
            + edu_score * settings.EDUCATION_WEIGHT
            + loc_score * settings.LOCATION_WEIGHT
        )

        await self._upsert_score(
            candidate_id=candidate_raw.candidate_id,
            job_id=job_raw.job_id,
            rule_score=round(rule_score, 2),
            skills_score=skills_result["score"],
            experience_score=exp_score,
            education_score=edu_score,
            location_score=loc_score,
            embedding_similarity=embedding_sim_pct,
            matched_skills=skills_result["matched"],
            missing_skills=skills_result["missing"],
        )

    async def _upsert_score(
        self, candidate_id, job_id, rule_score, skills_score,
        experience_score, education_score, location_score,
        embedding_similarity, matched_skills, missing_skills,
    ):
        result = await self.db.execute(
            select(CandidateJobScore).where(
                CandidateJobScore.candidate_id == candidate_id,
                CandidateJobScore.job_id == job_id,
            )
        )
        existing = result.scalar_one_or_none()
        now = datetime.now(timezone.utc)

        if existing:
            existing.rule_score = rule_score
            existing.skills_score = skills_score
            existing.experience_score = experience_score
            existing.education_score = education_score
            existing.location_score = location_score
            existing.embedding_similarity = embedding_similarity
            existing.matched_skills = json.dumps(matched_skills)
            existing.missing_skills = json.dumps(missing_skills)
            existing.generated_at = now
        else:
            self.db.add(CandidateJobScore(
                candidate_id=candidate_id,
                job_id=job_id,
                rule_score=rule_score,
                skills_score=skills_score,
                experience_score=experience_score,
                education_score=education_score,
                location_score=location_score,
                embedding_similarity=embedding_similarity,
                matched_skills=json.dumps(matched_skills),
                missing_skills=json.dumps(missing_skills),
                generated_at=now,
            ))
        await self.db.commit()