from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Literal
import os

current_file_dir = os.path.dirname(os.path.abspath(__file__))
env_path = os.path.join(current_file_dir, "..", "..", "..", ".envs", ".env.development")


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
