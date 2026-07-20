from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger

from app.config import settings
from app.config.logging import logger
from app.sync import CandidateSyncService, JobSyncService

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


def start_scheduler():
    scheduler.add_job(
        run_scheduled_sync,
        trigger=IntervalTrigger(minutes=settings.SYNC_INTERVAL_MINUTES),
        id="incremental_sync_job",
        replace_existing=True,
        max_instances=1,  # prevents overlap if a sync run takes longer than 2 minutes
    )
    scheduler.start()
    logger.info(
        f"[scheduler] started — incremental sync every "
        f"{settings.SYNC_INTERVAL_MINUTES} minute(s)"
    )


def shutdown_scheduler():
    scheduler.shutdown(wait=False)
    logger.info("[scheduler] stopped")