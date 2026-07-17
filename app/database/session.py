from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession

from app.database.mysql import MySQLSessionLocal
from app.database.postgres import PostgresSessionLocal


async def get_postgres_session() -> AsyncGenerator[AsyncSession, None]:
    async with PostgresSessionLocal() as session:
        yield session


async def get_mysql_session() -> AsyncGenerator[AsyncSession, None]:
    async with MySQLSessionLocal() as session:
        yield session