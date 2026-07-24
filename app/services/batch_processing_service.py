import asyncio

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.config.logging import logger
from app.database.models import CandidateRaw, JobRaw
from app.services.resume_processing_service import ResumeProcessingService
from app.services.job_processing_service import JobProcessingService


class BatchProcessingService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.resume_service = ResumeProcessingService(db)
        self.job_service = JobProcessingService(db)

    async def process_all_resumes(self) -> dict:
        result = await self.db.execute(
            select(CandidateRaw.candidate_id).where(
                CandidateRaw.resume_processed.is_(False),
                CandidateRaw.resume_file_url.is_not(None),
            )
        )
        candidate_ids = [row[0] for row in result.all()]

        logger.info(f"[batch] resume backfill starting — {len(candidate_ids)} pending")

        succeeded, failed, skipped = [], [], []

        for idx, candidate_id in enumerate(candidate_ids, start=1):
            try:
                outcome = await self.resume_service.process_candidate(candidate_id)
                status = outcome.get("status")

                if status in ("structured", "parsed_only"):
                    succeeded.append(candidate_id)
                elif status in ("unchanged", "no_resume"):
                    skipped.append(candidate_id)
                else:
                    failed.append({"candidate_id": candidate_id, "reason": status})

                logger.info(
                    f"[batch] resume {idx}/{len(candidate_ids)} "
                    f"candidate={candidate_id} status={status}"
                )

            except Exception as e:
                failed.append({"candidate_id": candidate_id, "reason": str(e)})
                logger.error(f"[batch] resume candidate={candidate_id} crashed: {e}")

            await asyncio.sleep(settings.GROQ_BATCH_DELAY_SECONDS)

        summary = {
            "total_pending": len(candidate_ids),
            "succeeded": len(succeeded),
            "skipped": len(skipped),
            "failed": len(failed),
            "failed_details": failed,
        }
        logger.info(f"[batch] resume backfill complete — {summary}")
        return summary

    async def process_all_jobs(self) -> dict:
        result = await self.db.execute(
            select(JobRaw.job_id).where(
                JobRaw.jd_processed.is_(False),
                JobRaw.job_description.is_not(None),
            )
        )
        job_ids = [row[0] for row in result.all()]

        logger.info(f"[batch] job backfill starting — {len(job_ids)} pending")

        succeeded, failed, skipped = [], [], []

        for idx, job_id in enumerate(job_ids, start=1):
            try:
                outcome = await self.job_service.process_job(job_id)
                status = outcome.get("status")

                if status in ("structured", "parsed_only"):
                    succeeded.append(job_id)
                elif status in ("unchanged", "no_description"):
                    skipped.append(job_id)
                else:
                    failed.append({"job_id": job_id, "reason": status})

                logger.info(f"[batch] job {idx}/{len(job_ids)} job={job_id} status={status}")

            except Exception as e:
                failed.append({"job_id": job_id, "reason": str(e)})
                logger.error(f"[batch] job={job_id} crashed: {e}")

            await asyncio.sleep(settings.GROQ_BATCH_DELAY_SECONDS)

        summary = {
            "total_pending": len(job_ids),
            "succeeded": len(succeeded),
            "skipped": len(skipped),
            "failed": len(failed),
            "failed_details": failed,
        }
        logger.info(f"[batch] job backfill complete — {summary}")
        return summary