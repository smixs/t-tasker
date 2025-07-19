"""Application settings configuration using pydantic-settings."""


from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application configuration settings."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"
    )

    # Telegram Bot Configuration
    telegram_bot_token: SecretStr = Field(
        description="Telegram Bot Token from @BotFather"
    )

    # OpenAI Configuration
    openai_api_key: SecretStr = Field(
        description="OpenAI API Key"
    )
    openai_model: str = Field(
        default="gpt-4o-2024-11-20",
        description="OpenAI model for task parsing"
    )
    openai_max_retries: int = Field(
        default=3,
        description="Maximum retries for OpenAI requests"
    )
    openai_timeout: int = Field(
        default=30,
        description="Timeout for OpenAI requests in seconds"
    )

    # Todoist Configuration
    # Note: Personal tokens are stored per-user in database, not in settings
    # Users will provide their token via /setup command in Telegram
    todoist_api_endpoint: str = Field(
        default="https://api.todoist.com/api/v1/sync",
        description="Todoist Unified API v1 endpoint"
    )
    todoist_rate_limit_requests: int = Field(
        default=450,
        description="Todoist API rate limit requests (conservative limit)"
    )
    todoist_rate_limit_window: int = Field(
        default=900,  # 15 minutes
        description="Todoist API rate limit window in seconds"
    )
    todoist_sync_commands_limit: int = Field(
        default=100,
        description="Maximum commands per sync request"
    )

    # Deepgram Configuration
    deepgram_api_key: SecretStr = Field(
        description="Deepgram API Key for speech transcription"
    )
    deepgram_model: str = Field(
        default="nova-3",
        description="Deepgram model for transcription"
    )
    deepgram_timeout: int = Field(
        default=30,
        description="Timeout for Deepgram requests in seconds"
    )

    # Database Configuration
    database_url: str = Field(
        description="PostgreSQL database URL"
    )
    database_pool_size: int = Field(
        default=10,
        description="Database connection pool size"
    )
    database_max_overflow: int = Field(
        default=20,
        description="Database connection pool max overflow"
    )
    database_echo: bool = Field(
        default=False,
        description="Enable SQLAlchemy query logging"
    )

    # Redis Configuration (for caching and rate limiting)
    redis_url: str = Field(
        default="redis://localhost:6379/0",
        description="Redis URL for caching"
    )
    redis_cache_ttl: int = Field(
        default=300,  # 5 minutes
        description="Default cache TTL in seconds"
    )

    # Audio Processing Configuration
    max_audio_duration: int = Field(
        default=300,  # 5 minutes
        description="Maximum audio duration in seconds"
    )
    max_file_size: int = Field(
        default=20 * 1024 * 1024,  # 20MB
        description="Maximum file size in bytes"
    )

    # Security Configuration
    encryption_key: SecretStr = Field(
        description="Key for encrypting user tokens in database"
    )
    session_secret: SecretStr = Field(
        description="Secret key for session management"
    )

    # Monitoring Configuration
    sentry_dsn: str | None = Field(
        default=None,
        description="Sentry DSN for error monitoring"
    )
    sentry_traces_sample_rate: float = Field(
        default=0.1,
        description="Sentry traces sample rate"
    )

    # OpenTelemetry Configuration
    otel_service_name: str = Field(
        default="tasker-bot",
        description="OpenTelemetry service name"
    )
    otel_exporter_endpoint: str | None = Field(
        default=None,
        description="OpenTelemetry exporter endpoint"
    )

    # Development Configuration
    debug: bool = Field(
        default=False,
        description="Enable debug mode"
    )
    log_level: str = Field(
        default="INFO",
        description="Logging level"
    )

    # Performance Targets
    target_latency_p95: float = Field(
        default=4.0,
        description="Target P95 latency in seconds"
    )
    target_cpu_usage: float = Field(
        default=0.5,
        description="Target CPU usage ratio"
    )
    target_memory_mb: int = Field(
        default=512,
        description="Target memory usage in MB"
    )

    @property
    def telegram_token(self) -> str:
        """Get Telegram bot token as string."""
        return self.telegram_bot_token.get_secret_value()

    @property
    def openai_key(self) -> str:
        """Get OpenAI API key as string."""
        return self.openai_api_key.get_secret_value()

    @property
    def deepgram_key(self) -> str:
        """Get Deepgram API key as string."""
        return self.deepgram_api_key.get_secret_value()


    @property
    def encryption_secret(self) -> str:
        """Get encryption key as string."""
        return self.encryption_key.get_secret_value()

    def model_dump_safe(self) -> dict:
        """Dump model without exposing secrets."""
        data = self.model_dump()
        # Remove or mask secret fields
        secret_fields = [
            'telegram_bot_token',
            'openai_api_key', 'deepgram_api_key',
            'encryption_key', 'session_secret'
        ]
        for field in secret_fields:
            if field in data:
                data[field] = "***"
        return data


# Global settings instance
_settings: Settings | None = None


def get_settings() -> Settings:
    """Get application settings singleton."""
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings


async def close_settings() -> None:
    """Clean up settings resources if needed."""
    # Currently no cleanup needed, but placeholder for future use
    pass


# Convenience function for tests
def override_settings(**kwargs) -> Settings:
    """Override settings for testing."""
    global _settings
    _settings = Settings(**kwargs)
    return _settings
