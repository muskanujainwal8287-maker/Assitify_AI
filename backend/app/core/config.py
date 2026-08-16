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
    jwt_expire_minutes: int = 60 * 24 * 7
    auth_required: bool = True
    frontend_url: str = "http://localhost:5173"
    password_reset_expire_minutes: int = 15
    password_reset_rate_limit: int = 3
    smtp_host: str = ""
    smtp_port: int = 587
    smtp_user: str = ""
    smtp_password: str = ""
    smtp_from: str = "noreply@assistify.local"
    smtp_use_tls: bool = True
    # SMS: leave sms_provider empty to log OTP locally. Supported: "fast2sms", "twilio"
    sms_provider: str = ""
    sms_api_key: str = ""
    twilio_account_sid: str = ""
    twilio_auth_token: str = ""
    twilio_from_number: str = ""
    twilio_verify_service_sid: str = ""

    model_config = SettingsConfigDict(
        env_file=str(_ENV_FILE),
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = Settings()
