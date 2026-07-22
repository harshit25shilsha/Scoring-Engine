import json
from datetime import datetime, timezone

from sqlalchemy import update
from sqlalchemy.ext.asyncio import AsyncSession

from app.config.logging import logger
from app.database.models import JobRaw, JobProcessed
from app.llm.jd_extractor import JDExtractor
from app.parsers.text_cleaner import clean_text
from app.utils.hashing import hash_text


class JobProcessingService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.extractor = JDExtractor()

    async def process_job(self, job_id: int) -> dict:
        job = await self.db.get(JobRaw, job_id)

        if job is None:
            return {"job_id": job_id, "status": "not_found"}

        if not job.job_description:
            return {"job_id": job_id, "status": "no_description"}

        content_hash = hash_text(job.job_description)

        existing = await self.db.get(JobProcessed, job_id)
        if existing and existing.jd_hash == content_hash:
            logger.info(f"[job] job={job_id} unchanged, skipping")
            return {"job_id": job_id, "status": "unchanged"}

        cleaned = clean_text(job.job_description)

        structured = None
        structured_error = None
        try:
            structured = self.extractor.extract(cleaned)
        except Exception as e:
            structured_error = str(e)
            logger.error(f"[groq] JD structuring failed for job={job_id}: {e}")

        await self._store_result(
            job_id=job_id,
            cleaned_jd=cleaned,
            structured_json=json.dumps(structured) if structured else None,
            jd_hash=content_hash,
            parse_status="STRUCTURED" if structured else "PARSED_ONLY",
            parse_error=structured_error,
        )

        if structured:
            await self._mark_job_processed(job_id, True)

        logger.info(f"[job] job={job_id} processed, structured={bool(structured)}")
        return {
            "job_id": job_id,
            "status": "structured" if structured else "parsed_only",
            "text_length": len(cleaned),
        }

    async def _store_result(self, job_id, cleaned_jd, structured_json, jd_hash, parse_status, parse_error):
        existing = await self.db.get(JobProcessed, job_id)
        now = datetime.now(timezone.utc)

        if existing:
            existing.cleaned_jd = cleaned_jd
            existing.structured_json = structured_json
            existing.jd_hash = jd_hash
            existing.parse_status = parse_status
            existing.parse_error = parse_error
            existing.processed_at = now
        else:
            self.db.add(JobProcessed(
                job_id=job_id,
                cleaned_jd=cleaned_jd,
                structured_json=structured_json,
                jd_hash=jd_hash,
                parse_status=parse_status,
                parse_error=parse_error,
                processed_at=now,
            ))
        await self.db.commit()

    async def _mark_job_processed(self, job_id: int, value: bool):
        await self.db.execute(
            update(JobRaw)
            .where(JobRaw.job_id == job_id)
            .values(jd_processed=value)
        )
        await self.db.commit()