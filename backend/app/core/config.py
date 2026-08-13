from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

_ENV_FILE = Path(__file__).resolve().parents[3] / ".env"


class Settings(BaseSettings):
    app_name: str = "Assitify Backend API"
    app_version: str = "1.0.0"
    allow_origins: list[str] = ["*"]
    database_url: str = "postgresql://assitify:assitify123@localhost:5432/assitify"
    redis_url: str = "redis://localhost:6379/0"
    qdrant_url: str = "http://localhost:6333"
    qdrant_api_key: str = ""
    ai_layer_url: str = "http://127.0.0.1:8000"
    embed_model: str = "text-embedding-3-small"
    jwt_secret: str = "change-me-in-production-assitify"
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 60
    auth_required: bool = True

    model_config = SettingsConfigDict(
        env_file=str(_ENV_FILE),
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = Settings()
