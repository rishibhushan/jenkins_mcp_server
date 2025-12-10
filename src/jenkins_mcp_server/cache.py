"""
Caching Module for Jenkins MCP Server

Provides TTL-based caching for frequently accessed Jenkins data
to reduce API calls and improve performance.
"""

import asyncio
import logging
import time
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any, Callable, Dict, Optional, TypeVar

logger = logging.getLogger(__name__)

T = TypeVar('T')


@dataclass
class CachedData:
    """Container for cached data with expiration"""
    data: Any
    cached_at: float
    ttl_seconds: int
    key: str
    
    def is_expired(self) -> bool:
        """Check if cached data has expired"""
        age = time.time() - self.cached_at
        return age >= self.ttl_seconds
    
    def age_seconds(self) -> float:
        """Get age of cached data in seconds"""
        return time.time() - self.cached_at
    
    def time_until_expiry(self) -> float:
        """Get seconds until expiry (negative if expired)"""
        return self.ttl_seconds - self.age_seconds()


class CacheManager:
    """
    Thread-safe cache manager with TTL support.
    
    Features:
    - TTL-based expiration
    - Thread-safe operations with async locks
    - Cache statistics
    - Automatic cleanup of expired entries
    """
    
    def __init__(self):
        """Initialize cache manager"""
        self._cache: Dict[str, CachedData] = {}
        self._lock = asyncio.Lock()
        
        # Statistics
        self._hits = 0
        self._misses = 0
        self._evictions = 0
        
        logger.info("Cache manager initialized")
    
    async def get(self, key: str) -> Optional[Any]:
        """
        Get cached data if available and not expired.
        
        Args:
            key: Cache key
            
        Returns:
            Cached data if available and valid, None otherwise
        """
        async with self._lock:
            if key not in self._cache:
                self._misses += 1
                logger.debug(f"Cache miss: {key}")
                return None
            
            cached = self._cache[key]
            
            if cached.is_expired():
                # Remove expired entry
                del self._cache[key]
                self._evictions += 1
                self._misses += 1
                logger.debug(f"Cache expired: {key} (age: {cached.age_seconds():.1f}s)")
                return None
            
            self._hits += 1
            logger.debug(f"Cache hit: {key} (age: {cached.age_seconds():.1f}s, ttl: {cached.ttl_seconds}s)")
            return cached.data
    
    async def set(self, key: str, data: Any, ttl_seconds: int = 30) -> None:
        """
        Store data in cache with TTL.
        
        Args:
            key: Cache key
            data: Data to cache
            ttl_seconds: Time-to-live in seconds
        """
        async with self._lock:
            self._cache[key] = CachedData(
                data=data,
                cached_at=time.time(),
                ttl_seconds=ttl_seconds,
                key=key
            )
            logger.debug(f"Cached: {key} (ttl: {ttl_seconds}s)")
    
    async def invalidate(self, key: str) -> bool:
        """
        Invalidate (remove) a specific cache entry.
        
        Args:
            key: Cache key to invalidate
            
        Returns:
            True if key was in cache, False otherwise
        """
        async with self._lock:
            if key in self._cache:
                del self._cache[key]
                self._evictions += 1
                logger.debug(f"Invalidated: {key}")
                return True
            return False
    
    async def invalidate_pattern(self, pattern: str) -> int:
        """
        Invalidate all cache entries matching a pattern.
        
        Args:
            pattern: String pattern to match (substring match)
            
        Returns:
            Number of entries invalidated
        """
        async with self._lock:
            keys_to_remove = [
                key for key in self._cache.keys()
                if pattern in key
            ]
            
            for key in keys_to_remove:
                del self._cache[key]
                self._evictions += 1
            
            if keys_to_remove:
                logger.debug(f"Invalidated {len(keys_to_remove)} entries matching '{pattern}'")
            
            return len(keys_to_remove)
    
    async def clear(self) -> int:
        """
        Clear all cached data.
        
        Returns:
            Number of entries cleared
        """
        async with self._lock:
            count = len(self._cache)
            self._cache.clear()
            self._evictions += count
            logger.info(f"Cache cleared: {count} entries removed")
            return count
    
    async def cleanup_expired(self) -> int:
        """
        Remove all expired entries from cache.
        
        Returns:
            Number of expired entries removed
        """
        async with self._lock:
            expired_keys = [
                key for key, cached in self._cache.items()
                if cached.is_expired()
            ]
            
            for key in expired_keys:
                del self._cache[key]
                self._evictions += 1
            
            if expired_keys:
                logger.debug(f"Cleaned up {len(expired_keys)} expired entries")
            
            return len(expired_keys)
    
    async def get_or_fetch(
        self,
        key: str,
        fetch_func: Callable[[], Any],
        ttl_seconds: int = 30
    ) -> Any:
        """
        Get cached data or fetch and cache if not available.
        
        Args:
            key: Cache key
            fetch_func: Function to call to fetch data if not cached
            ttl_seconds: TTL for newly cached data
            
        Returns:
            Cached or freshly fetched data
        """
        # Try cache first
        cached_data = await self.get(key)
        if cached_data is not None:
            return cached_data
        
        # Fetch and cache
        data = fetch_func()
        await self.set(key, data, ttl_seconds)
        return data
    
    def get_stats(self) -> Dict[str, Any]:
        """
        Get cache statistics.
        
        Returns:
            Dictionary with cache statistics
        """
        total_requests = self._hits + self._misses
        hit_rate = (self._hits / total_requests * 100) if total_requests > 0 else 0
        
        return {
            "size": len(self._cache),
            "hits": self._hits,
            "misses": self._misses,
            "evictions": self._evictions,
            "total_requests": total_requests,
            "hit_rate_percent": round(hit_rate, 2)
        }
    
    def reset_stats(self) -> None:
        """Reset cache statistics"""
        self._hits = 0
        self._misses = 0
        self._evictions = 0
        logger.debug("Cache statistics reset")
    
    async def get_all_keys(self) -> list[str]:
        """Get all cache keys"""
        async with self._lock:
            return list(self._cache.keys())
    
    async def get_cache_info(self) -> Dict[str, Any]:
        """
        Get detailed cache information.
        
        Returns:
            Dictionary with cache details including per-entry info
        """
        async with self._lock:
            entries = []
            for key, cached in self._cache.items():
                entries.append({
                    "key": key,
                    "age_seconds": round(cached.age_seconds(), 2),
                    "ttl_seconds": cached.ttl_seconds,
                    "expires_in_seconds": round(cached.time_until_expiry(), 2),
                    "is_expired": cached.is_expired(),
                    "cached_at": datetime.fromtimestamp(cached.cached_at).isoformat()
                })
            
            return {
                "stats": self.get_stats(),
                "entries": entries
            }


# Global cache manager instance
_cache_manager: Optional[CacheManager] = None


def get_cache_manager() -> CacheManager:
    """Get or create the global cache manager instance"""
    global _cache_manager
    if _cache_manager is None:
        _cache_manager = CacheManager()
    return _cache_manager


# Convenience functions
async def get_cached(key: str) -> Optional[Any]:
    """Get cached data"""
    return await get_cache_manager().get(key)


async def set_cached(key: str, data: Any, ttl_seconds: int = 30) -> None:
    """Set cached data"""
    await get_cache_manager().set(key, data, ttl_seconds)


async def invalidate_cache(key: str) -> bool:
    """Invalidate cache entry"""
    return await get_cache_manager().invalidate(key)


async def clear_cache() -> int:
    """Clear all cache"""
    return await get_cache_manager().clear()


async def get_cache_stats() -> Dict[str, Any]:
    """Get cache statistics"""
    return get_cache_manager().get_stats()
