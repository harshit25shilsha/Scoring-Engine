import logging

from app.core.redis_client import redis_client

logger = logging.getLogger(__name__)


async def check_rate_limit(key_id: int, limit_per_minute: int) -> bool:
    """
    Fixed-window rate limit: one Redis counter per key per minute.
    Returns True if the request is allowed, False if the limit is exceeded.
    If Redis is unavailable, the rate limiter gracefully skips enforcement so
    authentication can continue without crashing the request path.
    """
    try:
        from datetime import datetime, timezone
        window = datetime.now(timezone.utc).strftime("%Y%m%d%H%M")
        redis_key = f"rate_limit:{key_id}:{window}"

        current = await redis_client.incr(redis_key)
        if current == 1:
            await redis_client.expire(redis_key, 60)

        return current <= limit_per_minute
    except Exception:
        logger.warning("Redis rate-limit check unavailable; allowing request without rate-limit enforcement.", exc_info=True)
        return True