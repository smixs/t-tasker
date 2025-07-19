"""Tests for OpenAI service."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from src.core.exceptions import OpenAIError, ValidationError
from src.models.task import TaskSchema
from src.services.openai_service import OpenAIService


class TestOpenAIService:
    """Test OpenAI service."""

    @pytest.fixture
    def openai_service(self):
        """Create OpenAI service instance."""
        with patch('src.services.openai_service.AsyncOpenAI'):
            with patch('src.services.openai_service.instructor.patch') as mock_patch:
                mock_patch.return_value = MagicMock()
                service = OpenAIService()
                yield service

    @pytest.mark.asyncio
    async def test_parse_task_success(self, openai_service):
        """Test successful task parsing."""
        # Mock response
        mock_task = TaskSchema(
            content="Купить молоко",
            due_string="завтра",
            priority=2,
            labels=["покупки"]
        )
        
        openai_service.instructor_client.chat.completions.create = AsyncMock(
            return_value=mock_task
        )
        
        result = await openai_service.parse_task("Купить молоко завтра")
        
        assert result.content == "Купить молоко"
        assert result.due_string == "завтра"
        assert result.priority == 2
        assert result.labels == ["покупки"]

    @pytest.mark.asyncio
    async def test_parse_task_with_profanity(self, openai_service):
        """Test task parsing with profanity filtering."""
        mock_task = TaskSchema(content="Купить **** молоко")
        
        openai_service.instructor_client.chat.completions.create = AsyncMock(
            return_value=mock_task
        )
        
        # Message with profanity
        result = await openai_service.parse_task("Купить fucking молоко")
        
        # Check that profanity was filtered
        create_call = openai_service.instructor_client.chat.completions.create
        assert create_call.called
        messages = create_call.call_args[1]["messages"]
        assert "*" in messages[1]["content"]

    @pytest.mark.asyncio
    async def test_parse_task_short_message(self, openai_service):
        """Test parsing very short message."""
        with pytest.raises(ValidationError, match="Message is too short"):
            await openai_service.parse_task("Hi")

    @pytest.mark.asyncio
    async def test_parse_task_english(self, openai_service):
        """Test parsing with English language."""
        mock_task = TaskSchema(content="Buy milk")
        
        openai_service.instructor_client.chat.completions.create = AsyncMock(
            return_value=mock_task
        )
        
        result = await openai_service.parse_task("Buy milk", user_language="en")
        
        # Check English system prompt was used
        create_call = openai_service.instructor_client.chat.completions.create
        messages = create_call.call_args[1]["messages"]
        assert "You are an assistant" in messages[0]["content"]

    @pytest.mark.asyncio
    async def test_parse_task_openai_error(self, openai_service):
        """Test handling OpenAI API error."""
        openai_service.instructor_client.chat.completions.create = AsyncMock(
            side_effect=Exception("API Error")
        )
        
        with pytest.raises(OpenAIError, match="Failed to parse task"):
            await openai_service.parse_task("Test message")

    @pytest.mark.asyncio
    async def test_close(self, openai_service):
        """Test closing the service."""
        openai_service.client.close = AsyncMock()
        
        await openai_service.close()
        
        openai_service.client.close.assert_called_once()