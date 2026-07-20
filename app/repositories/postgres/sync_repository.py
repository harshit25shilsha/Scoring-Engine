from datetime import datetime

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models import SyncMetadata


class SyncRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_last_sync_time(self, entity_name: str) -> datetime | None:
        result = await self.db.execute(
            select(SyncMetadata.last_sync_time).where(
                SyncMetadata.entity_name == entity_name
            )
        )
        return result.scalar_one_or_none()

    async def update_last_sync_time(self, entity_name: str, sync_time: datetime) -> None:
        stmt = insert(SyncMetadata).values(
            entity_name=entity_name, last_sync_time=sync_time
        )
        stmt = stmt.on_conflict_do_update(
            index_elements=["entity_name"],
            set_={"last_sync_time": stmt.excluded.last_sync_time},
        )
        await self.db.execute(stmt)
        await self.db.commit()