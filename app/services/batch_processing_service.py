import asyncio

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.config.logging import logger
from app.database.models import CandidateRaw, JobRaw
from app.services.resume_processing_service import ResumeProcessingService
from app.services.job_processing_service import JobProcessingService

FETCH_CONCURRENCY = 5  # concurrent S3 downloads/extractions — I/O-bound, no Groq involved


class BatchProcessingService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.resume_service = ResumeProcessingService(db)
        self.job_service = JobProcessingService(db)

    async def process_all_resumes(self) -> dict:
        # (unchanged — existing simple sequential version, kept as-is for compatibility)
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

                logger.info(f"[batch] resume {idx}/{len(candidate_ids)} candidate={candidate_id} status={status}")

            except Exception as e:
                await self.db.rollback()
                failed.append({"candidate_id": candidate_id, "reason": str(e)})
                logger.error(f"[batch] resume candidate={candidate_id} crashed: {e}")

            await asyncio.sleep(settings.GROQ_BATCH_DELAY_SECONDS)

        summary = {
            "total_pending": len(candidate_ids), "succeeded": len(succeeded),
            "skipped": len(skipped), "failed": len(failed), "failed_details": failed,
        }
        logger.info(f"[batch] resume backfill complete — {summary}")
        return summary

    async def process_all_resumes_parallel_fetch(self) -> dict:
        """
        Two-phase resume backfill:
        Phase 1 — download + extract + clean CONCURRENTLY (I/O-bound, no Groq, safe to parallelize).
        Phase 2 — Groq structuring + embedding, SEQUENTIALLY with rate-limit delay (unchanged pacing).
        This speeds up large backfills without increasing Groq call rate at all.
        """
        result = await self.db.execute(
            select(CandidateRaw).where(
                CandidateRaw.resume_processed.is_(False),
                CandidateRaw.resume_file_url.is_not(None),
            )
        )
        candidates = result.scalars().all()

        if not candidates:
            return {"total_pending": 0, "succeeded": 0, "skipped": 0, "failed": 0, "failed_details": []}

        logger.info(f"[batch-parallel] resume backfill starting — {len(candidates)} pending, fetch_concurrency={FETCH_CONCURRENCY}")

        semaphore = asyncio.Semaphore(FETCH_CONCURRENCY)

        async def fetch_one(candidate):
            async with semaphore:
                try:
                    fetched = await asyncio.to_thread(
                        self.resume_service.fetch_and_clean_sync,
                        candidate.resume_file_url,
                        candidate.resume_file_name,
                    )
                    return {"candidate": candidate, "fetched": fetched, "error": None}
                except Exception as e:
                    return {"candidate": candidate, "fetched": None, "error": str(e)}

        # Phase 1: concurrent fetch/extract/clean — the actual speedup
        fetch_results = await asyncio.gather(*[fetch_one(c) for c in candidates])
        logger.info(f"[batch-parallel] phase 1 (fetch) complete — {len(fetch_results)} attempted")

        # Phase 2: sequential Groq structuring — unchanged rate-limit-safe pacing
        succeeded, failed, skipped = [], [], []

        for idx, item in enumerate(fetch_results, start=1):
            candidate = item["candidate"]
            candidate_id = candidate.candidate_id

            if item["error"]:
                failed.append({"candidate_id": candidate_id, "reason": item["error"]})
                logger.error(f"[batch-parallel] candidate={candidate_id} fetch failed: {item['error']}")
                await asyncio.sleep(settings.GROQ_BATCH_DELAY_SECONDS)
                continue

            try:
                fetched = item["fetched"]
                outcome = await self.resume_service.structure_and_store(
                    candidate_id, fetched["raw_text"], fetched["cleaned_text"], fetched["content_hash"]
                )
                status = outcome.get("status")

                if status in ("structured", "parsed_only"):
                    succeeded.append(candidate_id)
                elif status == "unchanged":
                    skipped.append(candidate_id)
                else:
                    failed.append({"candidate_id": candidate_id, "reason": status})

                logger.info(f"[batch-parallel] structure {idx}/{len(fetch_results)} candidate={candidate_id} status={status}")

            except Exception as e:
                await self.db.rollback()
                failed.append({"candidate_id": candidate_id, "reason": str(e)})
                logger.error(f"[batch-parallel] candidate={candidate_id} structuring crashed: {e}")

            await asyncio.sleep(settings.GROQ_BATCH_DELAY_SECONDS)

        summary = {
            "total_pending": len(candidates), "succeeded": len(succeeded),
            "skipped": len(skipped), "failed": len(failed), "failed_details": failed,
        }
        logger.info(f"[batch-parallel] resume backfill complete — {summary}")
        return summary

    # process_all_jobs() stays unchanged — no S3/download step, so parallelizing it
    # wouldn't help; job processing is already fast since JD text is already in the DB.
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
                await self.db.rollback()
                failed.append({"job_id": job_id, "reason": str(e)})
                logger.error(f"[batch] job={job_id} crashed: {e}")

            await asyncio.sleep(settings.GROQ_BATCH_DELAY_SECONDS)

        summary = {
            "total_pending": len(job_ids), "succeeded": len(succeeded),
            "skipped": len(skipped), "failed": len(failed), "failed_details": failed,
        }
        logger.info(f"[batch] job backfill complete — {summary}")
        return summary