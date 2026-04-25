from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "AI Layer API"
    app_version: str = "1.0.0"
    upload_dir: str = "uploads"
    allow_origins: list[str] = ["*"]
    openai_api_key: str = ""
    llm_model: str = "gpt-4.1-mini"

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")


settings = Settings()
