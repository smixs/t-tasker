"""Tests for OpenAI intent parsing."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from src.models.intent import TaskCreation, CommandExecution, Intent
from src.models.task import TaskSchema
from src.services.openai_service import OpenAIService


@pytest.fixture
def openai_service():
    """Create OpenAI service instance."""
    return OpenAIService()


@pytest.fixture
def mock_instructor_client():
    """Mock instructor client."""
    with patch("src.services.openai_service.instructor") as mock:
        yield mock


class TestParseIntent:
    """Test parse_intent method."""

    @pytest.mark.asyncio
    async def test_parse_task_creation_intent(self, openai_service, mock_instructor_client):
        """Test parsing task creation intent."""
        # Mock response
        expected_task = TaskSchema(
            content="Купить молоко",
            due_string="завтра",
            priority=1
        )
        expected_intent = TaskCreation(
            type="create_task",
            task=expected_task
        )
        
        # Setup mock
        mock_create = AsyncMock(return_value=expected_intent)
        openai_service.instructor_client.chat.completions.create = mock_create
        
        # Test
        result = await openai_service.parse_intent("Купить молоко завтра")
        
        # Verify
        assert isinstance(result, TaskCreation)
        assert result.type == "create_task"
        assert result.task.content == "Купить молоко"
        assert result.task.due_string == "завтра"
        
        # Check API call
        mock_create.assert_called_once()
        call_args = mock_create.call_args[1]
        assert call_args["response_model"] == Intent
        assert call_args["temperature"] == 0.2

    @pytest.mark.asyncio
    async def test_parse_view_command_intent(self, openai_service, mock_instructor_client):
        """Test parsing view tasks command."""
        # Mock response
        expected_intent = CommandExecution(
            type="command",
            command_type="view_tasks",
            target="today"
        )
        
        # Setup mock
        mock_create = AsyncMock(return_value=expected_intent)
        openai_service.instructor_client.chat.completions.create = mock_create
        
        # Test
        result = await openai_service.parse_intent("Покажи задачи на сегодня")
        
        # Verify
        assert isinstance(result, CommandExecution)
        assert result.type == "command"
        assert result.command_type == "view_tasks"
        assert result.target == "today"

    @pytest.mark.asyncio
    async def test_parse_delete_command_intent(self, openai_service, mock_instructor_client):
        """Test parsing delete task command."""
        # Mock response
        expected_intent = CommandExecution(
            type="command",
            command_type="delete_task",
            target="last"
        )
        
        # Setup mock
        mock_create = AsyncMock(return_value=expected_intent)
        openai_service.instructor_client.chat.completions.create = mock_create
        
        # Test
        result = await openai_service.parse_intent("Удали последнюю задачу")
        
        # Verify
        assert isinstance(result, CommandExecution)
        assert result.command_type == "delete_task"
        assert result.target == "last"

    @pytest.mark.asyncio
    async def test_parse_update_command_intent(self, openai_service, mock_instructor_client):
        """Test parsing update task command."""
        # Mock response
        expected_intent = CommandExecution(
            type="command",
            command_type="update_task",
            target="last",
            updates={"priority": 4}
        )
        
        # Setup mock
        mock_create = AsyncMock(return_value=expected_intent)
        openai_service.instructor_client.chat.completions.create = mock_create
        
        # Test
        result = await openai_service.parse_intent("Сделай последнюю задачу срочной")
        
        # Verify
        assert isinstance(result, CommandExecution)
        assert result.command_type == "update_task"
        assert result.updates == {"priority": 4}

    @pytest.mark.asyncio
    async def test_parse_complete_command_intent(self, openai_service, mock_instructor_client):
        """Test parsing complete task command."""
        # Mock response
        expected_intent = CommandExecution(
            type="command",
            command_type="complete_task",
            target="last"
        )
        
        # Setup mock
        mock_create = AsyncMock(return_value=expected_intent)
        openai_service.instructor_client.chat.completions.create = mock_create
        
        # Test
        result = await openai_service.parse_intent("Отметь последнюю задачу выполненной")
        
        # Verify
        assert isinstance(result, CommandExecution)
        assert result.command_type == "complete_task"

    @pytest.mark.asyncio
    async def test_parse_intent_english(self, openai_service, mock_instructor_client):
        """Test parsing intent in English."""
        # Mock response
        expected_intent = CommandExecution(
            type="command",
            command_type="view_tasks",
            target="tomorrow"
        )
        
        # Setup mock
        mock_create = AsyncMock(return_value=expected_intent)
        openai_service.instructor_client.chat.completions.create = mock_create
        
        # Test
        result = await openai_service.parse_intent("Show tomorrow's tasks", user_language="en")
        
        # Verify
        assert isinstance(result, CommandExecution)
        assert result.command_type == "view_tasks"
        assert result.target == "tomorrow"
        
        # Check that English prompt was used
        call_args = mock_create.call_args[1]
        messages = call_args["messages"]
        assert "intelligent intent classifier" in messages[0]["content"]

    @pytest.mark.asyncio
    async def test_parse_intent_short_message(self, openai_service):
        """Test parsing intent with too short message."""
        from src.core.exceptions import ValidationError
        
        with pytest.raises(ValidationError) as exc_info:
            await openai_service.parse_intent("a")
        
        assert "too short" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_parse_intent_profanity_filter(self, openai_service, mock_instructor_client):
        """Test profanity filtering in intent parsing."""
        # Mock response
        expected_task = TaskSchema(content="Купить ****")
        expected_intent = TaskCreation(
            type="create_task",
            task=expected_task
        )
        
        # Setup mock
        mock_create = AsyncMock(return_value=expected_intent)
        openai_service.instructor_client.chat.completions.create = mock_create
        
        # Test with profanity
        result = await openai_service.parse_intent("Купить shit")
        
        # Verify profanity was filtered
        call_args = mock_create.call_args[1]
        user_message = call_args["messages"][1]["content"]
        assert "shit" not in user_message
        assert "****" in user_message or "Купить" in user_message