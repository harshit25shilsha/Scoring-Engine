import json

from app.core.redis_client import redis_client
from app.config.logging import logger
from app.config import settings

CACHE_TTL_SECONDS= settings.CACHE_TTL_SECONDS


def _ranked_candidates_key(job_id: int, page: int, page_size: int, min_score, sort_by: str, sort_order: str) -> str:
    return f"job_candidates:{job_id}:{page}:{page_size}:{min_score}:{sort_by}:{sort_order}"


def _ranked_candidates_key_pattern(job_id: int) -> str:
    return f"job_candidates:{job_id}:*"


async def get_cached_ranked_candidates(
    job_id: int, page: int, page_size: int, min_score, sort_by: str, sort_order: str
) -> dict | None:
    try:
        key = _ranked_candidates_key(job_id, page, page_size, min_score, sort_by, sort_order)
        cached = await redis_client.get(key)
        return json.loads(cached) if cached else None
    except Exception as e:
        # Cache failures should never break the actual request — log and fall through to DB.
        logger.error(f"[cache] read failed for job={job_id}: {e}")
        return None


async def set_cached_ranked_candidates(
    job_id: int, page: int, page_size: int, min_score, sort_by: str, sort_order: str, data: dict
) -> None:
    try:
        key = _ranked_candidates_key(job_id, page, page_size, min_score, sort_by, sort_order)
        await redis_client.set(key, json.dumps(data), ex=CACHE_TTL_SECONDS)
    except Exception as e:
        logger.error(f"[cache] write failed for job={job_id}: {e}")


async def invalidate_ranked_candidates_cache(job_id: int) -> None:
    """
    Clears ALL cached page/filter/sort variants for a job at once, since a
    rescore can change ranking across every combination, not just one page.
    Uses SCAN (not KEYS) to avoid blocking Redis on large keyspaces.
    """
    try:
        pattern = _ranked_candidates_key_pattern(job_id)
        keys_to_delete = []
        async for key in redis_client.scan_iter(match=pattern, count=100):
            keys_to_delete.append(key)
        if keys_to_delete:
            await redis_client.delete(*keys_to_delete)
            logger.info(f"[cache] invalidated {len(keys_to_delete)} cached entries for job={job_id}")
    except Exception as e:
        logger.error(f"[cache] invalidation failed for job={job_id}: {e}")