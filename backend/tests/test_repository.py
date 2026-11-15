from app.repository import InMemoryUsers


def test_upsert_creates_then_updates_name_but_keeps_referrer():
    repo = InMemoryUsers()
    repo.upsert_telegram_user({"id": 5, "first_name": "Пригласивший"}, None)

    row, is_new = repo.upsert_telegram_user(
        {"id": 1, "first_name": "A", "username": "a"}, 5
    )
    assert is_new
    assert row["telegram_id"] == 1
    assert row["referred_by"] == 5

    row, is_new = repo.upsert_telegram_user(
        {"id": 1, "first_name": "B", "username": "a"}, None
    )
    assert not is_new
    assert row["first_name"] == "B"
    assert row["referred_by"] == 5


def test_get_returns_copy_and_none_for_missing():
    repo = InMemoryUsers()
    assert repo.get(1) is None
    repo.upsert_telegram_user({"id": 1, "first_name": "A"}, None)
    row = repo.get(1)
    row["first_name"] = "изменено снаружи"
    assert repo.get(1)["first_name"] == "A"