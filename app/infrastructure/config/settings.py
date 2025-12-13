"""Application settings."""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application configuration settings."""

    debug_mode: bool = False
    state_ttl_seconds: int = 86400  # 24 hours default
    twilio_account_sid: str = ""
    twilio_auth_token: str = ""
    twilio_whatsapp_number: str = ""
    twilio_validate_signature: bool = False
    llm_enabled: bool = False
    openai_api_key: str = ""
    openai_model: str = "gpt-4o-mini"
    openai_timeout_seconds: int = 10

    model_config = SettingsConfigDict(
        env_file=".env",
        case_sensitive=False,
        env_prefix="",
    )


settings = Settings()
