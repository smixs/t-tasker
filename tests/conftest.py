"""Pytest configuration and fixtures."""

import asyncio
import os
from typing import AsyncGenerator, Generator

import pytest
import pytest_asyncio
from unittest.mock import Mock, patch

from src.core.settings import Settings, override_settings


@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def mock_env_vars():
    """Mock environment variables for testing."""
    env_vars = {
        "TELEGRAM_BOT_TOKEN": "test_bot_token",
        "TELEGRAM_WEBHOOK_URL": "https://test.example.com",
        "OPENAI_API_KEY": "test_openai_key",
        "DEEPGRAM_API_KEY": "test_deepgram_key",
        "DATABASE_URL": "postgresql+asyncpg://test:test@localhost:5432/test",
        "ENCRYPTION_KEY": "test_encryption_key_32_bytes_long",
        "SESSION_SECRET": "test_session_secret"
    }
    
    with patch.dict(os.environ, env_vars, clear=True):
        yield env_vars


@pytest.fixture
def test_settings(mock_env_vars):
    """Create test settings instance."""
    settings = override_settings(**{
        key.lower(): value for key, value in mock_env_vars.items()
    })
    yield settings
    # Reset settings after test
    override_settings(**{})


@pytest.fixture
def mock_bot():
    """Create a mock bot instance."""
    bot = Mock()
    bot.get_me = Mock(return_value=Mock(username="test_bot"))
    return bot


@pytest_asyncio.fixture
async def mock_redis():
    """Create a mock Redis instance."""
    redis = Mock()
    redis.ping = Mock(return_value=asyncio.Future())
    redis.ping.return_value.set_result(True)
    redis.close = Mock(return_value=asyncio.Future())
    redis.close.return_value.set_result(None)
    return redis