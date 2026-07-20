from datetime import datetime
from typing import Sequence

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

JOB_COLUMNS = [
    "job_id", "job_title", "company_name", "job_description",
    "minimum_experience", "maximum_experience", "minimum_qualification",
    "preffered_qualification", "employment_type", "work_type",
    "job_location", "city", "state", "country", "notice_period",
    "job_status", "jobs_posted_status", "vendor_id",
    "created_at", "updated_at",
]


class JobRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_all_active(self) -> Sequence[dict]:
        query = text(f"""
            SELECT {", ".join(JOB_COLUMNS)}
            FROM jobs
            WHERE job_status = 1
        """)
        result = await self.db.execute(query)
        return [dict(row._mapping) for row in result]

    async def get_updated_since(self, since: datetime) -> Sequence[dict]:
        query = text(f"""
            SELECT {", ".join(JOB_COLUMNS)}
            FROM jobs
            WHERE job_status = 1
              AND updated_at > :since
        """)
        result = await self.db.execute(query, {"since": since})
        return [dict(row._mapping) for row in result]