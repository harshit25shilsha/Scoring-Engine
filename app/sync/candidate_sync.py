from datetime import datetime, timezone

from app.config.logging import logger
from app.database.mysql import MySQLSessionLocal
from app.database.postgres import PostgresSessionLocal
from app.repositories.mysql.candidate_repository import CandidateRepository as MySQLCandidateRepo
from app.repositories.postgres.candidate_repository import CandidateRepository as PGCandidateRepo
from app.repositories.postgres.sync_repository import SyncRepository

ENTITY_NAME = "candidate"
EPOCH = datetime(1970, 1, 1, tzinfo=timezone.utc)


class CandidateSyncService:

    async def run_initial_migration(self) -> int:
        async with MySQLSessionLocal() as mysql_db, PostgresSessionLocal() as pg_db:
            mysql_repo = MySQLCandidateRepo(mysql_db)
            pg_repo = PGCandidateRepo(pg_db)
            sync_repo = SyncRepository(pg_db)

            start_time = datetime.now(timezone.utc)
            candidates = await mysql_repo.get_all_active()
            count = await pg_repo.upsert_many(candidates)
            await sync_repo.update_last_sync_time(ENTITY_NAME, start_time)

            logger.info(f"[candidate initial migration] synced={count}")
            return count

    async def run_incremental_sync(self) -> int:
        async with MySQLSessionLocal() as mysql_db, PostgresSessionLocal() as pg_db:
            mysql_repo = MySQLCandidateRepo(mysql_db)
            pg_repo = PGCandidateRepo(pg_db)
            sync_repo = SyncRepository(pg_db)

            last_sync = await sync_repo.get_last_sync_time(ENTITY_NAME) or EPOCH
            start_time = datetime.now(timezone.utc)

            candidates = await mysql_repo.get_updated_since(last_sync)
            count = await pg_repo.upsert_many(candidates)
            await sync_repo.update_last_sync_time(ENTITY_NAME, start_time)

            logger.info(f"[candidate incremental sync] since={last_sync} synced={count}")
            return count