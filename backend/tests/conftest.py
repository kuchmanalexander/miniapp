import pytest

from app.config import settings
from app.main import app
from app.ratelimit import auth_limiter
from app.repository import InMemoryUsers, get_users_repo
from tests.test_auth import BOT_TOKEN


@pytest.fixture(autouse=True)
def test_settings(monkeypatch):
    """Тестовые настройки для всех тестов: не зависят от файла .env."""
    monkeypatch.setattr(settings, "bot_token", BOT_TOKEN)
    monkeypatch.setattr(settings, "dev_login_enabled", True)
    monkeypatch.setattr(settings, "jwt_secret", "t" * 40)
    monkeypatch.setattr(settings, "app_env", "dev")
    monkeypatch.setattr(settings, "admin_ids", "")
    monkeypatch.setattr(settings, "exam_date", "")


@pytest.fixture(autouse=True)
def users_repo():
    """Пустое хранилище пользователей в памяти для каждого теста (реальная база не трогается)."""
    repo = InMemoryUsers()
    app.dependency_overrides[get_users_repo] = lambda: repo
    yield repo
    app.dependency_overrides.pop(get_users_repo, None)


@pytest.fixture(autouse=True)
def reset_rate_limiter():
    """Каждый тест начинает с пустого счётчика попыток входа."""
    auth_limiter.reset()
    yield
    auth_limiter.reset()