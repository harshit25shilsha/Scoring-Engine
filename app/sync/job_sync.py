from datetime import datetime, timezone

from app.config.logging import logger
from app.database.mysql import MySQLSessionLocal
from app.database.postgres import PostgresSessionLocal
from app.repositories.mysql.job_repository import JobRepository as MySQLJobRepo
from app.repositories.postgres.job_repository import JobRepository as PGJobRepo
from app.repositories.postgres.sync_repository import SyncRepository

ENTITY_NAME = "job"
EPOCH = datetime(1970, 1, 1, tzinfo=timezone.utc)


class JobSyncService:

    async def run_initial_migration(self) -> int:
        
        async with MySQLSessionLocal() as mysql_db, PostgresSessionLocal() as pg_db:
            mysql_repo = MySQLJobRepo(mysql_db)
            pg_repo = PGJobRepo(pg_db)
            sync_repo = SyncRepository(pg_db)

            start_time = datetime.now(timezone.utc)
            jobs = await mysql_repo.get_all_active()
            count = await pg_repo.upsert_many(jobs)
            await sync_repo.update_last_sync_time(ENTITY_NAME, start_time)

            logger.info(f"[job initial migration] synced={count}")
            return count

    async def run_incremental_sync(self) -> int:
        
        async with MySQLSessionLocal() as mysql_db, PostgresSessionLocal() as pg_db:
            mysql_repo = MySQLJobRepo(mysql_db)
            pg_repo = PGJobRepo(pg_db)
            sync_repo = SyncRepository(pg_db)

            last_sync = await sync_repo.get_last_sync_time(ENTITY_NAME) or EPOCH
            start_time = datetime.now(timezone.utc)

            jobs = await mysql_repo.get_updated_since(last_sync)
            count = await pg_repo.upsert_many(jobs)
            await sync_repo.update_last_sync_time(ENTITY_NAME, start_time)

            logger.info(f"[job incremental sync] since={last_sync} synced={count}")
            return count