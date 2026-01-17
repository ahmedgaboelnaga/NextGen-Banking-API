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


settings = Settings()
