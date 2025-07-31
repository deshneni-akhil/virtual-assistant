import threading
import redis
import json
import os
from urllib.parse import urlparse


class RedisCache:
    """Redis-based cache using Azure Redis connection string."""

    def __init__(self, connection_string):
        if not connection_string:
            raise ValueError("Redis connection string is required")
        self.client = self._connect_redis(connection_string)

    def _connect_redis(self, connection_string):
        """Parses the connection string and establishes a Redis connection."""
        try:
            parsed_url = urlparse(connection_string)
            host, port, password = (
                parsed_url[0],
                parsed_url[2][:4],
                parsed_url[2][14:].split(",")[0],
            )
            return redis.StrictRedis(
                host=host,
                port=port,
                password=password,
                ssl=True,  # Azure Redis uses SSL/TLS
                decode_responses=True,
            )
        except Exception as e:
            raise ConnectionError(f"Failed to connect to Redis: {str(e)}")

    def get(self, key):
        value = self.client.get(key)
        try:
            return json.loads(value) if value else None
        except json.JSONDecodeError:
            return value

    def set(self, key, value, ex=3600):
        """Set a value in Redis with an optional expiration time (in seconds)."""
        existing_value = self.get(key)
        value_to_store = None
        if isinstance(existing_value, dict) and isinstance(value, dict):
            existing_value.update(value)
            value_to_store = json.dumps(existing_value)
        elif isinstance(existing_value, list):
            existing_value.append(value)
            value_to_store = json.dumps(existing_value)
        else:
            value_to_store = json.dumps(value)
        self.client.set(key, value_to_store, ex=ex)

    def delete(self, key):
        self.client.delete(key)

    def size(self):
        return self.client.dbsize()


# Global cache instance
_cache = None
_lock = threading.Lock()


def get_cache():
    """Returns a singleton Redis cache instance."""
    global _cache
    if _cache is None:
        with _lock:
            if _cache is None:
                redis_connection_string = os.getenv("AZURE_REDIS_CONNECTION_STRING")
                _cache = RedisCache(redis_connection_string)
    return _cache


# testing the cache
if __name__ == "__main__":
    try:
        cache = get_cache()
        print("Using Redis Cache")
        cache.set("key1", "value1")
        print(cache.get("key1"))  # Output: value1
        cache.set("key2", {"a": 1, "b": 2})
        print(cache.get("key2"))  # Output: {'a': 1, 'b': 2}
        cache.set("key2", {"c": 1, "d": 2})
        print(cache.get("key2"))  # Output: {'a': 1, 'b': 2, 'c': 1}
    except Exception as e:
        print(f"Error initializing Redis cache: {str(e)}")
