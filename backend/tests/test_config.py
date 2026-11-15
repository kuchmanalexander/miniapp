import pytest

from app.config import Settings, check_settings


def make(**kwargs) -> Settings:
    base = dict(
        app_env="prod",
        jwt_secret="x" * 40,
        bot_token="1:abc",
        cors_origins="https://app.example.com",
        supabase_url="https://example.supabase.co",
        supabase_key="key",
    )
    base.update(kwargs)
    return Settings(_env_file=None, **base)


def test_valid_prod_settings_pass():
    check_settings(make())


def test_prod_short_jwt_secret_fails():
    with pytest.raises(RuntimeError, match="JWT_SECRET"):
        check_settings(make(jwt_secret="short"))


def test_prod_without_bot_token_fails():
    with pytest.raises(RuntimeError, match="BOT_TOKEN"):
        check_settings(make(bot_token=""))


def test_prod_wildcard_cors_fails():
    with pytest.raises(RuntimeError, match="CORS_ORIGINS"):
        check_settings(make(cors_origins="*"))


def test_prod_without_database_fails():
    with pytest.raises(RuntimeError, match="SUPABASE_URL"):
        check_settings(make(supabase_url="", supabase_key=""))


def test_dev_without_jwt_secret_fails():
    with pytest.raises(RuntimeError, match="JWT_SECRET"):
        check_settings(make(app_env="dev", jwt_secret=""))


def test_unknown_env_fails():
    with pytest.raises(RuntimeError, match="APP_ENV"):
        check_settings(make(app_env="staging"))