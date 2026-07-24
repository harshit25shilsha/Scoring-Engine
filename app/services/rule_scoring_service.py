import json
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.config.logging import logger
from app.database.models import (
    CandidateRaw, JobRaw, ResumeProcessed, JobProcessed, CandidateJobScore,
)
from app.scoring.rule_engine import (
    score_skills, score_experience, score_education, score_location,
)


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

        scored, skipped = 0, 0

        for resume in resumes:
            candidate_raw = await self.db.get(CandidateRaw, resume.candidate_id)
            if candidate_raw is None:
                skipped += 1
                continue

            try:
                await self._score_pair(candidate_raw, resume, job_raw, job_structured)
                scored += 1
            except Exception as e:
                logger.error(
                    f"[rule-score] candidate={resume.candidate_id} job={job_id} failed: {e}"
                )
                skipped += 1

        logger.info(f"[rule-score] job={job_id} scored={scored} skipped={skipped}")
        return {"job_id": job_id, "status": "completed", "scored": scored, "skipped": skipped}

    async def _score_pair(self, candidate_raw, resume, job_raw, job_structured):
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
            matched_skills=skills_result["matched"],
            missing_skills=skills_result["missing"],
        )

    async def _upsert_score(
        self, candidate_id, job_id, rule_score, skills_score,
        experience_score, education_score, location_score,
        matched_skills, missing_skills,
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
                matched_skills=json.dumps(matched_skills),
                missing_skills=json.dumps(missing_skills),
                generated_at=now,
            ))
        await self.db.commit()