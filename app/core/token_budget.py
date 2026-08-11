from datetime import date

from redis import Redis
from redis.exceptions import RedisError

from app.config import settings
from app.config.logging import logger

# Separate sync Redis client — GroqClient.extract_json() runs in a worker
# thread (via asyncio.to_thread), so it needs a sync-safe Redis call here,
# not the async client used everywhere else in the app.
_sync_redis = Redis.from_url(settings.REDIS_URL, decode_responses=True)

DAILY_TOKEN_LIMIT = settings.DAILY_TOKEN_LIMIT


def _today_key() -> str:
    return f"groq_tokens_used:{date.today().isoformat()}"


def track_token_usage(tokens_used: int) -> None:
    """Increments today's token usage counter. Called synchronously from GroqClient."""
    try:
        key = _today_key()
        _sync_redis.incrby(key, tokens_used)
        _sync_redis.expire(key, 86400 * 2)  # auto-cleanup after 2 days
    except RedisError as e:
        # Tracking failure should never break actual Groq calls — log and continue.
        logger.error(f"[token-budget] failed to track usage: {e}")


def get_used_today() -> int:
    try:
        used = _sync_redis.get(_today_key())
        return int(used) if used else 0
    except RedisError as e:
        logger.error(f"[token-budget] failed to read usage: {e}")
        return 0


def get_remaining_budget() -> int:
    return max(0, DAILY_TOKEN_LIMIT - get_used_today())


def has_sufficient_budget(min_required: int = 2000) -> bool:
    """
    Returns False if remaining budget is too low to safely attempt more work.
    min_required is a conservative estimate of tokens needed for one more
    semantic scoring call (structured JSON in + response out).
    """
    return get_remaining_budget() >= min_required