from datetime import datetime, timedelta, timezone

from fastapi.testclient import TestClient

from app.auth import create_access_token
from app.config import settings
from app.main import app
from app.repository import get_users_repo
from tests.test_auth import USER, make_init_data

client = TestClient(app)


def login(init_data: str) -> dict:
    response = client.post("/api/v1/auth/telegram", json={"init_data": init_data})
    assert response.status_code == 200
    return response.json()


def auth_header(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def test_login_creates_user_and_me_returns_demo(users_repo):
    body = login(make_init_data())
    assert body["token_type"] == "bearer"
    assert body["user"]["id"] == USER["id"]
    assert users_repo.get(USER["id"]) is not None

    me = client.get("/api/v1/me", headers=auth_header(body["access_token"]))
    assert me.status_code == 200
    data = me.json()
    assert data["id"] == USER["id"]
    assert data["first_name"] == "Тест"
    assert data["access"] == {"status": "demo", "until": None}


def test_me_shows_full_access(users_repo):
    body = login(make_init_data())
    until = datetime.now(timezone.utc) + timedelta(days=30)
    users_repo.set_access_until(USER["id"], until.isoformat())

    me = client.get("/api/v1/me", headers=auth_header(body["access_token"])).json()
    assert me["access"]["status"] == "full"
    assert me["access"]["until"] is not None


def test_me_shows_days_to_exam(monkeypatch):
    exam = (datetime.now(timezone.utc) + timedelta(days=10)).date().isoformat()
    monkeypatch.setattr(settings, "exam_date", exam)
    body = login(make_init_data())
    me = client.get("/api/v1/me", headers=auth_header(body["access_token"])).json()
    assert me["exam_date"] == exam
    assert me["days_to_exam"] in (9, 10, 11)  # зависит от часового пояса


def test_referral_is_saved_for_new_user(users_repo):
    login(make_init_data())  # пригласивший
    friend = {"id": 777, "first_name": "Друг"}
    login(make_init_data(user=friend, start_param=f"ref_{USER['id']}"))
    assert users_repo.get(777)["referred_by"] == USER["id"]


def test_self_and_unknown_referrer_are_ignored(users_repo):
    login(make_init_data(start_param=f"ref_{USER['id']}"))
    assert users_repo.get(USER["id"])["referred_by"] is None

    other = {"id": 888, "first_name": "X"}
    login(make_init_data(user=other, start_param="ref_99999"))
    assert users_repo.get(888)["referred_by"] is None


def test_referral_is_not_overwritten_on_next_login(users_repo):
    login(make_init_data())
    friend = {"id": 777, "first_name": "Друг"}
    login(make_init_data(user=friend, start_param=f"ref_{USER['id']}"))
    login(make_init_data(user=friend, start_param="ref_555"))
    assert users_repo.get(777)["referred_by"] == USER["id"]


def test_login_with_bad_signature_returns_401():
    response = client.post(
        "/api/v1/auth/telegram", json={"init_data": make_init_data(bot_token="1:other")}
    )
    assert response.status_code == 401
    assert response.json()["code"] == "invalid_init_data"


def test_me_without_token_returns_401():
    response = client.get("/api/v1/me")
    assert response.status_code == 401
    assert response.json()["code"] == "unauthorized"


def test_me_with_garbage_token_returns_401():
    response = client.get("/api/v1/me", headers={"Authorization": "Bearer abc.def.ghi"})
    assert response.status_code == 401
    assert response.json()["code"] == "invalid_token"


def test_me_for_user_missing_in_db_returns_401():
    token = create_access_token(424242, settings.jwt_secret, 5)
    response = client.get("/api/v1/me", headers=auth_header(token))
    assert response.status_code == 401
    assert response.json()["code"] == "user_not_found"


def test_dev_login_creates_test_user_with_negative_id(users_repo):
    response = client.post(
        "/api/v1/auth/dev", json={"telegram_id": -5, "first_name": "Dev"}
    )
    assert response.status_code == 200
    assert users_repo.get(-5) is not None
    me = client.get(
        "/api/v1/me", headers=auth_header(response.json()["access_token"])
    )
    assert me.status_code == 200


def test_dev_login_with_unknown_positive_id_returns_404(users_repo):
    response = client.post("/api/v1/auth/dev", json={"telegram_id": 123})
    assert response.status_code == 404
    assert response.json()["code"] == "user_not_found"
    assert users_repo.get(123) is None  # запись не создана


def test_dev_login_with_existing_positive_id_works():
    login(make_init_data())
    response = client.post("/api/v1/auth/dev", json={"telegram_id": USER["id"]})
    assert response.status_code == 200


def test_dev_login_is_disabled_in_prod(monkeypatch):
    monkeypatch.setattr(settings, "app_env", "prod")
    response = client.post("/api/v1/auth/dev", json={"telegram_id": -1})
    assert response.status_code == 404
    assert response.json()["code"] == "not_found"


def test_invalid_request_body_returns_validation_error():
    response = client.post("/api/v1/auth/telegram", json={})
    assert response.status_code == 422
    assert response.json()["code"] == "validation_error"


class BrokenRepo:
    def get(self, user_id):
        raise RuntimeError("db down")

    def upsert_telegram_user(self, tg_user, referred_by):
        raise RuntimeError("db down")


def test_login_when_db_is_down_returns_503():
    app.dependency_overrides[get_users_repo] = lambda: BrokenRepo()
    response = client.post("/api/v1/auth/telegram", json={"init_data": make_init_data()})
    assert response.status_code == 503
    assert response.json()["code"] == "db_unavailable"