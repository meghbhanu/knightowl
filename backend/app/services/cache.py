import hashlib
import json
from app.redis_client import get_redis

CACHE_TTL = 3600

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