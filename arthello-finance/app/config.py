from functools import lru_cache
from pathlib import Path

from dotenv import load_dotenv
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=str(BASE_DIR / ".env"),
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )

    APP_NAME: str = "ARTHELLO Finance Dashboard"
    APP_ENV: str = Field(default="development")
    DEBUG: bool = Field(default=True)

    DATABASE_URL: str = Field(
        default="postgresql+asyncpg://arthello:arthello@localhost:5432/arthello_finance"
    )

    SECRET_KEY: str = Field(default="change-me-in-production-min-32-chars")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = Field(default=60 * 24 * 7)

    TELEGRAM_BOT_TOKEN: str = Field(default="")
    TELEGRAM_CHAT_ID: str = Field(default="")

    CORS_ORIGINS: str = Field(default="*")

    BANK_SYNC_INTERVAL_MINUTES: int = Field(default=30)
    DAILY_REPORT_HOUR: int = Field(default=9)

    # Точка OAuth2
    TOCHKA_CLIENT_ID: str = Field(default="")
    TOCHKA_CLIENT_SECRET: str = Field(default="")
    TOCHKA_REDIRECT_URL: str = Field(
        default="https://mybigprojects-production.up.railway.app/api/auth/tochka/callback"
    )
    # Авторизация Точки — Keycloak-realm. Если у вас старая интеграция
    # на /oauth2/authorize — переопределите эти переменные на Railway.
    TOCHKA_AUTHORIZE_URL: str = Field(
        default="https://id.tochka.com/realms/tochka/protocol/openid-connect/auth"
    )
    TOCHKA_TOKEN_URL: str = Field(
        default="https://id.tochka.com/realms/tochka/protocol/openid-connect/token"
    )
    TOCHKA_API_BASE: str = Field(default="https://enter.tochka.com/api/v1")
    TOCHKA_SCOPE: str = Field(default="account_info balances statements")
    TOCHKA_SYNC_INTERVAL_HOURS: int = Field(default=2)

    @property
    def cors_origins_list(self) -> list[str]:
        if not self.CORS_ORIGINS or self.CORS_ORIGINS == "*":
            return ["*"]
        return [o.strip() for o in self.CORS_ORIGINS.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
