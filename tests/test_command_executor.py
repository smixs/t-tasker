"""Tests for command executor."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime

from src.models.intent import CommandExecution
from src.services.command_executor import CommandExecutor
from src.core.exceptions import BotError


@pytest.fixture
def command_executor():
    """Create CommandExecutor instance."""
    return CommandExecutor()


@pytest.fixture
def mock_todoist_service():
    """Mock TodoistService."""
    with patch("src.services.command_executor.TodoistService") as mock:
        service_instance = AsyncMock()
        mock.return_value.__aenter__.return_value = service_instance
        yield service_instance


@pytest.fixture
def mock_db_session():
    """Mock database session."""
    with patch("src.services.command_executor.get_database") as mock_db:
        session = AsyncMock()
        mock_db.return_value.get_session.return_value.__aenter__.return_value = session
        yield session


@pytest.fixture
def mock_task_repo():
    """Mock TaskRepository."""
    with patch("src.services.command_executor.TaskRepository") as mock:
        repo_instance = AsyncMock()
        mock.return_value = repo_instance
        yield repo_instance


class TestViewTasks:
    """Test _view_tasks method."""

    @pytest.mark.asyncio
    async def test_view_today_tasks(self, command_executor, mock_todoist_service):
        """Test viewing today's tasks."""
        # Setup command
        command = CommandExecution(
            type="command",
            command_type="view_tasks",
            target="today"
        )
        
        # Mock tasks
        mock_tasks = [
            {
                "id": "1",
                "content": "Test task 1",
                "priority": 1,
                "due": {"date": "2024-01-19"},
                "labels": ["work"]
            },
            {
                "id": "2",
                "content": "Test task 2",
                "priority": 4,
                "due": {"datetime": "2024-01-19T15:00:00Z"}
            }
        ]
        mock_todoist_service.get_tasks.return_value = mock_tasks
        mock_todoist_service.get_projects.return_value = []
        
        # Execute
        result = await command_executor.execute(command, user_id=123, todoist_token="token")
        
        # Verify
        assert "📅 Задачи на сегодня" in result
        assert "Test task 1" in result
        assert "Test task 2" in result
        assert "🔴" in result  # High priority emoji
        assert "15:00" in result  # Time from datetime
        
        # Check API call
        mock_todoist_service.get_tasks.assert_called_once_with(
            filter_string="today",
            limit=20
        )

    @pytest.mark.asyncio
    async def test_view_empty_tasks(self, command_executor, mock_todoist_service):
        """Test viewing when no tasks found."""
        command = CommandExecution(
            type="command",
            command_type="view_tasks",
            target="tomorrow"
        )
        
        # Mock empty response
        mock_todoist_service.get_tasks.return_value = []
        
        # Execute
        result = await command_executor.execute(command, user_id=123, todoist_token="token")
        
        # Verify
        assert "📆 Задачи на завтра" in result
        assert "Задач не найдено" in result

    @pytest.mark.asyncio
    async def test_view_priority_tasks(self, command_executor, mock_todoist_service):
        """Test viewing tasks filtered by priority."""
        command = CommandExecution(
            type="command",
            command_type="view_tasks",
            target="all",
            filters={"priority": 3}
        )
        
        # Mock tasks
        mock_tasks = [{"id": "1", "content": "High priority task", "priority": 3}]
        mock_todoist_service.get_tasks.return_value = mock_tasks
        mock_todoist_service.get_projects.return_value = []
        
        # Execute
        result = await command_executor.execute(command, user_id=123, todoist_token="token")
        
        # Verify
        assert "🔴 Задачи с приоритетом 3" in result
        assert "High priority task" in result
        
        # Check API call with priority filter
        mock_todoist_service.get_tasks.assert_called_once_with(
            filter_string="p3",
            limit=20
        )


class TestDeleteTask:
    """Test _delete_task method."""

    @pytest.mark.asyncio
    async def test_delete_last_task_success(
        self, command_executor, mock_todoist_service, mock_db_session, mock_task_repo
    ):
        """Test successfully deleting last task."""
        command = CommandExecution(
            type="command",
            command_type="delete_task",
            target="last"
        )
        
        # Mock last task
        mock_task = MagicMock()
        mock_task.id = 1
        mock_task.todoist_id = "todoist123"
        mock_task.task_data = {"content": "Task to delete"}
        mock_task_repo.get_last_task.return_value = mock_task
        
        # Mock successful deletion
        mock_todoist_service.delete_task.return_value = True
        
        # Execute
        result = await command_executor.execute(command, user_id=123, todoist_token="token")
        
        # Verify
        assert "✅ Удалена задача:" in result
        assert "Task to delete" in result
        
        # Check calls
        mock_task_repo.get_last_task.assert_called_once_with(123)
        mock_todoist_service.delete_task.assert_called_once_with("todoist123")
        mock_task_repo.delete_task_record.assert_called_once_with(1)

    @pytest.mark.asyncio
    async def test_delete_no_last_task(
        self, command_executor, mock_db_session, mock_task_repo
    ):
        """Test deleting when no last task exists."""
        command = CommandExecution(
            type="command",
            command_type="delete_task",
            target="last"
        )
        
        # Mock no last task
        mock_task_repo.get_last_task.return_value = None
        
        # Execute
        result = await command_executor.execute(command, user_id=123, todoist_token="token")
        
        # Verify
        assert "❌ Последняя задача не найдена" in result

    @pytest.mark.asyncio
    async def test_delete_unsupported_target(self, command_executor):
        """Test deleting with unsupported target."""
        command = CommandExecution(
            type="command",
            command_type="delete_task",
            target="all"
        )
        
        # Execute
        result = await command_executor.execute(command, user_id=123, todoist_token="token")
        
        # Verify
        assert "❌ Пока поддерживается только удаление последней задачи" in result


