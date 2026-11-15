from fastapi.testclient import TestClient

from app.config import settings
from app.main import app

client = TestClient(app)


def test_dev_page_available_in_dev():
    response = client.get("/dev/webapp")
    assert response.status_code == 200
    assert "telegram-web-app.js" in response.text


def test_dev_page_hidden_in_prod(monkeypatch):
    monkeypatch.setattr(settings, "app_env", "prod")
    assert client.get("/dev/webapp").status_code == 404


def test_dev_login_can_be_switched_off(monkeypatch):
    monkeypatch.setattr(settings, "dev_login_enabled", False)
    response = client.post("/api/v1/auth/dev", json={"telegram_id": -1})
    assert response.status_code == 404