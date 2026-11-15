from fastapi.testclient import TestClient

from app.main import app
from app.ratelimit import RateLimiter, auth_limiter


def test_limiter_blocks_after_limit():
    limiter = RateLimiter(limit=2, window_seconds=60)
    assert limiter.check("a") is None
    assert limiter.check("a") is None
    assert limiter.check("a") is not None
    assert limiter.check("b") is None  # другой адрес не затронут


def test_limiter_window_expires():
    now = [1000.0]
    limiter = RateLimiter(limit=1, window_seconds=10, clock=lambda: now[0])
    assert limiter.check("a") is None
    assert limiter.check("a") is not None
    now[0] += 11
    assert limiter.check("a") is None


def test_login_is_rate_limited(monkeypatch):
    monkeypatch.setattr(auth_limiter, "limit", 2)
    client = TestClient(app)
    for _ in range(2):
        ok = client.post("/api/v1/auth/dev", json={"telegram_id": -1})
        assert ok.status_code == 200

    blocked = client.post("/api/v1/auth/dev", json={"telegram_id": -1})
    assert blocked.status_code == 429
    assert blocked.json()["code"] == "rate_limited"
    assert "retry-after" in blocked.headers