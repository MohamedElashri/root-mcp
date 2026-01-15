"""Caching utilities shared between core and extended modes."""

from collections import OrderedDict
from typing import Generic, TypeVar

T = TypeVar("T")


class LRUCache(Generic[T]):
    """Generic LRU cache implementation."""

    def __init__(self, max_size: int):
        """
        Initialize LRU cache.

        Args:
            max_size: Maximum number of items to cache
        """
        self.max_size = max_size
        self._cache: OrderedDict[str, T] = OrderedDict()

    def get(self, key: str) -> T | None:
        """
        Get item from cache.

        Args:
            key: Cache key

        Returns:
            Cached item or None if not found
        """
        if key in self._cache:
            self._cache.move_to_end(key)
            return self._cache[key]
        return None

    def put(self, key: str, value: T) -> None:
        """
        Add item to cache.

        Args:
            key: Cache key
            value: Item to cache
        """
        if key in self._cache:
            self._cache.move_to_end(key)
            self._cache[key] = value
            return

        self._cache[key] = value

        if len(self._cache) > self.max_size:
            self._cache.popitem(last=False)

    def clear(self) -> None:
        """Clear the cache."""
        self._cache.clear()

    def size(self) -> int:
        """Get current cache size."""
        return len(self._cache)
