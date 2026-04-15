"""
Redis-based runtime infrastructure per runtime-and-state.md.

Provides:
  • EventDeduplicator — SETNX(msg_id) with 24h TTL
  • AggregationWindow — 3-second sliding window
  • SuspendQueue — stores user interruptions during dispatch
  • OrderingGuard — create_ts >= last_processed_ts check

Uses an abstraction layer so tests can use InMemoryStore
while production uses real Redis.
"""

from __future__ import annotations

import time
from typing import Any, Dict, List, Optional, Protocol


# ---------------------------------------------------------------------- #
#  Store abstraction                                                      #
# ---------------------------------------------------------------------- #

class KeyValueStore(Protocol):
    """Abstraction over Redis or in-memory for testing."""

    def setnx(self, key: str, value: str, ttl_seconds: int = 0) -> bool:
        """Set key if not exists. Returns True if set, False if already existed."""
        ...

    def get(self, key: str) -> Optional[str]:
        ...

    def set(self, key: str, value: str, ttl_seconds: int = 0) -> None:
        ...

    def rpush(self, key: str, value: str) -> None:
        ...

    def lrange(self, key: str, start: int, end: int) -> List[str]:
        ...

    def delete(self, key: str) -> None:
        ...


class InMemoryStore:
    """In-memory implementation for testing and local dev."""

    def __init__(self) -> None:
        self._data: Dict[str, Any] = {}
        self._expires: Dict[str, float] = {}
        self._lists: Dict[str, List[str]] = {}

    def _is_expired(self, key: str) -> bool:
        if key in self._expires and time.time() > self._expires[key]:
            self._data.pop(key, None)
            self._expires.pop(key, None)
            return True
        return False

    def setnx(self, key: str, value: str, ttl_seconds: int = 0) -> bool:
        self._is_expired(key)
        if key in self._data:
            return False
        self._data[key] = value
        if ttl_seconds > 0:
            self._expires[key] = time.time() + ttl_seconds
        return True

    def get(self, key: str) -> Optional[str]:
        self._is_expired(key)
        return self._data.get(key)

    def set(self, key: str, value: str, ttl_seconds: int = 0) -> None:
        self._data[key] = value
        if ttl_seconds > 0:
            self._expires[key] = time.time() + ttl_seconds
        elif key in self._expires:
            del self._expires[key]

    def rpush(self, key: str, value: str) -> None:
        self._lists.setdefault(key, []).append(value)

    def lrange(self, key: str, start: int, end: int) -> List[str]:
        items = self._lists.get(key, [])
        if end == -1:
            return items[start:]
        return items[start : end + 1]

    def delete(self, key: str) -> None:
        self._data.pop(key, None)
        self._expires.pop(key, None)
        self._lists.pop(key, None)


class RedisStore:
    """Production Redis implementation of KeyValueStore.

    Requires the `redis` package: pip install redis>=5.0.0
    """

    def __init__(self, url: str) -> None:
        import redis as _redis

        self._client = _redis.Redis.from_url(url, decode_responses=True)

    def setnx(self, key: str, value: str, ttl_seconds: int = 0) -> bool:
        if ttl_seconds > 0:
            from datetime import timedelta

            return bool(self._client.set(key, value, nx=True, ex=timedelta(seconds=ttl_seconds)))
        return bool(self._client.set(key, value, nx=True))

    def get(self, key: str) -> Optional[str]:
        val = self._client.get(key)
        return val if val is not None else None

    def set(self, key: str, value: str, ttl_seconds: int = 0) -> None:
        if ttl_seconds > 0:
            from datetime import timedelta

            self._client.set(key, value, ex=timedelta(seconds=ttl_seconds))
        else:
            self._client.set(key, value)

    def rpush(self, key: str, value: str) -> None:
        self._client.rpush(key, value)

    def lrange(self, key: str, start: int, end: int) -> List[str]:
        return list(self._client.lrange(key, start, end))

    def delete(self, key: str) -> None:
        self._client.delete(key)


