from fastapi import Header, HTTPException, status, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.session import get_postgres_session
from app.database.models import ApiKey
from app.core.api_keys import verify_key
from app.core.key_rate_limit import check_rate_limit


async def verify_api_key(
    x_api_key: str = Header(...),
    db: AsyncSession = Depends(get_postgres_session),
) -> ApiKey:
    key_row = await verify_key(db, x_api_key)
    if key_row is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or missing API key")

    allowed = await check_rate_limit(key_row.id, key_row.rate_limit_per_minute)
    if not allowed:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Rate limit exceeded ({key_row.rate_limit_per_minute} requests/minute for this key)",
        )

    return key_row


async def require_admin_scope(key_row: ApiKey = Depends(verify_api_key)) -> ApiKey:
    if key_row.scope != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This action requires an admin-scoped API key",
        )
    return key_row