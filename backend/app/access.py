from datetime import date, datetime, timezone
from zoneinfo import ZoneInfo

from app.config import settings


def parse_dt(value) -> datetime | None:
    """Приводит значение из базы к дате со временем (без часового пояса считаем UTC)."""
    if not value:
        return None
    if isinstance(value, datetime):
        dt = value
    else:
        dt = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt


def compute_access(access_until, now: datetime | None = None) -> dict:
    """Возвращает {"status": "full" | "demo", "until": строка или None}."""
    now = now or datetime.now(timezone.utc)
    until = parse_dt(access_until)
    if until and until > now:
        return {"status": "full", "until": until.isoformat()}
    return {"status": "demo", "until": None}


def days_to_exam(exam_date: str, today: date | None = None) -> int | None:
    """Сколько дней до экзамена. None, если дата не задана, неверна или экзамен прошёл."""
    if not exam_date:
        return None
    try:
        exam_day = date.fromisoformat(exam_date)
    except ValueError:
        return None
    today = today or datetime.now(ZoneInfo(settings.timezone)).date()
    days = (exam_day - today).days
    return days if days >= 0 else None