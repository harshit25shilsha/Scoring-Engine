from fastapi import APIRouter

from app.config.logging import logger
from app.schemas.sync import SyncResult
from app.sync import CandidateSyncService, JobSyncService

router = APIRouter(prefix="/sync", tags=["sync"])

candidate_sync_service = CandidateSyncService()
job_sync_service = JobSyncService()


# Initial Migration (one-time, internal/admin)

@router.post("/initial/candidates", response_model=SyncResult)
async def sync_initial_candidates():
    count = await candidate_sync_service.run_initial_migration()
    return SyncResult(entity="candidate", mode="initial", synced_count=count)


@router.post("/initial/jobs", response_model=SyncResult)
async def sync_initial_jobs():
    count = await job_sync_service.run_initial_migration()
    return SyncResult(entity="job", mode="initial", synced_count=count)


@router.post("/initial/all", response_model=list[SyncResult])
async def sync_initial_all():
    candidate_count = await candidate_sync_service.run_initial_migration()
    job_count = await job_sync_service.run_initial_migration()
    return [
        SyncResult(entity="candidate", mode="initial", synced_count=candidate_count),
        SyncResult(entity="job", mode="initial", synced_count=job_count),
    ]


# Incremental Sync (manual trigger; scheduler calls same services)

@router.post("/incremental/candidates", response_model=SyncResult)
async def sync_incremental_candidates():
    count = await candidate_sync_service.run_incremental_sync()
    return SyncResult(entity="candidate", mode="incremental", synced_count=count)


@router.post("/incremental/jobs", response_model=SyncResult)
async def sync_incremental_jobs():
    count = await job_sync_service.run_incremental_sync()
    return SyncResult(entity="job", mode="incremental", synced_count=count)


@router.post("/incremental/all", response_model=list[SyncResult])
async def sync_incremental_all():
    candidate_count = await candidate_sync_service.run_incremental_sync()
    job_count = await job_sync_service.run_incremental_sync()
    return [
        SyncResult(entity="candidate", mode="incremental", synced_count=candidate_count),
        SyncResult(entity="job", mode="incremental", synced_count=job_count),
    ]