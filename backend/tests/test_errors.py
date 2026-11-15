from fastapi.testclient import TestClient

from app.main import app


@app.get("/_test/boom")
def _boom():
    raise RuntimeError("boom")


def test_unhandled_error_is_returned_in_common_format():
    client = TestClient(app, raise_server_exceptions=False)
    response = client.get("/_test/boom")
    assert response.status_code == 500
    body = response.json()
    assert body["code"] == "internal_error"
    assert "request_id" in body