from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

_ENV_FILE = Path(__file__).resolve().parent.parent / ".env"


class Settings(BaseSettings):
    app_name: str = "AI Layer API"
    app_version: str = "1.0.0"
    upload_dir: str = "uploads"
    allow_origins: list[str] = ["*"]
    openai_api_key: str = ""
    llm_model: str = "gpt-4o-mini"
    database_url: str = ""
    redis_url: str = ""
    qdrant_url: str = ""
    qdrant_api_key: str = ""
    embed_model: str = "text-embedding-3-small"

    model_config = SettingsConfigDict(env_file=str(_ENV_FILE), env_file_encoding="utf-8", extra="ignore")


settings = Settings()
