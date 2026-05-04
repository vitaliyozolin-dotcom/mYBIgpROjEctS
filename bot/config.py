from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    telegram_bot_token: str = ""
    anthropic_api_key: str = ""
    ai_start_hour: int = 20
    ai_end_hour: int = 9
    company_name: str = "Инвест Недвижимость"
    backend_url: str = "http://backend:8000"

    class Config:
        env_file = ".env"


settings = Settings()
