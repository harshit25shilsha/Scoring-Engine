from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.config import settings

postgres_engine = create_async_engine(
    settings.postgres_url,
    echo=settings.DEBUG,
    future=True,
    pool_pre_ping=True,
    pool_size=10,
    max_overflow=20,
)

PostgresSessionLocal = async_sessionmaker(
    bind=postgres_engine,
    class_=AsyncSession,
    expire_on_commit=False,
)