def create_store(url: str = "") -> KeyValueStore:
    """Factory: returns RedisStore if URL is provided, InMemoryStore otherwise.

    Usage:
        store = create_store(os.getenv("REDIS_URL", ""))
    """
    if url:
        try:
            store = RedisStore(url)
            # Verify connectivity
            store.get("__ping__")
            return store
        except Exception:
            import logging

            logging.getLogger(__name__).warning(
                "Redis connection failed, falling back to InMemoryStore"
            )
    return InMemoryStore()


# ---------------------------------------------------------------------- #
#  Event Deduplicator                                                     #
# ---------------------------------------------------------------------- #

MSG_ID_TTL = 86400  # 24 hours


class EventDeduplicator:
    """Deduplicate inbound webhook events with SETNX keyed by msg_id.

    Per runtime-and-state.md:
    - Use Redis SETNX(msg_id) with 24h TTL for webhook deduplication.
    - Return HTTP 200 on duplicate delivery and stop processing.
    """

    def __init__(self, store: KeyValueStore) -> None:
        self.store = store

    def is_duplicate(self, msg_id: str) -> bool:
        """Returns True if this msg_id has already been processed."""
        if not msg_id:
            return False
        key = f"dedup:{msg_id}"
        was_new = self.store.setnx(key, "1", ttl_seconds=MSG_ID_TTL)
        return not was_new


# ---------------------------------------------------------------------- #
#  Aggregation Window                                                     #
# ---------------------------------------------------------------------- #

AGGREGATION_WINDOW_SECONDS = 3.0


class AggregationWindow:
    """3-second sliding aggregation window.

    Per runtime-and-state.md:
    - Keep a 3-second sliding aggregation window for related inbound messages.
    - Once the window closes, any new arrival is a new event.
    """

    def __init__(self, store: KeyValueStore, window_seconds: float = AGGREGATION_WINDOW_SECONDS) -> None:
        self.store = store
        self.window_seconds = max(float(window_seconds), 0.0)

    def should_aggregate(self, conversation_id: str, timestamp: float) -> bool:
        """Returns True if this message falls within the current aggregation window."""
        key = f"aggwin:{conversation_id}"
        existing = self.store.get(key)
        if existing is None:
            self.store.set(key, str(timestamp), ttl_seconds=max(1, int(self.window_seconds) + 1))
            return False

        window_start = float(existing)
        if timestamp - window_start <= self.window_seconds:
            return True
        else:
            # Window closed, start new window
            self.store.set(key, str(timestamp), ttl_seconds=max(1, int(self.window_seconds) + 1))
            return False


# ---------------------------------------------------------------------- #
#  Suspend Queue                                                          #
# ---------------------------------------------------------------------- #

class SuspendQueue:
    """Stores user interruptions during dispatching state.

    Per runtime-and-state.md:
    - While state is dispatching, store any user interruption in suspend storage.
    - Do not drop those messages.
    - After the current task completes, ask whether to re-evaluate.
    """

    def __init__(self, store: KeyValueStore) -> None:
        self.store = store

    def enqueue(self, session_id: str, message: str) -> None:
        """Store a suspended message for later re-evaluation."""
        key = f"suspend:{session_id}"
        self.store.rpush(key, message)

    def drain(self, session_id: str) -> List[str]:
        """Retrieve and remove all suspended messages."""
        key = f"suspend:{session_id}"
        messages = self.store.lrange(key, 0, -1)
        self.store.delete(key)
        return messages

    def has_pending(self, session_id: str) -> bool:
        """Check if there are suspended messages."""
        key = f"suspend:{session_id}"
        return len(self.store.lrange(key, 0, -1)) > 0


# ---------------------------------------------------------------------- #
#  Ordering Guard                                                         #
# ---------------------------------------------------------------------- #

class OrderingGuard:
    """Timestamp ordering guard.

    Per runtime-and-state.md:
    - Only allow state transitions from events where create_ts >= last_processed_ts.
    - Use this to block stale or reordered events from mutating workflow state.
    """

    def __init__(self, store: KeyValueStore) -> None:
        self.store = store

    def is_stale(self, session_id: str, create_ts: float) -> bool:
        """Returns True if this event is stale (older than last processed)."""
        key = f"order:{session_id}"
        last = self.store.get(key)
        if last is not None and create_ts < float(last):
            return True
        self.store.set(key, str(create_ts))
        return False
