"""Simple in-process sliding-window rate limiter for public auth endpoints."""

from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timedelta, timezone
from threading import Lock


class SlidingWindowRateLimiter:
    def __init__(self, *, max_requests: int, window_seconds: int = 60) -> None:
        self.max_requests = max_requests
        self.window = timedelta(seconds=window_seconds)
        self._hits: dict[str, list[datetime]] = defaultdict(list)
        self._lock = Lock()

    def allow(self, key: str) -> bool:
        now = datetime.now(timezone.utc)
        cutoff = now - self.window
        with self._lock:
            hits = [stamp for stamp in self._hits[key] if stamp > cutoff]
            if len(hits) >= self.max_requests:
                self._hits[key] = hits
                return False
            hits.append(now)
            self._hits[key] = hits
            return True


check_email_limiter = SlidingWindowRateLimiter(max_requests=15, window_seconds=60)
social_auth_limiter = SlidingWindowRateLimiter(max_requests=20, window_seconds=60)
