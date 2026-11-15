import logging

from fastapi import APIRouter, Depends, Request

from app.auth import InitDataError, create_access_token, validate_init_data
from app.config import settings
from app.errors import ApiError
from app.ratelimit import client_ip, limit_auth
from app.repository import UsersRepo, db_unavailable, get_users_repo
from app.schemas import DevLoginRequest, TelegramLoginRequest, TokenResponse, UserInfo

logger = logging.getLogger("app.auth")

router = APIRouter(prefix="/auth", tags=["auth"], dependencies=[Depends(limit_auth)])


def _issue_token(user: UserInfo) -> TokenResponse:
    if not settings.jwt_secret:
        raise ApiError(500, "server_misconfigured", "Сервер не настроен")
    token = create_access_token(user.id, settings.jwt_secret, settings.jwt_ttl_minutes)
    return TokenResponse(
        access_token=token,
        expires_in=settings.jwt_ttl_minutes * 60,
        user=user,
    )


def parse_ref(start_param: str | None) -> int | None:
    """Достаёт ID пригласившего из параметра вида ref_12345."""
    if start_param and start_param.startswith("ref_"):
        value = start_param[4:]
        if value.isdigit():
            return int(value)
    return None


@router.post("/telegram", response_model=TokenResponse)
def login_telegram(
    body: TelegramLoginRequest,
    request: Request,
    repo: UsersRepo = Depends(get_users_repo),
):
    """Вход по initData из Telegram Mini App. Создаёт пользователя, если его ещё нет."""
    if not settings.bot_token:
        raise ApiError(500, "server_misconfigured", "Сервер не настроен")

    try:
        data = validate_init_data(
            body.init_data,
            settings.bot_token,
            max_age_seconds=settings.init_data_max_age_seconds,
        )
    except InitDataError as e:
        logger.warning("Неудачный вход через Telegram: %s (ip=%s)", e, client_ip(request))
        raise ApiError(401, "invalid_init_data", str(e))

    tg_user = data["user"]
    try:
        row, is_new = repo.upsert_telegram_user(
            tg_user, parse_ref(data.get("start_param"))
        )
    except Exception:
        logger.exception("Ошибка базы данных при входе")
        raise db_unavailable()

    if is_new:
        logger.info("Новый пользователь: %s", row["telegram_id"])

    user = UserInfo(
        id=row["telegram_id"],
        first_name=row.get("first_name"),
        username=row.get("username"),
    )
    return _issue_token(user)


@router.post("/dev", response_model=TokenResponse)
def login_dev(body: DevLoginRequest, repo: UsersRepo = Depends(get_users_repo)):
    """Вход без Telegram для разработки (только APP_ENV=dev).

    Отрицательный telegram_id: создаётся тестовый пользователь.
    Положительный: только для уже существующего пользователя (запись не создаётся).
    """
    if settings.app_env != "dev" or not settings.dev_login_enabled:
        raise ApiError(404, "not_found", "Не найдено")

    try:
        if body.telegram_id < 0:
            repo.upsert_telegram_user(
                {"id": body.telegram_id, "first_name": body.first_name}, None
            )
        elif repo.get(body.telegram_id) is None:
            raise ApiError(
                404,
                "user_not_found",
                "Такого пользователя нет в базе. Для тестов используйте отрицательный telegram_id",
            )
    except ApiError:
        raise
    except Exception:
        logger.exception("Ошибка базы данных при dev-входе")
        raise db_unavailable()

    return _issue_token(UserInfo(id=body.telegram_id, first_name=body.first_name))