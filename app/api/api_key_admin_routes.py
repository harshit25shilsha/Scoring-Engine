from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.api_keys import create_api_key, delete_api_key, list_keys, revoke_key
from app.core.auth import require_scope
from app.database.models import ApiKey
from app.database.session import get_postgres_session

router = APIRouter(prefix="/admin", tags=["api-key-admin"])


class CreateApiKeyRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    scope: str = Field(default="read")
    rate_limit_per_minute: int = Field(default=60, ge=1)


class ApiKeyMetadataResponse(BaseModel):
    id: int
    created_by_id: int | None
    name: str
    key_prefix: str
    scope: str
    status: str
    is_active: bool
    rate_limit_per_minute: int
    created_at: str | None = None
    revoked_at: str | None = None
    last_used_at: str | None = None


@router.post(
    "/api-keys",
    response_model=dict,
    summary="Create API Key",
    description=(
        "Admin-only endpoint for creating application keys. "
        "Use a name such as 'frontend-read-key', 'backend-read-write-key', or 'key-admin-bootstrap'. "
        "Allowed scopes are 'read', 'read_write', and 'key_admin'."
    ),
)
async def create_admin_api_key(
    payload: CreateApiKeyRequest,
    db: AsyncSession = Depends(get_postgres_session),
    acting_key: ApiKey = Depends(require_scope("key_admin")),
):
    if payload.scope not in {"read", "write", "read_write"}:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid scope")

    raw_key = await create_api_key(
        db,
        name=payload.name,
        scope=payload.scope,
        rate_limit_per_minute=payload.rate_limit_per_minute,
        created_by_id=acting_key.id,
    )
    return {
        "message": "API key created successfully. Store this raw key securely; it will only be shown once.",
        "key": raw_key,
        "scope": payload.scope,
        "rate_limit_per_minute": payload.rate_limit_per_minute,
    }


@router.get(
    "/api-keys",
    response_model=list[ApiKeyMetadataResponse],
    summary="List API Keys",
    description=(
        "Admin-only metadata listing for API keys. "
        "This endpoint never returns the plaintext secret; it only shows key metadata such as name, scope, prefix, status, and timestamps."
    ),
)
async def list_admin_api_keys(
    db: AsyncSession = Depends(get_postgres_session),
    _: ApiKey = Depends(require_scope("key_admin")),
):
    keys = await list_keys(db)
    return [
        ApiKeyMetadataResponse(
            id=key.id,
            created_by_id=key.created_by_id,
            name=key.name,
            key_prefix=key.key_prefix,
            scope=key.scope,
            status=key.status,
            is_active=key.is_active,
            rate_limit_per_minute=key.rate_limit_per_minute,
            created_at=key.created_at.isoformat() if key.created_at else None,
            revoked_at=key.revoked_at.isoformat() if key.revoked_at else None,
            last_used_at=key.last_used_at.isoformat() if key.last_used_at else None,
        )
        for key in keys
    ]


@router.get(
    "/api-keys/{key_id}",
    response_model=ApiKeyMetadataResponse,
    summary="Get API Key",
    description=(
        "Admin-only lookup for a single API key record. "
        "Returns only metadata; the raw secret is never exposed again after creation."
    ),
)
async def get_admin_api_key(
    key_id: int,
    db: AsyncSession = Depends(get_postgres_session),
    _: ApiKey = Depends(require_scope("key_admin")),
):
    key = await db.get(ApiKey, key_id)
    if key is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="API key not found")

    return ApiKeyMetadataResponse(
        id=key.id,
        created_by_id=key.created_by_id,
        name=key.name,
        key_prefix=key.key_prefix,
        scope=key.scope,
        status=key.status,
        is_active=key.is_active,
        rate_limit_per_minute=key.rate_limit_per_minute,
        created_at=key.created_at.isoformat() if key.created_at else None,
        revoked_at=key.revoked_at.isoformat() if key.revoked_at else None,
        last_used_at=key.last_used_at.isoformat() if key.last_used_at else None,
    )


@router.post(
    "/api-keys/{key_id}/revoke",
    response_model=dict,
    summary="Revoke API Key",
    description=(
        "Admin-only route to revoke an existing API key. "
        "A revoked key fails authentication immediately and cannot access protected routes."
    ),
)
async def revoke_admin_api_key(
    key_id: int,
    db: AsyncSession = Depends(get_postgres_session),
    acting_key: ApiKey = Depends(require_scope("key_admin")),
):
    try:
        key = await revoke_key(db, key_id, acting_key_id=acting_key.id)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    if key is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="API key not found")
    return {"message": "API key revoked", "id": key_id, "status": key.status}


@router.delete(
    "/api-keys/{key_id}",
    response_model=dict,
    summary="Delete API Key",
    description=(
        "Admin-only route to permanently delete an API key record. "
        "The value is removed from storage and cannot be used afterward."
    ),
)
async def delete_admin_api_key(
    key_id: int,
    db: AsyncSession = Depends(get_postgres_session),
    acting_key: ApiKey = Depends(require_scope("key_admin")),
):
    try:
        deleted = await delete_api_key(db, key_id, acting_key_id=acting_key.id)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    if not deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="API key not found")
    return {"message": "API key deleted", "id": key_id}
