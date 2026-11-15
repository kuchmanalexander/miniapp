import hashlib
import hmac
import json
import time
from urllib.parse import urlencode

import jwt
import pytest

from app.auth import (
    InitDataError,
    create_access_token,
    decode_access_token,
    validate_init_data,
)

BOT_TOKEN = "123456:TEST_BOT_TOKEN"
USER = {"id": 5129900191, "first_name": "Тест", "username": "tester"}


def make_init_data(
    user=USER, bot_token=BOT_TOKEN, auth_date=None, with_hash=True, start_param=None
) -> str:
    """Собирает initData и подписывает его так же, как это делает Telegram."""
    if auth_date is None:
        auth_date = int(time.time())
    fields = {
        "auth_date": str(auth_date),
        "query_id": "AAH-test",
        "user": json.dumps(user, separators=(",", ":"), ensure_ascii=False),
    }
    if start_param:
        fields["start_param"] = start_param
    data_check_string = "\n".join(f"{k}={v}" for k, v in sorted(fields.items()))
    secret = hmac.new(b"WebAppData", bot_token.encode(), hashlib.sha256).digest()
    if with_hash:
        fields["hash"] = hmac.new(
            secret, data_check_string.encode(), hashlib.sha256
        ).hexdigest()
    return urlencode(fields)


def test_valid_init_data():
    result = validate_init_data(make_init_data(), BOT_TOKEN)
    assert result["user"]["id"] == USER["id"]
    assert result["user"]["first_name"] == "Тест"


def test_wrong_bot_token_is_rejected():
    init_data = make_init_data(bot_token="999:ANOTHER_TOKEN")
    with pytest.raises(InitDataError):
        validate_init_data(init_data, BOT_TOKEN)


def test_tampered_data_is_rejected():
    init_data = make_init_data()
    # Меняем ID пользователя, не пересчитывая подпись
    tampered = init_data.replace("5129900191", "1111111111")
    assert tampered != init_data
    with pytest.raises(InitDataError):
        validate_init_data(tampered, BOT_TOKEN)


def test_missing_hash_is_rejected():
    with pytest.raises(InitDataError):
        validate_init_data(make_init_data(with_hash=False), BOT_TOKEN)


def test_expired_data_is_rejected():
    old = int(time.time()) - 90000  # больше суток назад
    with pytest.raises(InitDataError):
        validate_init_data(make_init_data(auth_date=old), BOT_TOKEN)


def test_future_date_is_rejected():
    future = int(time.time()) + 3600
    with pytest.raises(InitDataError):
        validate_init_data(make_init_data(auth_date=future), BOT_TOKEN)


def test_empty_data_and_empty_token_are_rejected():
    with pytest.raises(InitDataError):
        validate_init_data("", BOT_TOKEN)
    with pytest.raises(InitDataError):
        validate_init_data(make_init_data(), "")


def test_jwt_roundtrip():
    secret = "s" * 40
    token = create_access_token(42, secret, ttl_minutes=5)
    assert decode_access_token(token, secret) == 42


def test_jwt_wrong_secret_is_rejected():
    token = create_access_token(42, "s" * 40, ttl_minutes=5)
    with pytest.raises(jwt.PyJWTError):
        decode_access_token(token, "x" * 40)


def test_jwt_expired_is_rejected():
    secret = "s" * 40
    token = create_access_token(42, secret, ttl_minutes=-1)
    with pytest.raises(jwt.PyJWTError):
        decode_access_token(token, secret)