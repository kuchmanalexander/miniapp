import threading
import time
from collections import deque
from typing import Callable

from fastapi import Request

from app.config import settings
from app.errors import ApiError


class RateLimiter:
    """Простой ограничитель: не больше `limit` обращений за `window_seconds` секунд на ключ."""

    def __init__(
        self,
        limit: int,
        window_seconds: int,
        clock: Callable[[], float] = time.monotonic,
    ):
        self.limit = limit
        self.window = window_seconds
        self._clock = clock
        self._hits: dict[str, deque] = {}
        self._lock = threading.Lock()

    def check(self, key: str) -> int | None:
        """None, если можно. Иначе число секунд, через которое можно повторить."""
        now = self._clock()
        with self._lock:
            hits = self._hits.setdefault(key, deque())
            while hits and now - hits[0] > self.window:
                hits.popleft()
            if len(hits) >= self.limit:
                return max(1, int(self.window - (now - hits[0])) + 1)
            hits.append(now)
            if len(self._hits) > 10000:
                self._cleanup(now)
            return None

    def _cleanup(self, now: float) -> None:
        for key in [k for k, v in self._hits.items() if not v or now - v[-1] > self.window]:
            del self._hits[key]

    def reset(self) -> None:
        with self._lock:
            self._hits.clear()


def client_ip(request: Request) -> str:
    """Адрес клиента. За прокси (TRUST_PROXY=true) берём первый адрес из X-Forwarded-For."""
    if settings.trust_proxy:
        forwarded = request.headers.get("x-forwarded-for")
        if forwarded:
            return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


auth_limiter = RateLimiter(settings.auth_rate_limit, 60)


def limit_auth(request: Request) -> None:
    """Зависимость для адресов входа: ограничивает частоту попыток."""
    retry_after = auth_limiter.check(client_ip(request))
    if retry_after is not None:
        raise ApiError(
            429,
            "rate_limited",
            f"Слишком много попыток. Повторите через {retry_after} сек.",
            headers={"Retry-After": str(retry_after)},
        )