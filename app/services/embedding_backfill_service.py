from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config.logging import logger
from app.database.models import ResumeProcessed, JobProcessed
from app.embeddings.embedding_service import EmbeddingService

CHUNK_SIZE = 32  # matches the model's batch_size for efficient GPU/CPU utilization


class EmbeddingBackfillService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.embedder = EmbeddingService()

    async def backfill_resume_embeddings(self) -> dict:
        result = await self.db.execute(
            select(ResumeProcessed).where(
                ResumeProcessed.structured_json.is_not(None),
                ResumeProcessed.embedding.is_(None),
            )
        )
        rows = result.scalars().all()

        if not rows:
            return {"total_pending": 0, "embedded": 0}

        logger.info(f"[embedding-backfill] resumes pending: {len(rows)}")

        embedded = 0
        for i in range(0, len(rows), CHUNK_SIZE):
            chunk = rows[i : i + CHUNK_SIZE]
            texts = [row.cleaned_text or "" for row in chunk]

            try:
                vectors = self.embedder.generate_batch(texts)
                for row, vector in zip(chunk, vectors):
                    row.embedding = vector
                await self.db.commit()
                embedded += len(chunk)
                logger.info(
                    f"[embedding-backfill] resumes {min(i + CHUNK_SIZE, len(rows))}/{len(rows)} embedded"
                )
            except Exception as e:
                await self.db.rollback()
                logger.error(f"[embedding-backfill] resume chunk failed at offset {i}: {e}")

        return {"total_pending": len(rows), "embedded": embedded}

    async def backfill_job_embeddings(self) -> dict:
        result = await self.db.execute(
            select(JobProcessed).where(
                JobProcessed.structured_json.is_not(None),
                JobProcessed.embedding.is_(None),
            )
        )
        rows = result.scalars().all()

        if not rows:
            return {"total_pending": 0, "embedded": 0}

        logger.info(f"[embedding-backfill] jobs pending: {len(rows)}")

        embedded = 0
        for i in range(0, len(rows), CHUNK_SIZE):
            chunk = rows[i : i + CHUNK_SIZE]
            texts = [row.cleaned_jd or "" for row in chunk]

            try:
                vectors = self.embedder.generate_batch(texts)
                for row, vector in zip(chunk, vectors):
                    row.embedding = vector
                await self.db.commit()
                embedded += len(chunk)
                logger.info(
                    f"[embedding-backfill] jobs {min(i + CHUNK_SIZE, len(rows))}/{len(rows)} embedded"
                )
            except Exception as e:
                await self.db.rollback()
                logger.error(f"[embedding-backfill] job chunk failed at offset {i}: {e}")

        return {"total_pending": len(rows), "embedded": embedded}