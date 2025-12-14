"""Application settings."""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application configuration settings."""

    debug_mode: bool = False
    state_ttl_seconds: int = 86400  # 24 hours default
    conversation_state_repository: str = "in_memory"  # in_memory or postgres
    lead_repository: str = "in_memory"  # in_memory or postgres
    database_url: str = (
        ""  # Required when conversation_state_repository=postgres or lead_repository=postgres
    )
    twilio_account_sid: str = ""
    twilio_auth_token: str = ""
    twilio_whatsapp_number: str = ""
    twilio_validate_signature: bool = False
    llm_enabled: bool = False
    openai_api_key: str = ""
    openai_model: str = "gpt-4o-mini"
    openai_timeout_seconds: int = 10
    redis_url: str = "redis://localhost:6379/0"
    twilio_idempotency_enabled: bool = True
    twilio_idempotency_ttl_seconds: int = 3600

    model_config = SettingsConfigDict(
        env_file=".env",
        case_sensitive=False,
        env_prefix="",
    )


settings = Settings()
