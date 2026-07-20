from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.config import settings

mysql_engine = create_async_engine(
    settings.mysql_url,
    echo=settings.DEBUG,
    future=True,
    pool_pre_ping= False,
    pool_size=5,
    max_overflow=10,
)

MySQLSessionLocal = async_sessionmaker(
    bind=mysql_engine,
    class_=AsyncSession,
    expire_on_commit=False,
)