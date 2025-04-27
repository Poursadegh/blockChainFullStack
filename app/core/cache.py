from fastapi_cache import FastAPICache
from fastapi_cache.backends.redis import RedisBackend
from fastapi_cache.decorator import cache
from redis import asyncio as aioredis
from .config import settings

async def init_cache():
    redis = aioredis.from_url(
        settings.REDIS_URL,
        encoding="utf8",
        decode_responses=True
    )
    FastAPICache.init(RedisBackend(redis), prefix="crypto-cache")

# Cache decorator with default expiration time
def cache_response(expire: int = 60):
    return cache(expire=expire) 