# -*- coding: utf-8 -*-
"""Cache service implementation using Redis"""

import json
import redis.asyncio as redis
from typing import Optional, Any, Dict, List
from datetime import timedelta
import logging

from ..core.config import settings

logger = logging.getLogger(__name__)


class CacheService:
    """Redis cache service for performance optimization"""
    
    _instance = None
    _redis_client = None
    
    def __new__(cls):
        """Singleton pattern implementation"""
        if cls._instance is None:
            cls._instance = super(CacheService, cls).__new__(cls)
        return cls._instance
    
    async def connect(self):
        """Initialize Redis connection"""
        if not self._redis_client:
            try:
                self._redis_client = await redis.from_url(
                    f"redis://{settings.REDIS_HOST}:{settings.REDIS_PORT}/{settings.REDIS_DB}",
                    password=settings.REDIS_PASSWORD,
                    encoding="utf-8",
                    decode_responses=True
                )
                await self._redis_client.ping()
                logger.info("Redis cache connected successfully")
            except Exception as e:
                logger.error(f"Failed to connect to Redis: {e}")
                self._redis_client = None
    
    async def disconnect(self):
        """Close Redis connection"""
        if self._redis_client:
            await self._redis_client.close()
            self._redis_client = None
    
    async def get(self, key: str) -> Optional[Any]:
        """Get value from cache"""
        if not self._redis_client:
            return None
        
        try:
            value = await self._redis_client.get(key)
            if value:
                return json.loads(value)
            return None
        except Exception as e:
            logger.error(f"Cache get error: {e}")
            return None
    
    async def set(self, key: str, value: Any, expire: Optional[int] = 3600):
        """Set value in cache with optional expiration"""
        if not self._redis_client:
            return False
        
        try:
            serialized = json.dumps(value)
            if expire:
                await self._redis_client.setex(key, expire, serialized)
            else:
                await self._redis_client.set(key, serialized)
            return True
        except Exception as e:
            logger.error(f"Cache set error: {e}")
            return False
    
    async def delete(self, key: str) -> bool:
        """Delete key from cache"""
        if not self._redis_client:
            return False
        
        try:
            await self._redis_client.delete(key)
            return True
        except Exception as e:
            logger.error(f"Cache delete error: {e}")
            return False
    
    async def delete_pattern(self, pattern: str) -> int:
        """Delete all keys matching pattern"""
        if not self._redis_client:
            return 0
        
        try:
            keys = await self._redis_client.keys(pattern)
            if keys:
                deleted = await self._redis_client.delete(*keys)
                return deleted
            return 0
        except Exception as e:
            logger.error(f"Cache delete pattern error: {e}")
            return 0
    
    async def exists(self, key: str) -> bool:
        """Check if key exists in cache"""
        if not self._redis_client:
            return False
        
        try:
            return await self._redis_client.exists(key) > 0
        except Exception as e:
            logger.error(f"Cache exists error: {e}")
            return False
    
    async def increment(self, key: str, amount: int = 1) -> Optional[int]:
        """Increment counter in cache"""
        if not self._redis_client:
            return None
        
        try:
            return await self._redis_client.incrby(key, amount)
        except Exception as e:
            logger.error(f"Cache increment error: {e}")
            return None
    
    async def get_ttl(self, key: str) -> Optional[int]:
        """Get time to live for key"""
        if not self._redis_client:
            return None
        
        try:
            ttl = await self._redis_client.ttl(key)
            return ttl if ttl > 0 else None
        except Exception as e:
            logger.error(f"Cache TTL error: {e}")
            return None
    
    async def set_list(self, key: str, values: List[Any], expire: Optional[int] = 3600):
        """Store list in cache"""
        if not self._redis_client:
            return False
        
        try:
            await self._redis_client.delete(key)
            for value in values:
                await self._redis_client.rpush(key, json.dumps(value))
            if expire:
                await self._redis_client.expire(key, expire)
            return True
        except Exception as e:
            logger.error(f"Cache set list error: {e}")
            return False
    
    async def get_list(self, key: str, start: int = 0, end: int = -1) -> List[Any]:
        """Get list from cache"""
        if not self._redis_client:
            return []
        
        try:
            values = await self._redis_client.lrange(key, start, end)
            return [json.loads(v) for v in values]
        except Exception as e:
            logger.error(f"Cache get list error: {e}")
            return []
    
    async def cache_key_wrapper(self, prefix: str, *args, **kwargs) -> str:
        """Generate cache key from prefix and arguments"""
        key_parts = [prefix]
        key_parts.extend(str(arg) for arg in args)
        key_parts.extend(f"{k}:{v}" for k, v in sorted(kwargs.items()))
        return ":".join(key_parts)
    
    async def get_or_set(self, key: str, func, expire: Optional[int] = 3600):
        """Get from cache or compute and set"""
        value = await self.get(key)
        if value is not None:
            return value
        
        value = await func()
        await self.set(key, value, expire)
        return value
    
    async def clear_user_cache(self, user_id: int):
        """Clear all cache entries for a specific user"""
        patterns = [
            f"user:{user_id}:*",
            f"session:{user_id}",
            f"cart:{user_id}",
            f"wishlist:{user_id}"
        ]
        
        total_deleted = 0
        for pattern in patterns:
            deleted = await self.delete_pattern(pattern)
            total_deleted += deleted
        
        return total_deleted
    
    async def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        if not self._redis_client:
            return {"connected": False}
        
        try:
            info = await self._redis_client.info()
            return {
                "connected": True,
                "used_memory": info.get("used_memory_human"),
                "connected_clients": info.get("connected_clients"),
                "total_commands": info.get("total_commands_processed"),
                "keyspace_hits": info.get("keyspace_hits"),
                "keyspace_misses": info.get("keyspace_misses"),
                "uptime_seconds": info.get("uptime_in_seconds")
            }
        except Exception as e:
            logger.error(f"Failed to get cache stats: {e}")
            return {"connected": False, "error": str(e)}
