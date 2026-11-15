from fastapi import APIRouter
from fastapi.responses import HTMLResponse

from app.config import settings
from app.errors import ApiError

router = APIRouter(include_in_schema=False)

PAGE = """<!doctype html>
<html lang="ru">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Проверка входа</title>
<script src="https://telegram.org/js/telegram-web-app.js"></script>
<style>
  body { font-family: -apple-system, system-ui, sans-serif; padding: 16px;
         color: var(--tg-theme-text-color, #000); background: var(--tg-theme-bg-color, #fff); }
  pre { white-space: pre-wrap; word-break: break-word; padding: 12px; border-radius: 8px;
        background: rgba(127, 127, 127, 0.15); }
  .ok { color: #2e7d32; font-weight: 600; }
  .bad { color: #c62828; font-weight: 600; }
</style>
</head>
<body>
<h2>Проверка входа через Telegram</h2>
<div id="status">Проверяю…</div>
<pre id="out"></pre>
<script>
  const tg = window.Telegram && window.Telegram.WebApp;
  const statusEl = document.getElementById('status');
  const outEl = document.getElementById('out');

  function show(ok, title, data) {
    statusEl.className = ok ? 'ok' : 'bad';
    statusEl.textContent = title;
    outEl.textContent = JSON.stringify(data, null, 2);
  }

  (async () => {
    if (!tg || !tg.initData) {
      show(false, 'Нет initData: откройте страницу кнопкой бота внутри Telegram', {});
      return;
    }
    tg.ready();
    try {
      const login = await fetch('/api/v1/auth/telegram', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ init_data: tg.initData }),
      });
      const loginBody = await login.json();
      if (!login.ok) {
        show(false, 'Вход не удался: ' + login.status, loginBody);
        return;
      }
      const me = await fetch('/api/v1/me', {
        headers: { Authorization: 'Bearer ' + loginBody.access_token },
      });
      const meBody = await me.json();
      show(me.ok, me.ok ? 'Вход выполнен' : 'Ошибка /me: ' + me.status, meBody);
    } catch (e) {
      show(false, 'Ошибка сети', { error: String(e) });
    }
  })();
</script>
</body>
</html>
"""


@router.get("/dev/webapp", response_class=HTMLResponse)
def dev_webapp():
    """Тестовая страница для проверки входа в Telegram. Только при APP_ENV=dev."""
    if settings.app_env != "dev":
        raise ApiError(404, "not_found", "Не найдено")
    return HTMLResponse(PAGE)