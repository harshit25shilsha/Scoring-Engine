import json
from datetime import datetime, timezone

from sqlalchemy import update
from sqlalchemy.ext.asyncio import AsyncSession

from app.config.logging import logger
from app.database.models import CandidateRaw, ResumeProcessed
from app.llm.resume_extractor import ResumeExtractor
from app.parsers.resume_parser import extract_text, UnsupportedResumeFormat
from app.parsers.text_cleaner import clean_text
from app.services.s3_service import S3Service
from app.utils.hashing import hash_content


class ResumeProcessingService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.s3 = S3Service()
        self.extractor = ResumeExtractor()

    async def process_candidate(self, candidate_id: int) -> dict:
        candidate = await self.db.get(CandidateRaw, candidate_id)

        if candidate is None:
            return {"candidate_id": candidate_id, "status": "not_found"}

        if not candidate.resume_file_url or not candidate.resume_file_name:
            return {"candidate_id": candidate_id, "status": "no_resume"}

        try:
            file_bytes = self.s3.download_file(candidate.resume_file_url)
            content_hash = hash_content(file_bytes)

            existing = await self.db.get(ResumeProcessed, candidate_id)
            if existing and existing.resume_hash == content_hash:
                logger.info(f"[resume] candidate={candidate_id} unchanged, skipping")
                return {"candidate_id": candidate_id, "status": "unchanged"}

            raw_text = extract_text(file_bytes, candidate.resume_file_name)
            cleaned = clean_text(raw_text)

            structured = None
            structured_error = None
            try:
                structured = self.extractor.extract(cleaned)
            except Exception as e:
                structured_error = str(e)
                logger.error(f"[groq] structuring failed for candidate={candidate_id}: {e}")

            await self._store_result(
                candidate_id=candidate_id,
                resume_text=raw_text,
                cleaned_text=cleaned,
                structured_json=json.dumps(structured) if structured else None,
                resume_hash=content_hash,
                parse_status="STRUCTURED" if structured else "PARSED_ONLY",
                parse_error=structured_error,
            )
            await self._mark_candidate_processed(candidate_id, True)

            logger.info(f"[resume] candidate={candidate_id} processed, structured={bool(structured)}")
            return {
                "candidate_id": candidate_id,
                "status": "structured" if structured else "parsed_only",
                "text_length": len(cleaned),
            }

        except UnsupportedResumeFormat as e:
            await self._store_result(
                candidate_id=candidate_id,
                resume_text=None,
                cleaned_text=None,
                structured_json=None,
                resume_hash=None,
                parse_status="UNSUPPORTED_FORMAT",
                parse_error=str(e),
            )
            logger.warning(f"[resume] candidate={candidate_id} unsupported format: {e}")
            return {"candidate_id": candidate_id, "status": "unsupported_format"}

        except Exception as e:
            await self._store_result(
                candidate_id=candidate_id,
                resume_text=None,
                cleaned_text=None,
                structured_json=None,
                resume_hash=None,
                parse_status="FAILED",
                parse_error=str(e),
            )
            logger.error(f"[resume] candidate={candidate_id} failed: {e}")
            return {"candidate_id": candidate_id, "status": "failed", "error": str(e)}

    async def _store_result(
        self, candidate_id, resume_text, cleaned_text, structured_json,
        resume_hash, parse_status, parse_error
    ):
        existing = await self.db.get(ResumeProcessed, candidate_id)
        now = datetime.now(timezone.utc)

        if existing:
            existing.resume_text = resume_text
            existing.cleaned_text = cleaned_text
            existing.structured_json = structured_json
            existing.resume_hash = resume_hash
            existing.parse_status = parse_status
            existing.parse_error = parse_error
            existing.processed_at = now
        else:
            self.db.add(ResumeProcessed(
                candidate_id=candidate_id,
                resume_text=resume_text,
                cleaned_text=cleaned_text,
                structured_json=structured_json,
                resume_hash=resume_hash,
                parse_status=parse_status,
                parse_error=parse_error,
                processed_at=now,
            ))
        await self.db.commit()

    async def _mark_candidate_processed(self, candidate_id: int, value: bool):
        await self.db.execute(
            update(CandidateRaw)
            .where(CandidateRaw.candidate_id == candidate_id)
            .values(resume_processed=value)
        )
        await self.db.commit()