class TestUpdateTask:
    """Test _update_task method."""

    @pytest.mark.asyncio
    async def test_update_priority(
        self, command_executor, mock_todoist_service, mock_db_session, mock_task_repo
    ):
        """Test updating task priority."""
        command = CommandExecution(
            type="command",
            command_type="update_task",
            target="last",
            updates={"priority": 4}
        )
        
        # Mock last task
        mock_task = MagicMock()
        mock_task.todoist_id = "todoist123"
        mock_task.task_data = {"content": "Test task"}
        mock_task_repo.get_last_task.return_value = mock_task
        
        # Mock successful update
        mock_todoist_service.update_task.return_value = {"id": "todoist123", "priority": 4}
        
        # Execute
        result = await command_executor.execute(command, user_id=123, todoist_token="token")
        
        # Verify
        assert "✅ Обновлена задача:" in result
        assert "Test task" in result
        assert "приоритет → срочный" in result
        
        # Check API call
        mock_todoist_service.update_task.assert_called_once_with(
            "todoist123",
            priority=4
        )

    @pytest.mark.asyncio
    async def test_update_multiple_fields(
        self, command_executor, mock_todoist_service, mock_db_session, mock_task_repo
    ):
        """Test updating multiple fields."""
        command = CommandExecution(
            type="command",
            command_type="update_task",
            target="last",
            updates={
                "priority": 3,
                "due_string": "tomorrow at 15:00"
            }
        )
        
        # Mock last task
        mock_task = MagicMock()
        mock_task.todoist_id = "todoist123"
        mock_task.task_data = {"content": "Test task"}
        mock_task_repo.get_last_task.return_value = mock_task
        
        # Execute
        result = await command_executor.execute(command, user_id=123, todoist_token="token")
        
        # Verify
        assert "приоритет → высокий" in result
        assert "срок → tomorrow at 15:00" in result

    @pytest.mark.asyncio
    async def test_update_no_updates(self, command_executor):
        """Test update command without updates."""
        command = CommandExecution(
            type="command",
            command_type="update_task",
            target="last",
            updates=None
        )
        
        # Execute
        result = await command_executor.execute(command, user_id=123, todoist_token="token")
        
        # Verify
        assert "❌ Не указаны изменения для задачи" in result


class TestCompleteTask:
    """Test _complete_task method."""

    @pytest.mark.asyncio
    async def test_complete_last_task_success(
        self, command_executor, mock_todoist_service, mock_db_session, mock_task_repo
    ):
        """Test successfully completing last task."""
        command = CommandExecution(
            type="command",
            command_type="complete_task",
            target="last"
        )
        
        # Mock last task
        mock_task = MagicMock()
        mock_task.todoist_id = "todoist123"
        mock_task.task_data = {"content": "Task to complete"}
        mock_task_repo.get_last_task.return_value = mock_task
        
        # Mock successful completion
        mock_todoist_service.complete_task.return_value = True
        
        # Execute
        result = await command_executor.execute(command, user_id=123, todoist_token="token")
        
        # Verify
        assert "✅ Выполнена задача:" in result
        assert "Task to complete" in result
        
        # Check API call
        mock_todoist_service.complete_task.assert_called_once_with("todoist123")

    @pytest.mark.asyncio
    async def test_complete_failed(
        self, command_executor, mock_todoist_service, mock_db_session, mock_task_repo
    ):
        """Test failed task completion."""
        command = CommandExecution(
            type="command",
            command_type="complete_task",
            target="last"
        )
        
        # Mock last task
        mock_task = MagicMock()
        mock_task.todoist_id = "todoist123"
        mock_task.task_data = {"content": "Task"}
        mock_task_repo.get_last_task.return_value = mock_task
        
        # Mock failed completion
        mock_todoist_service.complete_task.return_value = False
        
        # Execute
        result = await command_executor.execute(command, user_id=123, todoist_token="token")
        
        # Verify
        assert "❌ Не удалось отметить задачу выполненной" in result


class TestGeneralExecution:
    """Test general command execution."""

    @pytest.mark.asyncio
    async def test_unknown_command_type(self, command_executor, monkeypatch):
        """Test handling unknown command type."""
        # Create a valid command but mock it to have unknown type
        command = CommandExecution(
            type="command",
            command_type="view_tasks",  # Valid type for creation
            target="last"
        )
        
        # Monkey patch the command_type to an invalid value after creation
        monkeypatch.setattr(command, "command_type", "unknown_command")
        
        # Execute and expect error
        with pytest.raises(BotError) as exc_info:
            await command_executor.execute(command, user_id=123, todoist_token="token")
        
        assert "Unknown command type" in str(exc_info.value)