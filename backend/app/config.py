from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: str = "postgresql+asyncpg://crm:crm_secret@db:5432/crm"
    secret_key: str = "dev_secret_key_change_in_production"
    access_token_expire_minutes: int = 10080  # 7 дней

    telegram_bot_token: str = ""
    anthropic_api_key: str = ""

    ai_start_hour: int = 20
    ai_end_hour: int = 9
    company_name: str = "Инвест Недвижимость"

    class Config:
        env_file = ".env"


settings = Settings()
