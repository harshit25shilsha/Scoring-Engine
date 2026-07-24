from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.session import get_postgres_session
from app.services.batch_processing_service import BatchProcessingService
from app.services.resume_processing_service import ResumeProcessingService

router = APIRouter(prefix="/process-resume", tags=["resume-processing"])


@router.post("/batch")
async def process_resume_batch(
    db: AsyncSession = Depends(get_postgres_session),
):
    service = BatchProcessingService(db)
    return await service.process_all_resumes()


@router.post("/{candidate_id}")
async def process_resume(
    candidate_id: int,
    db: AsyncSession = Depends(get_postgres_session),
):
    service = ResumeProcessingService(db)
    return await service.process_candidate(candidate_id)