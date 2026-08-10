from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger

from app.config import settings
from app.config.logging import logger
from app.database.postgres import PostgresSessionLocal
from app.sync import CandidateSyncService, JobSyncService
from app.services.batch_processing_service import BatchProcessingService
from app.services.auto_scoring_service import AutoScoringService

scheduler = AsyncIOScheduler()

candidate_sync_service = CandidateSyncService()
job_sync_service = JobSyncService()


async def run_scheduled_sync():
    try:
        candidate_count = await candidate_sync_service.run_incremental_sync()
        job_count = await job_sync_service.run_incremental_sync()
        logger.info(
            f"[scheduler] incremental sync complete | "
            f"candidates={candidate_count} jobs={job_count}"
        )
    except Exception as e:
        logger.error(f"[scheduler] incremental sync failed: {e}")


async def run_scheduled_processing():
    try:
        async with PostgresSessionLocal() as db:
            batch_service = BatchProcessingService(db)
            resume_summary = await batch_service.process_all_resumes()
            job_summary = await batch_service.process_all_jobs()
            logger.info(
                f"[scheduler] auto-processing complete | "
                f"resumes={resume_summary} jobs={job_summary}"
            )
    except Exception as e:
        logger.error(f"[scheduler] auto-processing failed: {e}")


async def run_scheduled_scoring():
    try:
        async with PostgresSessionLocal() as db:
            auto_scoring_service = AutoScoringService(db)
            result = await auto_scoring_service.run_scoring_cycle()
            logger.info(f"[scheduler] auto-scoring cycle complete | {result}")
    except Exception as e:
        logger.error(f"[scheduler] auto-scoring failed: {e}")


def start_scheduler():
    scheduler.add_job(
        run_scheduled_sync,
        trigger=IntervalTrigger(minutes=settings.SYNC_INTERVAL_MINUTES),
        id="incremental_sync_job",
        replace_existing=True,
        max_instances=1,
    )

    scheduler.add_job(
        run_scheduled_processing,
        trigger=IntervalTrigger(minutes=settings.AUTO_PROCESSING_INTERVAL_MINUTES),
        id="auto_processing_job",
        replace_existing=True,
        max_instances=1,
    )

    scheduler.add_job(
        run_scheduled_scoring,
        trigger=IntervalTrigger(minutes=settings.AUTO_SCORING_INTERVAL_MINUTES),
        id="auto_scoring_job",
        replace_existing=True,
        max_instances=1,  # critical: semantic scoring is the slowest step, never overlap
    )

    scheduler.start()
    logger.info(
        f"[scheduler] started — sync every {settings.SYNC_INTERVAL_MINUTES} min(s), "
        f"auto-processing every {settings.AUTO_PROCESSING_INTERVAL_MINUTES} min(s), "
        f"auto-scoring every {settings.AUTO_SCORING_INTERVAL_MINUTES} min(s)"
    )


def shutdown_scheduler():
    scheduler.shutdown(wait=False)
    logger.info("[scheduler] stopped")
