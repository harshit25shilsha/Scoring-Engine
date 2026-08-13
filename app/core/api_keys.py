import hashlib
import secrets
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models import ApiKey


def _hash_key(raw_key: str) -> str:
    return hashlib.sha256(raw_key.encode()).hexdigest()


async def create_api_key(
    db: AsyncSession, name: str, scope: str = "read", rate_limit_per_minute: int = 60
) -> str:
    """Generates a new key, stores its hash, returns the RAW key ONCE — never retrievable again."""
    raw_key = secrets.token_urlsafe(32)
    db.add(ApiKey(
        name=name,
        key_hash=_hash_key(raw_key),
        scope=scope,
        rate_limit_per_minute=rate_limit_per_minute,
        is_active=True,
        created_at=datetime.now(timezone.utc),
    ))
    await db.commit()
    return raw_key


async def verify_key(db: AsyncSession, raw_key: str) -> ApiKey | None:
    key_hash = _hash_key(raw_key)
    result = await db.execute(
        select(ApiKey).where(ApiKey.key_hash == key_hash, ApiKey.is_active.is_(True))
    )
    key_row = result.scalar_one_or_none()
    if key_row:
        key_row.last_used_at = datetime.now(timezone.utc)
        await db.commit()
    return key_row


async def revoke_key(db: AsyncSession, key_id: int) -> None:
    key = await db.get(ApiKey, key_id)
    if key:
        key.is_active = False
        await db.commit()


async def list_keys(db: AsyncSession) -> list[ApiKey]:
    result = await db.execute(select(ApiKey))
    return list(result.scalars().all())