"""Tests for command handlers."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, User

from src.handlers.commands import cmd_start, cmd_help, cmd_setup, cmd_status, SetupStates


class TestCommandHandlers:
    """Test command handlers."""

    @pytest.fixture
    def mock_message(self):
        """Create mock message."""
        message = MagicMock(spec=Message)
        message.answer = AsyncMock()
        message.delete = AsyncMock()
        message.from_user = MagicMock(spec=User)
        message.from_user.id = 123456789
        message.from_user.username = "testuser"
        message.from_user.first_name = "Test"
        message.from_user.last_name = "User"
        message.from_user.language_code = "ru"
        return message

    @pytest.fixture
    def mock_state(self):
        """Create mock FSM state."""
        state = MagicMock(spec=FSMContext)
        state.set_state = AsyncMock()
        state.get_state = AsyncMock()
        state.clear = AsyncMock()
        return state

    @pytest.mark.asyncio
    async def test_cmd_start(self, mock_message):
        """Test /start command."""
        with patch('src.handlers.commands.get_database') as mock_db:
            mock_session = AsyncMock()
            mock_db.return_value.get_session.return_value.__aenter__.return_value = mock_session
            
            with patch('src.handlers.commands.UserRepository') as mock_repo:
                mock_repo.return_value.create_or_update = AsyncMock()
                
                await cmd_start(mock_message)
                
                # Check user was created/updated
                mock_repo.return_value.create_or_update.assert_called_once_with(
                    user_id=123456789,
                    username="testuser",
                    first_name="Test",
                    last_name="User",
                    language_code="ru"
                )
                
                # Check welcome message
                mock_message.answer.assert_called_once()
                args = mock_message.answer.call_args[0]
                assert "Привет" in args[0]
                assert "/setup" in args[0]

    @pytest.mark.asyncio
    async def test_cmd_help(self, mock_message):
        """Test /help command."""
        await cmd_help(mock_message)
        
        # Check help message
        mock_message.answer.assert_called_once()
        args = mock_message.answer.call_args
        assert "Как использовать бота" in args[0][0]
        assert args[1]["parse_mode"] == "Markdown"

    @pytest.mark.asyncio
    async def test_cmd_setup(self, mock_message, mock_state):
        """Test /setup command."""
        await cmd_setup(mock_message, mock_state)
        
        # Check state was set
        mock_state.set_state.assert_called_once_with(SetupStates.waiting_for_token)
        
        # Check instructions message
        mock_message.answer.assert_called_once()
        args = mock_message.answer.call_args
        assert "Настройка подключения" in args[0][0]
        assert "Todoist Settings" in args[0][0]
        assert args[1]["parse_mode"] == "Markdown"
        assert args[1]["disable_web_page_preview"] is True

    @pytest.mark.asyncio
    async def test_cmd_status_no_token(self, mock_message):
        """Test /status command without token."""
        with patch('src.handlers.commands.get_database') as mock_db:
            mock_session = AsyncMock()
            mock_db.return_value.get_session.return_value.__aenter__.return_value = mock_session
            
            with patch('src.handlers.commands.UserRepository') as mock_repo:
                # User without token
                mock_user = MagicMock()
                mock_user.todoist_token_encrypted = None
                mock_repo.return_value.get_by_id = AsyncMock(return_value=mock_user)
                
                await cmd_status(mock_message)
                
                # Check error message
                mock_message.answer.assert_called_once()
                args = mock_message.answer.call_args[0]
                assert "Todoist не подключен" in args[0]
                assert "/setup" in args[0]

    @pytest.mark.asyncio
    async def test_cmd_status_with_token(self, mock_message):
        """Test /status command with token."""
        from datetime import datetime
        
        with patch('src.handlers.commands.get_database') as mock_db:
            mock_session = AsyncMock()
            mock_db.return_value.get_session.return_value.__aenter__.return_value = mock_session
            
            with patch('src.handlers.commands.UserRepository') as mock_repo:
                # User with token
                mock_user = MagicMock()
                mock_user.todoist_token_encrypted = "encrypted_token"
                mock_user.tasks_created = 42
                mock_user.last_task_at = datetime(2025, 1, 19, 15, 30)
                mock_repo.return_value.get_by_id = AsyncMock(return_value=mock_user)
                
                await cmd_status(mock_message)
                
                # Check status message
                mock_message.answer.assert_called_once()
                args = mock_message.answer.call_args[0]
                assert "Todoist подключен" in args[0]
                assert "42" in args[0]
                assert "19.01.2025" in args[0]