import logging
import threading
from datetime import datetime, timezone
from typing import Protocol

from app.config import settings
from app.errors import ApiError
from app.notify import notify_admins

logger = logging.getLogger("app.repository")


class UsersRepo(Protocol):
    def get(self, user_id: int) -> dict | None: ...

    def upsert_telegram_user(
        self, tg_user: dict, referred_by: int | None
    ) -> tuple[dict, bool]: ...


class SupabaseUsers:
    """Пользователи в таблице users (Supabase), общей с ботом."""

    def __init__(self, url: str, key: str):
        from supabase import create_client

        self.client = create_client(url, key)

    def get(self, user_id: int) -> dict | None:
        res = (
            self.client.table("users")
            .select("*")
            .eq("telegram_id", user_id)
            .execute()
        )
        return res.data[0] if res.data else None

    def upsert_telegram_user(
        self, tg_user: dict, referred_by: int | None
    ) -> tuple[dict, bool]:
        """Создаёт пользователя или обновляет имя. Возвращает (строка, это новый пользователь)."""
        user_id = tg_user["id"]
        fields = {
            "first_name": tg_user.get("first_name"),
            "username": tg_user.get("username"),
        }

        existing = self.get(user_id)
        if existing:
            changes = {k: v for k, v in fields.items() if existing.get(k) != v}
            if changes:
                self.client.table("users").update(changes).eq(
                    "telegram_id", user_id
                ).execute()
                existing.update(changes)
            return existing, False

        # Пригласивший должен существовать и не быть самим пользователем
        if referred_by is not None and (
            referred_by == user_id or self.get(referred_by) is None
        ):
            referred_by = None

        row = {"telegram_id": user_id, **fields, "referred_by": referred_by}
        try:
            res = self.client.table("users").insert(row).execute()
        except Exception:
            # Параллельный вход мог создать запись раньше нас
            again = self.get(user_id)
            if again:
                return again, False
            raise
        return (res.data[0] if res.data else row), True


class InMemoryUsers:
    """Хранилище в памяти: для тестов и для разработки без базы."""

    def __init__(self):
        self._rows: dict[int, dict] = {}
        self._lock = threading.Lock()

    def get(self, user_id: int) -> dict | None:
        with self._lock:
            row = self._rows.get(user_id)
            return dict(row) if row else None

    def upsert_telegram_user(
        self, tg_user: dict, referred_by: int | None
    ) -> tuple[dict, bool]:
        user_id = tg_user["id"]
        fields = {
            "first_name": tg_user.get("first_name"),
            "username": tg_user.get("username"),
        }
        with self._lock:
            row = self._rows.get(user_id)
            if row:
                row.update(fields)
                return dict(row), False

            if referred_by is not None and (
                referred_by == user_id or referred_by not in self._rows
            ):
                referred_by = None

            row = {
                "telegram_id": user_id,
                **fields,
                "referred_by": referred_by,
                "access_until": None,
                "created_at": datetime.now(timezone.utc).isoformat(),
            }
            self._rows[user_id] = row
            return dict(row), True

    def set_access_until(self, user_id: int, value: str | None) -> None:
        """Только для тестов: выдать или забрать доступ."""
        with self._lock:
            self._rows[user_id]["access_until"] = value


_repo: UsersRepo | None = None
_repo_lock = threading.Lock()


def get_users_repo() -> UsersRepo:
    """Хранилище пользователей. Создаётся один раз при первом обращении."""
    global _repo
    with _repo_lock:
        if _repo is None:
            if settings.supabase_url and settings.supabase_key:
                _repo = SupabaseUsers(settings.supabase_url, settings.supabase_key)
            else:
                logger.warning(
                    "SUPABASE_URL/SUPABASE_KEY не заданы: используется хранилище "
                    "в памяти (только для разработки)"
                )
                _repo = InMemoryUsers()
        return _repo


def db_unavailable() -> ApiError:
    """Ошибка 503 для клиента и уведомление админам."""
    notify_admins("⚠️ База данных недоступна для API", key="db_unavailable")
    return ApiError(503, "db_unavailable", "База данных временно недоступна")