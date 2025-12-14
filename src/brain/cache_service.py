"""
Cache Service for OriginBrain.
Handles Redis-based caching for improved performance.
"""

import json
import pickle
import logging
from typing import Any, Optional, Union, List
from datetime import datetime, timedelta
import redis
from src.db.db import BrainDB

logger = logging.getLogger(__name__)

class CacheService:
    """Redis-based caching service with TTL support."""

    def __init__(self, host='localhost', port=6379, db=0, password=None):
        """
        Initialize cache service.

        Args:
            host: Redis host
            port: Redis port
            db: Redis database number
            password: Redis password (optional)
        """
        self.redis_client = None
        self.is_connected = False
        self.db = BrainDB()

        try:
            self.redis_client = redis.Redis(
                host=host,
                port=port,
                db=db,
                password=password,
                decode_responses=False,  # We'll handle encoding ourselves
                socket_connect_timeout=5,
                socket_timeout=5,
                retry_on_timeout=True
            )
            # Test connection
            self.redis_client.ping()
            self.is_connected = True
            logger.info("Connected to Redis cache")
        except Exception as e:
            logger.warning(f"Redis connection failed: {e}. Using in-memory fallback.")
            self.is_connected = False
            self._fallback_cache = {}

    def _make_key(self, prefix: str, identifier: str) -> str:
        """Create a cache key."""
        return f"originbrain:{prefix}:{identifier}"

    def _serialize(self, value: Any) -> bytes:
        """Serialize value for caching."""
        try:
            # Use pickle for complex objects, JSON for simple ones
            if isinstance(value, (dict, list, str, int, float, bool)) or value is None:
                return json.dumps(value).encode('utf-8')
            else:
                return pickle.dumps(value)
        except Exception as e:
            logger.error(f"Failed to serialize cache value: {e}")
            raise

    def _deserialize(self, value: bytes) -> Any:
        """Deserialize cached value."""
        try:
            # Try JSON first, then pickle
            try:
                return json.loads(value.decode('utf-8'))
            except (json.JSONDecodeError, UnicodeDecodeError):
                return pickle.loads(value)
        except Exception as e:
            logger.error(f"Failed to deserialize cache value: {e}")
            return None

    def get(self, prefix: str, identifier: str) -> Optional[Any]:
        """
        Get value from cache.

        Args:
            prefix: Cache prefix (e.g., 'artifact', 'search_result')
            identifier: Unique identifier for the value

        Returns:
            Cached value or None
        """
        key = self._make_key(prefix, identifier)

        if self.is_connected:
            try:
                value = self.redis_client.get(key)
                if value is not None:
                    return self._deserialize(value)
            except Exception as e:
                logger.error(f"Failed to get from cache: {e}")
                return None
        else:
            # Fallback to in-memory cache
            return self._fallback_cache.get(key)

    def set(self, prefix: str, identifier: str, value: Any, ttl: int = None) -> bool:
        """
        Set value in cache.

        Args:
            prefix: Cache prefix
            identifier: Unique identifier
            value: Value to cache
            ttl: Time to live in seconds (default: 1 hour)

        Returns:
            True if successful
        """
        key = self._make_key(prefix, identifier)
        ttl = ttl or 3600  # Default 1 hour

        try:
            serialized = self._serialize(value)

            if self.is_connected:
                self.redis_client.setex(key, ttl, serialized)
            else:
                # Fallback to in-memory cache (no TTL)
                self._fallback_cache[key] = value
                # Simple TTL cleanup for fallback
                if not hasattr(self, '_fallback_timestamps'):
                    self._fallback_timestamps = {}
                self._fallback_timestamps[key] = datetime.now() + timedelta(seconds=ttl)

            return True
        except Exception as e:
            logger.error(f"Failed to set cache: {e}")
            return False

    def delete(self, prefix: str, identifier: str) -> bool:
        """
        Delete value from cache.

        Args:
            prefix: Cache prefix
            identifier: Unique identifier

        Returns:
            True if deleted
        """
        key = self._make_key(prefix, identifier)

        if self.is_connected:
            try:
                self.redis_client.delete(key)
                return True
            except Exception as e:
                logger.error(f"Failed to delete from cache: {e}")
                return False
        else:
            # Fallback
            self._fallback_cache.pop(key, None)
            if hasattr(self, '_fallback_timestamps'):
                self._fallback_timestamps.pop(key, None)
            return True

    def invalidate_pattern(self, pattern: str) -> int:
        """
        Invalidate cache entries matching pattern.

        Args:
            pattern: Pattern to match (e.g., 'artifact:*')

        Returns:
            Number of keys deleted
        """
        full_pattern = f"originbrain:{pattern}"

        if self.is_connected:
            try:
                keys = self.redis_client.keys(full_pattern)
                if keys:
                    return self.redis_client.delete(*keys)
                return 0
            except Exception as e:
                logger.error(f"Failed to invalidate pattern: {e}")
                return 0
        else:
            # Fallback - simple pattern matching
            count = 0
            keys_to_delete = []
            for key in self._fallback_cache.keys():
                if pattern.replace('*', '') in key:
                    keys_to_delete.append(key)

            for key in keys_to_delete:
                self._fallback_cache.pop(key, None)
                if hasattr(self, '_fallback_timestamps'):
                    self._fallback_timestamps.pop(key, None)
                count += 1

            return count

    def clear_all(self) -> bool:
        """Clear all OriginBrain cache entries."""
        if self.is_connected:
            try:
                keys = self.redis_client.keys("originbrain:*")
                if keys:
                    self.redis_client.delete(*keys)
                return True
            except Exception as e:
                logger.error(f"Failed to clear cache: {e}")
                return False
        else:
            self._fallback_cache.clear()
            if hasattr(self, '_fallback_timestamps'):
                self._fallback_timestamps.clear()
            return True

    def get_stats(self) -> dict:
        """Get cache statistics."""
        if self.is_connected:
            try:
                info = self.redis_client.info('memory')
                keys = self.redis_client.dbsize()
                return {
                    'connected': True,
                    'total_keys': keys,
                    'memory_used': info.get('used_memory_human', 'N/A'),
                    'memory_peak': info.get('used_memory_peak_human', 'N/A')
                }
            except Exception as e:
                logger.error(f"Failed to get cache stats: {e}")
                return {'connected': False, 'error': str(e)}
        else:
            return {
                'connected': False,
                'fallback_keys': len(self._fallback_cache),
                'message': 'Using in-memory fallback'
            }

    # --- Specific cache methods ---

    def cache_artifact(self, artifact_id: str, artifact_data: dict, ttl: int = 3600):
        """Cache an artifact with its data."""
        return self.set('artifact', artifact_id, artifact_data, ttl)

    def get_cached_artifact(self, artifact_id: str) -> Optional[dict]:
        """Get cached artifact."""
        return self.get('artifact', artifact_id)

    def cache_search_result(self, query_hash: str, results: list, ttl: int = 1800):
        """Cache search results for 30 minutes."""
        return self.set('search', query_hash, results, ttl)

    def get_cached_search_result(self, query_hash: str) -> Optional[list]:
        """Get cached search results."""
        return self.get('search', query_hash)

    def cache_recommendations(self, user_id: str, recommendations: list, ttl: int = 3600):
        """Cache user recommendations."""
        return self.set('recommendations', user_id, recommendations, ttl)

    def get_cached_recommendations(self, user_id: str) -> Optional[list]:
        """Get cached recommendations."""
        return self.get('recommendations', user_id)

    def cache_insights(self, key: str, insights: dict, ttl: int = 7200):
        """Cache insights data for 2 hours."""
        return self.set('insights', key, insights, ttl)

    def get_cached_insights(self, key: str) -> Optional[dict]:
        """Get cached insights."""
        return self.get('insights', key)

    def cache_consumption_queue(self, user_id: str, queue: list, ttl: int = 300):
        """Cache consumption queue for 5 minutes."""
        return self.set('queue', user_id, queue, ttl)

    def get_cached_consumption_queue(self, user_id: str) -> Optional[list]:
        """Get cached consumption queue."""
        return self.get('queue', user_id)

    def invalidate_artifact_cache(self, artifact_id: str = None):
        """
        Invalidate artifact cache.

        Args:
            artifact_id: Specific artifact ID, or None for all artifacts
        """
        if artifact_id:
            return self.delete('artifact', artifact_id)
        else:
            return self.invalidate_pattern('artifact:*')

    def invalidate_user_cache(self, user_id: str):
        """Invalidate all cache entries for a user."""
        patterns = [
            f'recommendations:{user_id}',
            f'queue:{user_id}'
        ]
        count = 0
        for pattern in patterns:
            count += self.invalidate_pattern(pattern)
        return count

    def warm_cache(self, artifact_ids: List[str] = None):
        """
        Warm cache with frequently accessed data.

        Args:
            artifact_ids: List of artifact IDs to cache (optional)
        """
        if not artifact_ids:
            # Get recently accessed artifacts
            try:
                artifacts = self.db.get_artifacts_with_extended(limit=50)
                artifact_ids = [a['id'] for a in artifacts]
            except Exception as e:
                logger.error(f"Failed to get artifacts for cache warming: {e}")
                return

        logger.info(f"Warming cache with {len(artifact_ids)} artifacts")

        for artifact_id in artifact_ids:
            try:
                artifact = self.db.get_artifact_extended(artifact_id)
                if artifact:
                    self.cache_artifact(artifact_id, artifact, ttl=7200)  # 2 hours
            except Exception as e:
                logger.error(f"Failed to warm cache for artifact {artifact_id}: {e}")
                continue

        logger.info("Cache warming completed")