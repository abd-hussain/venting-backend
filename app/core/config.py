from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = "Venting Backend"
    app_env: str = "development"
    debug: bool = True
    api_v1_prefix: str = "/v1"
    cors_origins: list[str] = ["*"]

    # Database — matches docker-compose-dev.yml env vars; override with DATABASE_URL.
    database_url: str | None = None
    database_hostname: str = "localhost"
    database_port: int = 5432
    database_username: str = "postgres"
    database_password: str = "password123"
    database_name: str = "venting_db"

    # Auth / JWT
    secret_key: str = "change-me-in-production-use-a-long-random-string"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 60
    refresh_token_expire_days: int = 30

    # Uploads (avatars, etc.) — served under /static
    static_dir: str = "static"
    upload_subdir: str = "uploads"

    # Static / non-API content URLs (mobile WebViews & support)
    terms_url: str = "https://venting.app/terms"
    privacy_url: str = "https://venting.app/privacy"
    help_center_base_url: str = "https://venting.app/help"
    support_email: str = "support@venting.app"
    support_whatsapp: str = ""

    @property
    def sqlalchemy_database_url(self) -> str:
        if self.database_url:
            url = self.database_url
            # Heroku provides postgres:// or postgresql://; we use psycopg3.
            if url.startswith("postgres://"):
                url = url.replace("postgres://", "postgresql+psycopg://", 1)
            elif url.startswith("postgresql://"):
                url = url.replace("postgresql://", "postgresql+psycopg://", 1)
            return url
        return (
            f"postgresql+psycopg://{self.database_username}:{self.database_password}"
            f"@{self.database_hostname}:{self.database_port}/{self.database_name}"
        )

    @property
    def upload_dir(self) -> str:
        return f"{self.static_dir}/{self.upload_subdir}"


@lru_cache
def get_settings() -> Settings:
    return Settings()
