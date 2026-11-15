import hashlib
import hmac
import json
import time
from urllib.parse import parse_qsl

import jwt


class InitDataError(Exception):
    """Данные initData не прошли проверку."""


def validate_init_data(
    init_data: str,
    bot_token: str,
    max_age_seconds: int = 86400,
    now: float | None = None,
) -> dict:
    """Проверяет подпись и срок действия initData от Telegram Mini App.

    Возвращает {"user": {...}, "auth_date": int, "start_param": str | None}.
    При любой проблеме выбрасывает InitDataError.
    """
    if not init_data:
        raise InitDataError("Пустые данные входа")
    if not bot_token:
        raise InitDataError("Токен бота не настроен")

    pairs = dict(parse_qsl(init_data, keep_blank_values=True))
    received_hash = pairs.pop("hash", None)
    if not received_hash:
        raise InitDataError("В данных нет подписи")

    # Строка для проверки: все поля кроме hash, по алфавиту, формат ключ=значение
    data_check_string = "\n".join(f"{k}={v}" for k, v in sorted(pairs.items()))

    secret_key = hmac.new(b"WebAppData", bot_token.encode(), hashlib.sha256).digest()
    expected_hash = hmac.new(
        secret_key, data_check_string.encode(), hashlib.sha256
    ).hexdigest()

    if not hmac.compare_digest(expected_hash, received_hash):
        raise InitDataError("Неверная подпись")

    try:
        auth_date = int(pairs["auth_date"])
    except (KeyError, ValueError):
        raise InitDataError("Некорректная дата входа")

    current = now if now is not None else time.time()
    if current - auth_date > max_age_seconds:
        raise InitDataError("Данные входа устарели")
    if auth_date - current > 300:
        raise InitDataError("Дата входа из будущего")

    try:
        user = json.loads(pairs["user"])
    except (KeyError, ValueError):
        raise InitDataError("В данных нет пользователя")
    if not isinstance(user, dict) or "id" not in user:
        raise InitDataError("В данных нет пользователя")

    return {
        "user": user,
        "auth_date": auth_date,
        "start_param": pairs.get("start_param"),
    }


def create_access_token(user_id: int, secret: str, ttl_minutes: int) -> str:
    """Создаёт JWT-токен на заданное число минут."""
    now = int(time.time())
    payload = {"sub": str(user_id), "iat": now, "exp": now + ttl_minutes * 60}
    return jwt.encode(payload, secret, algorithm="HS256")


def decode_access_token(token: str, secret: str) -> int:
    """Возвращает ID пользователя из токена. Бросает jwt.PyJWTError, если токен плохой."""
    payload = jwt.decode(token, secret, algorithms=["HS256"])
    return int(payload["sub"])