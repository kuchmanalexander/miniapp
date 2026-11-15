from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Настройки приложения. Значения берутся из файла .env и переменных окружения."""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # По умолчанию prod: режим dev включается явно (APP_ENV=dev в локальном .env)
    app_env: str = "prod"
    bot_token: str = ""
    jwt_secret: str = ""
    jwt_ttl_minutes: int = 1440
    init_data_max_age_seconds: int = 86400
    cors_origins: str = "http://localhost:5173"
    admin_ids: str = ""
    auth_rate_limit: int = 10
    trust_proxy: bool = False
    log_level: str = "INFO"
    supabase_url: str = ""
    supabase_key: str = ""
    exam_date: str = ""
    timezone: str = "Europe/Moscow"
    dev_login_enabled: bool = True

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    @property
    def admin_id_list(self) -> list[int]:
        return [int(x) for x in self.admin_ids.split(",") if x.strip().isdigit()]


settings = Settings()


def check_settings(s: Settings) -> None:
    """Проверяет настройки при запуске. При проблеме останавливает сервер с понятным текстом."""
    problems = []

    if s.app_env not in ("dev", "prod"):
        problems.append("APP_ENV должен быть dev или prod")

    if s.app_env == "prod":
        if len(s.jwt_secret) < 32:
            problems.append("JWT_SECRET должен быть не короче 32 символов")
        if not s.bot_token:
            problems.append("BOT_TOKEN не задан")
        if "*" in s.cors_origin_list:
            problems.append("CORS_ORIGINS не должен содержать *")
        if not s.supabase_url or not s.supabase_key:
            problems.append("SUPABASE_URL и SUPABASE_KEY должны быть заданы")
    elif s.app_env == "dev":
        if not s.jwt_secret:
            problems.append("JWT_SECRET не задан")

    if problems:
        raise RuntimeError("Неверные настройки:\n- " + "\n- ".join(problems))