import logging
import threading
import time

import httpx

from app.config import settings

logger = logging.getLogger("app.notify")

COOLDOWN_SECONDS = 600
_last_sent: dict[str, float] = {}
_lock = threading.Lock()


def _scrub(text: str) -> str:
    """Прячем секреты, если они случайно попали в текст ошибки."""
    for secret in (settings.bot_token, settings.jwt_secret):
        if secret:
            text = text.replace(secret, "***")
    return text


def _send(text: str) -> None:
    for admin_id in settings.admin_id_list:
        try:
            httpx.post(
                f"https://api.telegram.org/bot{settings.bot_token}/sendMessage",
                json={"chat_id": admin_id, "text": text},
                timeout=10,
            )
        except Exception:
            # Не логируем детали: в тексте исключения может быть адрес с токеном
            logger.warning("Не удалось отправить уведомление админу %s", admin_id)


def notify_admins(text: str, key: str) -> None:
    """Отправляет админам сообщение в фоне. Одинаковые (по key) не чаще раза в 10 минут."""
    if not settings.bot_token or not settings.admin_id_list:
        return

    now = time.monotonic()
    with _lock:
        if now - _last_sent.get(key, 0) < COOLDOWN_SECONDS:
            return
        if len(_last_sent) > 200:
            _last_sent.clear()
        _last_sent[key] = now

    threading.Thread(target=_send, args=(_scrub(text)[:3900],), daemon=True).start()