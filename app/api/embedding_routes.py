from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.session import get_postgres_session
from app.services.embedding_backfill_service import EmbeddingBackfillService

router = APIRouter(prefix="/embeddings", tags=["embeddings"])


@router.post("/backfill/resumes")
async def backfill_resume_embeddings(
    db: AsyncSession = Depends(get_postgres_session),
):
    service = EmbeddingBackfillService(db)
    return await service.backfill_resume_embeddings()


@router.post("/backfill/jobs")
async def backfill_job_embeddings(
    db: AsyncSession = Depends(get_postgres_session),
):
    service = EmbeddingBackfillService(db)
    return await service.backfill_job_embeddings()