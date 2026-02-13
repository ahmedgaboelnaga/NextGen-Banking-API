from pathlib import Path
from typing import Literal
from pydantic_settings import BaseSettings, SettingsConfigDict


env_path = Path(__file__).parent.parent.parent.parent / ".envs" / ".env.development"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=env_path,
        env_file_encoding="utf-8",
        env_ignore_empty=True,
        extra="ignore",
    )

    ENVIRONMENT: Literal["development", "staging", "production"] = "development"

    PROJECT_NAME: str = ""
    PROJECT_DESCRIPTION: str = ""
    API_V1_STR: str = ""
    SITE_NAME: str = ""
    DATABASE_URL: str = ""

    MAIL_FROM: str = ""
    MAIL_FROM_NAME: str = ""
    SMTP_HOST: str = "mailpit"
    SMTP_PORT: int = 1025
    MAILPIT_UI_PORT: int = 8025

    REDIS_HOST: str = "redis"
    REDIS_PORT: int = 6379
    REDIS_DB: int = 0

    RABBITMQ_HOST: str = "rabbitmq"
    RABBITMQ_PORT: int = 5672
    RABBITMQ_USER: str = "guest"
    RABBITMQ_PASSWORD: str = "guest"

    OTP_EXIRATION_MINUTES: int = 2 if ENVIRONMENT == "local" else 5
    LOGIN_ATTEMPTS: int = 3
    LOCKOUT_DURATION_MINUTES: int = 2 if ENVIRONMENT == "local" else 5


settings = Settings()
