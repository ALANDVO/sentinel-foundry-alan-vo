from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field
from typing import Optional
import secrets


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Application
    app_host: str = "0.0.0.0"
    app_port: int = 8000
    app_env: str = "development"
    secret_key: str = Field(default_factory=lambda: secrets.token_urlsafe(32))

    # Database
    database_url: str = "sqlite:///./data/sentinel.db"

    # Keycloak / OIDC
    keycloak_url: str = "http://localhost:8080"
    keycloak_realm: str = "sentinel"
    keycloak_client_id: str = "sentinel-backend"
    keycloak_client_secret: str = ""
    oidc_issuer_url: str = "http://localhost:8080/realms/sentinel"
    oidc_redirect_uri: str = "http://localhost:5173/callback"
    oidc_logout_redirect_uri: str = "http://localhost:5173"

    # Demo mode (explicitly gated)
    demo_mode: bool = True

    # LLM Provider defaults (can be overridden via UI)
    openai_compatible_base_url: Optional[str] = None
    openai_compatible_api_key: Optional[str] = None
    openai_compatible_model: Optional[str] = None
    anthropic_api_key: Optional[str] = None
    anthropic_base_url: str = "https://api.anthropic.com"
    gemini_api_key: Optional[str] = None
    gemini_base_url: str = "https://generativelanguage.googleapis.com"
    ollama_base_url: str = "http://localhost:11434"


settings = Settings()