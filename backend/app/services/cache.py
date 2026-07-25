import hashlib
import json
import os
from datetime import datetime
from app.redis_client import get_redis

CACHE_TTL = 3600
DAILY_CALL_LIMIT = int(os.getenv("DAILY_CALL_LIMIT", 500))

def make_cache_key(messages: list) -> str:
    """
    Hash the conversation content to create a cache key.
    Same question in same context = same key = cache hit.
    """
    content = json.dumps([{"role": m["role"], "content": m["content"]} for m in messages])
    return "chat:" + hashlib.sha256(content.encode()).hexdigest()

def get_cached_response(messages: list) -> dict | None:
    """Return cached AI response if it exists, else None."""
    try:
        redis = get_redis()
        key = make_cache_key(messages)
        cached = redis.get(key)
        if cached:
            return json.loads(cached)
    except Exception:
        pass  # Redis unavailable — degrade gracefully, never crash
    return None

def cache_response(messages: list, response: dict) -> None:
    """Cache an AI response with TTL."""
    try:
        redis = get_redis()
        key = make_cache_key(messages)
        redis.setex(key, CACHE_TTL, json.dumps(response))
    except Exception:
        pass  # Redis unavailable — fail silently

def check_global_budget() -> tuple[bool, int]:
    """
    Global daily spend cap across all sessions.
    Returns (under_limit, calls_remaining_today).
    Fails open — if Redis is down, allow the request.
    """
    try:
        redis = get_redis()
        today = datetime.utcnow().strftime("%Y-%m-%d")
        key = f"global_calls:{today}"

        count = redis.get(key)
        current = int(count) if count else 0

        if current >= DAILY_CALL_LIMIT:
            return False, 0

        redis.incr(key)
        redis.expire(key, 86400)
        return True, DAILY_CALL_LIMIT - current - 1

    except Exception:
        return True, DAILY_CALL_LIMIT  # Redis down — fail open    