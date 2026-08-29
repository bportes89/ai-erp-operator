import threading
import time
from collections import defaultdict, deque
from fastapi import HTTPException, Request
from app.config import get_settings


class RateLimiter:
    def __init__(self):
        self._hits: dict[str, deque] = defaultdict(deque)
        self._lock = threading.Lock()

    def allow(self, key: str, max_calls: int, window_seconds: int) -> bool:
        now = time.monotonic()
        with self._lock:
            queue = self._hits[key]
            while queue and now - queue[0] > window_seconds:
                queue.popleft()
            if len(queue) >= max_calls:
                return False
            queue.append(now)
            return True


_limiter = RateLimiter()


def rate_limit(max_calls: int, window_seconds: int):
    def dependency(request: Request) -> None:
        if not get_settings().rate_limit_enabled:
            return
        client = request.client.host if request.client else "unknown"
        scope = request.url.path
        if not _limiter.allow(f"{client}:{scope}", max_calls, window_seconds):
            raise HTTPException(429, "Muitas requisições, tente novamente em instantes")

    return dependency