from app.core.redis_client import redis_client

from app.config import settings

RESCORE_LOCK_TTL_SECONDS = settings.RESCORE_LOCK_TTL_SECONDS

async def try_acquire_rescore_lock(job_id: int)-> bool:
    key = f"rescore_lock:{job_id}"
    
    acquired = await redis_client.set(key,"1", nx=True, ex=RESCORE_LOCK_TTL_SECONDS)
    return bool(acquired)

async def release_rescore_lock(job_id: int)-> None:
    key= f"rescore_lock:{job_id}"
    await redis_client.delete(key)
    