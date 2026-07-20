from datetime import datetime
from typing import Sequence

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

CANDIDATE_COLUMNS = [
    "candidate_id", "first_name", "last_name", "email",
    "current_designation", "currently_working_company_name",
    "key_experience", "key_experience_in_month", "overview",
    "resume_file_name", "resume_file_url", "city", "state", "country",
    "active_status", "is_rejected", "candidate_type", "vendor_id",
    "created_at", "updated_at",
]


class CandidateRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_all_active(self) -> Sequence[dict]:
        query = text(f"""
            SELECT {", ".join(CANDIDATE_COLUMNS)}
            FROM candidate
            WHERE active_status = 1
              AND (is_rejected = 0 OR is_rejected IS NULL)
        """)
        result = await self.db.execute(query)
        return [dict(row._mapping) for row in result]

    async def get_updated_since(self, since: datetime) -> Sequence[dict]:
        query = text(f"""
            SELECT {", ".join(CANDIDATE_COLUMNS)}
            FROM candidate
            WHERE active_status = 1
              AND (is_rejected = 0 OR is_rejected IS NULL)
              AND updated_at > :since
        """)
        result = await self.db.execute(query, {"since": since})
        return [dict(row._mapping) for row in result]