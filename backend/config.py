from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # Anthropic API
    anthropic_api_key: str
    anthropic_model: str = "claude-sonnet-4-6"

    # Database
    database_url: str = "sqlite:///./sentinel.db"

    # Agent behavior
    confidence_threshold: float = 0.75  # Below this, always escalate to human
    max_retries: int = 3
    request_timeout_seconds: int = 30

    # API
    api_host: str = "0.0.0.0"
    api_port: int = 8000

    class Config:
        env_file = ".env"
        case_sensitive = False


settings = Settings()
