from fastapi import Header, HTTPException, status, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.session import get_postgres_session
from app.database.models import ApiKey
from app.core.api_keys import verify_key, normalize_scope
from app.core.key_rate_limit import check_rate_limit


async def _check_key_rate_limit(key_row: ApiKey) -> None:
    allowed = await check_rate_limit(key_row.id, key_row.rate_limit_per_minute)
    if not allowed:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Rate limit exceeded ({key_row.rate_limit_per_minute} requests/minute for this key)",
        )


async def get_current_api_key(
    x_api_key: str = Header(..., alias="X-API-Key"),
    db: AsyncSession = Depends(get_postgres_session),
) -> ApiKey:
    if not x_api_key:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing API key")

    key_row = await verify_key(db, x_api_key)
    if key_row is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or missing API key")

    await _check_key_rate_limit(key_row)
    return key_row


async def verify_api_key(
    key_row: ApiKey = Depends(get_current_api_key),
) -> ApiKey:
    return key_row


def require_scope(*allowed_scopes: str):
    async def dependency(api_key: ApiKey = Depends(get_current_api_key)) -> ApiKey:
        normalized_key_scopes = normalize_scope(api_key.scope)
        if not set(allowed_scopes) & normalized_key_scopes:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"This action requires one of the scopes: {', '.join(allowed_scopes)}",
            )
        return api_key

    return dependency


async def require_admin_scope(key_row: ApiKey = Depends(get_current_api_key)) -> ApiKey:
    if "key_admin" not in normalize_scope(key_row.scope):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This action requires a key_admin-scoped API key",
        )
    return key_row