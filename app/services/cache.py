from redis import asyncio as aioredis
from typing import Optional, List, Dict, Any
import json
from datetime import timedelta
from ..core.config import settings

class CacheService:
    def __init__(self):
        self.redis = aioredis.from_url(
            settings.REDIS_URL,
            encoding="utf8",
            decode_responses=True
        )
        self.prefix = "crypto_social:"

    async def get(self, key: str) -> Optional[str]:
        return await self.redis.get(f"{self.prefix}{key}")

    async def set(self, key: str, value: str, expire: int = 3600):
        await self.redis.setex(f"{self.prefix}{key}", expire, value)

    async def delete(self, key: str):
        await self.redis.delete(f"{self.prefix}{key}")

    async def get_user_profile(self, user_id: int) -> Optional[Dict[str, Any]]:
        data = await self.get(f"profile:{user_id}")
        return json.loads(data) if data else None

    async def set_user_profile(self, user_id: int, profile_data: Dict[str, Any]):
        await self.set(f"profile:{user_id}", json.dumps(profile_data), expire=3600)

    async def get_user_feed(self, user_id: int, page: int = 1, limit: int = 20) -> List[Dict[str, Any]]:
        data = await self.get(f"feed:{user_id}:{page}:{limit}")
        return json.loads(data) if data else []

    async def set_user_feed(self, user_id: int, posts: List[Dict[str, Any]], page: int = 1, limit: int = 20):
        await self.set(f"feed:{user_id}:{page}:{limit}", json.dumps(posts), expire=300)

    async def get_post(self, post_id: int) -> Optional[Dict[str, Any]]:
        data = await self.get(f"post:{post_id}")
        return json.loads(data) if data else None

    async def set_post(self, post_id: int, post_data: Dict[str, Any]):
        await self.set(f"post:{post_id}", json.dumps(post_data), expire=1800)

    async def get_chat_messages(self, room_id: int, limit: int = 50) -> List[Dict[str, Any]]:
        data = await self.get(f"chat:{room_id}:messages:{limit}")
        return json.loads(data) if data else []

    async def set_chat_messages(self, room_id: int, messages: List[Dict[str, Any]], limit: int = 50):
        await self.set(f"chat:{room_id}:messages:{limit}", json.dumps(messages), expire=300)

    async def get_online_users(self) -> List[int]:
        data = await self.get("online_users")
        return json.loads(data) if data else []

    async def set_online_users(self, user_ids: List[int]):
        await self.set("online_users", json.dumps(user_ids), expire=60)

    async def increment_post_metrics(self, post_id: int, metric: str):
        await self.redis.hincrby(f"{self.prefix}post_metrics:{post_id}", metric, 1)

    async def get_post_metrics(self, post_id: int) -> Dict[str, int]:
        return await self.redis.hgetall(f"{self.prefix}post_metrics:{post_id}")

    async def add_to_search_index(self, entity_type: str, entity_id: int, data: Dict[str, Any]):
        key = f"{self.prefix}search:{entity_type}:{entity_id}"
        await self.redis.hmset(key, data)
        await self.redis.expire(key, 86400)  # 24 hours

    async def search(self, entity_type: str, query: str) -> List[Dict[str, Any]]:
        pattern = f"{self.prefix}search:{entity_type}:*"
        keys = await self.redis.keys(pattern)
        results = []
        for key in keys:
            data = await self.redis.hgetall(key)
            if query.lower() in str(data).lower():
                results.append(data)
        return results

    async def clear_user_cache(self, user_id: int):
        # Clear all cached data for a user
        keys = await self.redis.keys(f"{self.prefix}*:{user_id}:*")
        if keys:
            await self.redis.delete(*keys)

    async def clear_post_cache(self, post_id: int):
        # Clear all cached data for a post
        keys = await self.redis.keys(f"{self.prefix}post:{post_id}*")
        if keys:
            await self.redis.delete(*keys)

cache_service = CacheService() 