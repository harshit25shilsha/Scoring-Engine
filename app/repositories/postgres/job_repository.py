from datetime import datetime, timezone
from typing import Sequence

from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models import JobRaw
from app.utils.coercion import to_bool


class JobRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def upsert_many(self, jobs: Sequence[dict]) -> int:
        if not jobs:
            return 0

        now = datetime.now(timezone.utc)
        rows = [
            {
                "job_id": j["job_id"],
                "job_title": j.get("job_title"),
                "company_name": j.get("company_name"),
                "job_description": j.get("job_description"),
                "minimum_experience": j.get("minimum_experience"),
                "maximum_experience": j.get("maximum_experience"),
                "minimum_qualification": j.get("minimum_qualification"),
                "preffered_qualification": j.get("preffered_qualification"),
                "employment_type": j.get("employment_type"),
                "work_type": j.get("work_type"),
                "job_location": j.get("job_location"),
                "city": j.get("city"),
                "state": j.get("state"),
                "country": j.get("country"),
                "notice_period": j.get("notice_period"),
                "job_status": to_bool(j.get("job_status")),
                "jobs_posted_status": j.get("jobs_posted_status"),
                "vendor_id": j.get("vendor_id"),
                "sync_status": "SYNCED",
                "last_synced_at": now,
            }
            for j in jobs
        ]

        stmt = insert(JobRaw).values(rows)
        update_cols = {
            col: getattr(stmt.excluded, col)
            for col in rows[0].keys()
            if col != "job_id"
        }
        stmt = stmt.on_conflict_do_update(
            index_elements=["job_id"],
            set_=update_cols,
        )
        await self.db.execute(stmt)
        await self.db.commit()
        return len(rows)