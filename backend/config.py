from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=Path(__file__).resolve().parent.parent / '.env',
        env_file_encoding='utf-8',
        extra='ignore',
    )

    database_url: str = 'sqlite:///./easeit.db'
    jwt_secret: str = 'dev-secret-change-me'
    jwt_algorithm: str = 'HS256'
    jwt_expire_minutes: int = 60
    ollama_url: str = 'http://localhost:11434'
    llm_model: str = 'llama3.2:3b'
    frontend_origin: str = 'http://localhost:5173'
    smtp_host: str = 'localhost'
    smtp_port: int = 1025
    n8n_webhook_url: str = ''
    n8n_webhook_token: str = ''
    n8n_timeout_seconds: float = 30


settings = Settings()
