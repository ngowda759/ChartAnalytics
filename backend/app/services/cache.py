"""Lightweight in-process TTL cache for expensive, deterministic computations.

The screener engine's synthetic OHLC is seeded per symbol + hour (see
``screener_engine._seed_for``), so any derived analysis (decision signals,
agent analysis) is stable within an hour. Caching those results for a short
window avoids regenerating 6 templates x 30 symbols (or the full agent
pipeline for 30 symbols) on every dashboard refresh, without introducing a
Redis/Celery dependency.

Thread-safe enough for the single FastAPI event loop; not a distributed cache.
"""

from __future__ import annotations

import threading
import time
from typing import Callable, Dict, Generic, Optional, Tuple, TypeVar

K = TypeVar("K")
V = TypeVar("V")


class TTLCache(Generic[K, V]):
    """A minimal thread-safe TTL cache. Entries expire after ``ttl`` seconds."""

    def __init__(self, ttl: float):
        self._ttl = ttl
        self._store: Dict[K, Tuple[V, float]] = {}
        self._lock = threading.Lock()

    def get(self, key: K) -> Optional[V]:
        with self._lock:
            entry = self._store.get(key)
            if entry is None:
                return None
            value, expires_at = entry
            if time.monotonic() > expires_at:
                self._store.pop(key, None)
                return None
            return value

    def set(self, key: K, value: V) -> None:
        with self._lock:
            self._store[key] = (value, time.monotonic() + self._ttl)

    def clear(self) -> None:
        with self._lock:
            self._store.clear()

    def __len__(self) -> int:
        return len(self._store)


def cached(ttl: float, cache: Optional[TTLCache] = None) -> Callable:
    """Decorator: memoize a function's result for ``ttl`` seconds.

    A shared ``TTLCache`` can be passed to share state across calls; otherwise a
    private cache is created per decorated function. The cache key is built from
    all positional + keyword arguments.
    """

    def decorator(fn: Callable) -> Callable:
        store = cache or TTLCache(ttl)

        def _key(args, kwargs):
            return (args, tuple(sorted(kwargs.items())))

        def wrapper(*args, **kwargs):
            k = _key(args, kwargs)
            hit = store.get(k)
            if hit is not None:
                return hit
            result = fn(*args, **kwargs)
            store.set(k, result)
            return result

        wrapper._cache = store  # type: ignore[attr-defined]
        return wrapper

    return decorator
