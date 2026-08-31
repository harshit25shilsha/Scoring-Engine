import hashlib
import secrets
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models import ApiKey

VALID_API_KEY_SCOPES = {"read", "write", "read_write", "key_admin"}


def _hash_key(raw_key: str) -> str:
    return hashlib.sha256(raw_key.encode()).hexdigest()


def normalize_scope(scope: str) -> set[str]:
    if scope == "read_write":
        return {"read", "write", "read_write"}
    return {scope}


async def create_api_key(
    db: AsyncSession,
    name: str,
    scope: str = "read",
    rate_limit_per_minute: int = 60,
    created_by_id: int | None = None,
) -> str:
    """Generates a new key, stores its hash, and returns the raw key once."""
    if scope not in VALID_API_KEY_SCOPES:
        raise ValueError(f"Unsupported API key scope: {scope}")

    raw_key = secrets.token_urlsafe(32)
    db.add(
        ApiKey(
            created_by_id=created_by_id,
            name=name,
            key_hash=_hash_key(raw_key),
            key_prefix=raw_key[:8],
            scope=scope,
            status="active",
            rate_limit_per_minute=rate_limit_per_minute,
            is_active=True,
            created_at=datetime.now(timezone.utc),
        )
    )
    await db.commit()
    return raw_key


async def verify_key(db: AsyncSession, raw_key: str) -> ApiKey | None:
    key_hash = _hash_key(raw_key)
    result = await db.execute(
        select(ApiKey).where(
            ApiKey.key_hash == key_hash,
            ApiKey.is_active.is_(True),
            ApiKey.status == "active",
        )
    )
    key_row = result.scalar_one_or_none()
    if key_row:
        key_row.last_used_at = datetime.now(timezone.utc)
        await db.commit()
    return key_row


async def _ensure_admin_key_can_be_removed(
    db: AsyncSession,
    key: ApiKey,
    acting_key_id: int | None,
    action: str,
) -> None:
    if key.id == acting_key_id:
        raise ValueError(f"An admin API key cannot {action} itself")

    if key.scope != "key_admin" or not key.is_active:
        if acting_key_id is not None and key.created_by_id != acting_key_id:
            raise ValueError("An admin API key cannot remove another admin's created API key")
        return

    result = await db.execute(
        select(ApiKey).where(
            ApiKey.scope == "key_admin",
            ApiKey.is_active.is_(True),
            ApiKey.status == "active",
        )
    )
    if len(result.scalars().all()) <= 1:
        raise ValueError("Cannot remove the last active key_admin API key")

    if acting_key_id is not None:
        raise ValueError(f"An admin API key cannot {action} another key_admin API key")


async def revoke_key(
    db: AsyncSession,
    key_id: int,
    acting_key_id: int | None = None,
) -> ApiKey | None:
    key = await db.get(ApiKey, key_id)
    if key is None:
        return None

    await _ensure_admin_key_can_be_removed(db, key, acting_key_id, "revoke")

    key.is_active = False
    key.status = "revoked"
    key.revoked_at = datetime.now(timezone.utc)
    await db.commit()
    return key


async def delete_api_key(
    db: AsyncSession,
    key_id: int,
    acting_key_id: int | None = None,
) -> bool:
    key = await db.get(ApiKey, key_id)
    if key is None:
        return False

    await _ensure_admin_key_can_be_removed(db, key, acting_key_id, "delete")
    await db.delete(key)
    await db.commit()
    return True


async def list_keys(db: AsyncSession) -> list[ApiKey]:
    result = await db.execute(select(ApiKey).order_by(ApiKey.created_at.desc()))
    return list(result.scalars().all())