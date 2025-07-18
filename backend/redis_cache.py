import redis
import os
import json

# Singleton Redis client
_redis_client = None

def get_redis_client():
    global _redis_client
    if _redis_client is None:
        redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
        _redis_client = redis.Redis.from_url(redis_url, decode_responses=True)
    return _redis_client

def redis_cache_get(key: str):
    client = get_redis_client()
    value = client.get(key)
    if value is not None:
        try:
            return json.loads(str(value))
        except Exception:
            return value
    return None

def redis_cache_set(key: str, value, ex: int = 3600):
    client = get_redis_client()
    try:
        client.set(key, json.dumps(value), ex=ex)
    except Exception as e:
        pass
