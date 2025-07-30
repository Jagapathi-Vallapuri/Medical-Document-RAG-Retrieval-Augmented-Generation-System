import redis
import os
import json
import logging
from models import ContentType, ContextChunk, RetrievalResult

logger = logging.getLogger(__name__)

def serialize_for_redis(obj):
    """Convert objects to JSON-serializable format"""
    if isinstance(obj, ContentType):
        return obj.value
    elif isinstance(obj, ContextChunk):
        return {
            'content_type': obj.content_type.value,
            'text': obj.text,
            'pdf_id': obj.pdf_id,
            'page': obj.page,
            'score': obj.score,
            'tables': obj.tables
        }
    elif isinstance(obj, RetrievalResult):
        return {
            'context_chunks': [serialize_for_redis(chunk) for chunk in obj.context_chunks],
            'raw_mongo_text': obj.raw_mongo_text,
            'raw_mongo_images': obj.raw_mongo_images,
            's3_cache': obj.s3_cache
        }
    elif hasattr(obj, '__dict__'):
        # Handle other objects with __dict__
        result = {}
        for key, value in obj.__dict__.items():
            try:
                result[key] = serialize_for_redis(value)
            except (TypeError, ValueError):
                # Skip non-serializable fields
                continue
        return result
    elif isinstance(obj, list):
        return [serialize_for_redis(item) for item in obj]
    elif isinstance(obj, dict):
        return {key: serialize_for_redis(value) for key, value in obj.items()}
    else:
        return obj

def deserialize_from_redis(data, target_type=None):
    """Convert Redis data back to proper objects"""
    if target_type == RetrievalResult and isinstance(data, dict):
        context_chunks = []
        for chunk_data in data.get('context_chunks', []):
            chunk = ContextChunk(
                content_type=ContentType(chunk_data['content_type']),
                text=chunk_data['text'],
                pdf_id=chunk_data['pdf_id'],
                page=chunk_data['page'],
                score=chunk_data['score'],
                tables=chunk_data.get('tables', [])
            )
            context_chunks.append(chunk)
        
        return RetrievalResult(
            context_chunks=context_chunks,
            raw_mongo_text=data.get('raw_mongo_text', []),
            raw_mongo_images=data.get('raw_mongo_images', []),
            s3_cache=data.get('s3_cache', {})
        )
    return data

_redis_client = None
_redis_available = None

def get_redis_client():
    global _redis_client, _redis_available
    
    if _redis_available is False:
        return None
        
    if _redis_client is None:
        try:
            redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
            _redis_client = redis.Redis.from_url(redis_url, decode_responses=True)
            _redis_client.ping()
            _redis_available = True
            logger.info("Redis connection established successfully")
        except Exception as e:
            logger.warning(f"Redis not available: {e}. Continuing without Redis cache.")
            _redis_available = False
            _redis_client = None
            
    return _redis_client

def redis_cache_get(key: str, target_type=None):
    client = get_redis_client()
    if client is None:
        return None
        
    try:
        value = client.get(key)
        if value is not None:
            try:
                parsed_value = json.loads(str(value))
                return deserialize_from_redis(parsed_value, target_type)
            except Exception:
                return value
    except Exception as e:
        logger.warning(f"Redis get error for key {key}: {e}")
    return None

def redis_cache_set(key: str, value, ex: int = 3600):
    client = get_redis_client()
    if client is None:
        return False
        
    try:
        serialized_value = serialize_for_redis(value)
        client.set(key, json.dumps(serialized_value), ex=ex)
        return True
    except Exception as e:
        logger.warning(f"Redis set error for key {key}: {e}")
        return False

def is_redis_available():
    """Check if Redis is available"""
    global _redis_available
    if _redis_available is None:
        get_redis_client()
    return _redis_available or False
