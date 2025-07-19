"""Tests for application settings."""

import os
from unittest.mock import patch

import pytest
from pydantic import ValidationError
from pydantic_settings import SettingsConfigDict

from src.core.settings import Settings, get_settings, override_settings


class TestSettings:
    """Test settings configuration."""
    
    def test_settings_from_env(self, mock_env_vars):
        """Test loading settings from environment variables."""
        settings = Settings()
        
        assert settings.telegram_bot_token.get_secret_value() == "test_bot_token"
        assert settings.telegram_webhook_url == "https://test.example.com"
        assert settings.openai_api_key.get_secret_value() == "test_openai_key"
        assert settings.deepgram_api_key.get_secret_value() == "test_deepgram_key"
        assert settings.database_url == "postgresql+asyncpg://test:test@localhost:5432/test"
    
    def test_settings_defaults(self, mock_env_vars):
        """Test default values for optional settings."""
        settings = Settings()
        
        assert settings.server_host == "0.0.0.0"
        assert settings.server_port == 8443
        assert settings.webhook_path == "/webhook"
        assert settings.health_check_path == "/health"
        assert settings.openai_model == "gpt-4o-2024-11-20"
        assert settings.deepgram_model == "nova-3"  # Default value in settings.py
        assert settings.todoist_api_endpoint == "https://api.todoist.com/api/v1/sync"
        assert settings.todoist_rate_limit_requests == 450
        assert settings.debug is False
        assert settings.log_level == "INFO"
    
    def test_settings_validation_error(self):
        """Test validation error when required fields are missing."""
        # Need to temporarily rename .env file to prevent it from being loaded
        import tempfile
        with tempfile.TemporaryDirectory() as temp_dir:
            with patch.dict(os.environ, {"ENV_FILE": f"{temp_dir}/.env"}, clear=True):
                # Override the model_config to use a non-existent .env file
                with patch.object(Settings, 'model_config', SettingsConfigDict(
                    env_file=f"{temp_dir}/.env",
                    env_file_encoding="utf-8",
                    case_sensitive=False,
                    extra="ignore"
                )):
                    with pytest.raises(ValidationError) as exc_info:
                        Settings()
                    
                    errors = exc_info.value.errors()
                    required_fields = {error["loc"][0] for error in errors}
                    
                    assert "telegram_bot_token" in required_fields
                    assert "openai_api_key" in required_fields
                    assert "deepgram_api_key" in required_fields
                    assert "database_url" in required_fields
                    assert "encryption_key" in required_fields
                    assert "session_secret" in required_fields
    
    def test_settings_properties(self, test_settings):
        """Test settings property methods."""
        assert test_settings.telegram_token == "test_bot_token"
        assert test_settings.openai_key == "test_openai_key"
        assert test_settings.deepgram_key == "test_deepgram_key"
        # Todoist tokens are now stored per-user in database, not in settings
        assert test_settings.encryption_secret == "test_encryption_key_32_bytes_long"
    
    def test_todoist_token_removed(self, mock_env_vars):
        """Test that Todoist tokens are no longer in settings."""
        # Remove TODOIST_PERSONAL_TOKEN from env if present
        env_without_token = {k: v for k, v in mock_env_vars.items() if k != "TODOIST_PERSONAL_TOKEN"}
        with patch.dict(os.environ, env_without_token, clear=True):
            settings = Settings()
            
            # Todoist configuration should only have API endpoint and rate limit settings
            assert hasattr(settings, 'todoist_api_endpoint')
            assert hasattr(settings, 'todoist_rate_limit_requests')
            assert hasattr(settings, 'todoist_sync_commands_limit')
            
            # No personal token or OAuth fields should exist
            assert not hasattr(settings, 'todoist_personal_token')
            assert not hasattr(settings, 'todoist_client_id')
            assert not hasattr(settings, 'todoist_client_secret')
    
    def test_settings_model_dump_safe(self, test_settings):
        """Test safe model dump masks secrets."""
        safe_dump = test_settings.model_dump_safe()
        
        assert safe_dump["telegram_bot_token"] == "***"
        assert safe_dump["openai_api_key"] == "***"
        assert safe_dump["deepgram_api_key"] == "***"
        # Todoist personal token no longer in settings
        assert safe_dump["encryption_key"] == "***"
        assert safe_dump["session_secret"] == "***"
        
        # Non-secret fields should remain
        assert safe_dump["server_host"] == "0.0.0.0"
        assert safe_dump["server_port"] == 8443
    
    def test_get_settings_singleton(self, mock_env_vars):
        """Test get_settings returns singleton instance."""
        settings1 = get_settings()
        settings2 = get_settings()
        
        assert settings1 is settings2
    
    def test_override_settings(self):
        """Test override_settings for testing."""
        test_token = "override_test_token"
        settings = override_settings(
            telegram_bot_token=test_token,
            openai_api_key="test_key",
            deepgram_api_key="test_key",
            database_url="test_url",
            encryption_key="test_key",
            session_secret="test_secret"
        )
        
        assert settings.telegram_token == test_token
        assert get_settings() is settings
    
    def test_todoist_sync_settings(self, test_settings):
        """Test Todoist sync-specific settings."""
        assert test_settings.todoist_api_endpoint == "https://api.todoist.com/api/v1/sync"
        assert test_settings.todoist_sync_commands_limit == 100
        assert test_settings.todoist_rate_limit_requests == 450
        assert test_settings.todoist_rate_limit_window == 900
    
    def test_performance_targets(self, test_settings):
        """Test performance target settings."""
        assert test_settings.target_latency_p95 == 4.0
        assert test_settings.target_cpu_usage == 0.5
        assert test_settings.target_memory_mb == 512
    
    def test_audio_processing_settings(self, test_settings):
        """Test audio processing settings."""
        assert test_settings.max_audio_duration == 300  # 5 minutes
        assert test_settings.max_file_size == 20 * 1024 * 1024  # 20MB