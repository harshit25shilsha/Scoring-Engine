from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.session import get_postgres_session
from app.services.batch_processing_service import BatchProcessingService
from app.services.job_processing_service import JobProcessingService

router = APIRouter(prefix="/process-job", tags=["job-processing"])


@router.post("/batch")
async def process_job_batch(
    db: AsyncSession = Depends(get_postgres_session),
):
    service = BatchProcessingService(db)
    return await service.process_all_jobs()


@router.post("/{job_id}")
async def process_job(
    job_id: int,
    db: AsyncSession = Depends(get_postgres_session),
):
    service = JobProcessingService(db)
    return await service.process_job(job_id)