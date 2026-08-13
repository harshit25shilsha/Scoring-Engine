from app.core.redis_client import redis_client


async def check_rate_limit(key_id: int, limit_per_minute: int) -> bool:
    """
    Fixed-window rate limit: one Redis counter per key per minute.
    Returns True if the request is allowed, False if the limit is exceeded.
    """
    from datetime import datetime, timezone
    window = datetime.now(timezone.utc).strftime("%Y%m%d%H%M")  # changes every minute
    redis_key = f"rate_limit:{key_id}:{window}"

    current = await redis_client.incr(redis_key)
    if current == 1:
        await redis_client.expire(redis_key, 60)

    return current <= limit_per_minute