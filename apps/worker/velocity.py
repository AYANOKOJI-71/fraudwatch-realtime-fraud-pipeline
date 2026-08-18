"""Short-window velocity feature stores with a Redis-ready protocol."""

from __future__ import annotations

from collections import defaultdict, deque
from datetime import datetime, timedelta


class InMemoryVelocityStore:
    def __init__(self, window: timedelta = timedelta(minutes=5)) -> None:
        self.window = window
        self._timestamps: dict[str, deque[datetime]] = defaultdict(deque)

    def record_and_count(self, account_token: str, occurred_at: datetime) -> int:
        timestamps = self._timestamps[account_token]
        threshold = occurred_at - self.window
        while timestamps and timestamps[0] < threshold:
            timestamps.popleft()
        timestamps.append(occurred_at)
        return len(timestamps)


class RedisVelocityStore:
    """Redis implementation used by the container topology; imported lazily for local demo mode."""

    def __init__(self, client: object, window_seconds: int = 300) -> None:
        self.client = client
        self.window_seconds = window_seconds

    def record_and_count(self, account_token: str, occurred_at: datetime) -> int:
        key = f"fraudwatch:velocity:{account_token}"
        score = occurred_at.timestamp()
        pipe = self.client.pipeline()
        pipe.zremrangebyscore(key, 0, score - self.window_seconds)
        pipe.zadd(key, {f"{score}:{account_token}": score})
        pipe.zcard(key)
        pipe.expire(key, self.window_seconds + 15)
        results = pipe.execute()
        return int(results[2])
