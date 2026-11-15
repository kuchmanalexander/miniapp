from datetime import date, datetime, timedelta, timezone

from app.access import compute_access, days_to_exam

NOW = datetime(2026, 11, 12, 12, 0, tzinfo=timezone.utc)


def test_no_access_is_demo():
    assert compute_access(None, NOW) == {"status": "demo", "until": None}


def test_future_access_is_full():
    until = (NOW + timedelta(days=5)).isoformat()
    result = compute_access(until, NOW)
    assert result["status"] == "full"
    assert result["until"] is not None


def test_expired_access_is_demo():
    until = (NOW - timedelta(seconds=1)).isoformat()
    assert compute_access(until, NOW)["status"] == "demo"


def test_string_without_timezone_is_treated_as_utc():
    assert compute_access("2026-12-01T00:00:00", NOW)["status"] == "full"
    assert compute_access("2026-01-01T00:00:00", NOW)["status"] == "demo"


def test_days_to_exam():
    assert days_to_exam("2026-12-15", today=date(2026, 11, 12)) == 33
    assert days_to_exam("2026-11-12", today=date(2026, 11, 12)) == 0


def test_days_to_exam_empty_invalid_or_past():
    assert days_to_exam("", today=date(2026, 11, 12)) is None
    assert days_to_exam("не дата", today=date(2026, 11, 12)) is None
    assert days_to_exam("2026-11-01", today=date(2026, 11, 12)) is None