import os
import redis
from dotenv import load_dotenv

load_dotenv()

_redis_client = None

def get_redis() -> redis.Redis:
    """
    Lazy singleton — creates the Redis connection once,
    reuses it for every subsequent call.
    """
    global _redis_client
    if _redis_client is None:
        _redis_client = redis.from_url(
            os.getenv("REDIS_URL", "redis://localhost:6379"),
            decode_responses=True  # return strings not bytes
        )
    return _redis_client