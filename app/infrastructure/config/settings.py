"""Application settings."""

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application configuration settings."""

    class Config:
        """Pydantic configuration."""

        env_file = ".env"
        case_sensitive = False


settings = Settings()
