import logging

import jwt
from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.access import compute_access
from app.auth import decode_access_token
from app.config import settings
from app.errors import ApiError
from app.repository import UsersRepo, db_unavailable, get_users_repo

logger = logging.getLogger("app.dependencies")

bearer_scheme = HTTPBearer(auto_error=False)


def get_current_user_id(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
) -> int:
    """Достаёт ID пользователя из токена. Без токена или с плохим токеном даёт ошибку 401."""
    if credentials is None:
        raise ApiError(401, "unauthorized", "Требуется вход")
    try:
        return decode_access_token(credentials.credentials, settings.jwt_secret)
    except (jwt.PyJWTError, KeyError, ValueError):
        raise ApiError(401, "invalid_token", "Токен недействителен или истёк")


def get_current_user(
    user_id: int = Depends(get_current_user_id),
    repo: UsersRepo = Depends(get_users_repo),
) -> dict:
    """Текущий пользователь из базы (строка таблицы users)."""
    try:
        row = repo.get(user_id)
    except Exception:
        logger.exception("Ошибка базы данных при получении пользователя")
        raise db_unavailable()
    if not row:
        raise ApiError(401, "user_not_found", "Пользователь не найден, войдите заново")
    return row


def require_full_access(user: dict = Depends(get_current_user)) -> dict:
    """Пропускает только пользователей с полным доступом. Остальным: 403 access_required."""
    if compute_access(user.get("access_until"))["status"] != "full":
        raise ApiError(403, "access_required", "Нужен полный доступ")
    return user