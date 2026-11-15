from datetime import datetime, timedelta, timezone

from fastapi import Depends
from fastapi.testclient import TestClient

from app.dependencies import require_full_access
from app.main import app
from tests.test_auth import USER, make_init_data


@app.get("/_test/premium")
def _premium(user: dict = Depends(require_full_access)):
    return {"ok": True}


client = TestClient(app)


def _login_token() -> str:
    response = client.post("/api/v1/auth/telegram", json={"init_data": make_init_data()})
    return response.json()["access_token"]


def test_demo_user_gets_403(users_repo):
    token = _login_token()
    response = client.get("/_test/premium", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 403
    assert response.json()["code"] == "access_required"


def test_full_user_passes(users_repo):
    token = _login_token()
    until = datetime.now(timezone.utc) + timedelta(days=1)
    users_repo.set_access_until(USER["id"], until.isoformat())
    response = client.get("/_test/premium", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 200