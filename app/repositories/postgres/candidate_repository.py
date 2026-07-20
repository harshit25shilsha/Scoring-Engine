from datetime import datetime, timezone
from typing import Sequence

from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models import CandidateRaw
from app.utils.coercion import to_bool, to_int


class CandidateRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def upsert_many(self, candidates: Sequence[dict]) -> int:
        if not candidates:
            return 0

        now = datetime.now(timezone.utc)
        rows = [
            {
                "candidate_id": c["candidate_id"],
                "first_name": c.get("first_name"),
                "last_name": c.get("last_name"),
                "email": c.get("email"),
                "current_designation": c.get("current_designation"),
                "currently_working_company_name": c.get("currently_working_company_name"),
                "key_experience": c.get("key_experience"),
                "key_experience_in_month": to_int(c.get("key_experience_in_month")),
                "overview": c.get("overview"),
                "resume_file_name": c.get("resume_file_name"),
                "resume_file_url": c.get("resume_file_url"),
                "city": c.get("city"),
                "state": c.get("state"),
                "country": c.get("country"),
                "active_status": to_bool(c.get("active_status")),
                "is_rejected": to_bool(c.get("is_rejected")),
                "candidate_type": c.get("candidate_type"),
                "vendor_id": c.get("vendor_id"),
                "sync_status": "SYNCED",
                "last_synced_at": now,
            }
            for c in candidates
        ]

        stmt = insert(CandidateRaw).values(rows)
        update_cols = {
            col: getattr(stmt.excluded, col)
            for col in rows[0].keys()
            if col != "candidate_id"
        }
        stmt = stmt.on_conflict_do_update(
            index_elements=["candidate_id"],
            set_=update_cols,
        )
        await self.db.execute(stmt)
        await self.db.commit()
        return len(rows)