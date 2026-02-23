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

    OTP_EXPIRATION_MINUTES: int = 2 if ENVIRONMENT == "development" else 5
    LOGIN_ATTEMPTS: int = 3
    LOCKOUT_DURATION_MINUTES: int = 2 if ENVIRONMENT == "development" else 5
    ACTIVATION_TOKEN_EXPIRATION_MINUTES: int = 2 if ENVIRONMENT == "development" else 5
    API_BASE_URL: str = ""
    SUPPORT_EMAIL: str = ""
    JWT_SECRET_KEY: str = ""
    JWT_ALGORITHM: str = "HS256"
    JWT_ACCESS_TOKEN_EXPIRATION_MINUTES: int = (
        30 if ENVIRONMENT == "development" else 15
    )
    JWT_REFRESH_TOKEN_EXPIRATION_DAYS: int = 1
    
    COOKIE_ACCESS_NAME: str = "access_token"
    COOKIE_REFRESH_NAME: str = "refresh_token"
    COOKIE_LOGGED_IN_NAME: str = "logged_in"

    COOKIE_PATH: str = "/"
    COOKIE_SECURE: bool = False if ENVIRONMENT == "development" else True
    COOKIE_HTTP_ONLY: bool = True
    COOKIE_SAME_SITE: str = "lax"
    SIGNING_KEY: str = ""

    # Internationalization settings
    DEFAULT_LANGUAGE: str = "en"
    SUPPORTED_LANGUAGES: list[str] = [
        "en",
        "ar",
        "fr",
        "es",
    ]  # English, Arabic, French, Spanish


settings = Settings()
