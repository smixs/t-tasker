"""Tests for Todoist service extensions."""

import pytest
from unittest.mock import AsyncMock, MagicMock
import httpx

from src.services.todoist_service import TodoistService
from src.core.exceptions import TodoistError, InvalidTokenError


@pytest.fixture
def todoist_service():
    """Create TodoistService instance."""
    return TodoistService(api_token="test_token")


@pytest.fixture
def mock_http_client(monkeypatch):
    """Mock httpx.AsyncClient."""
    mock_client = AsyncMock()
    mock_response = MagicMock()  # Use MagicMock for response to avoid async issues
    
    # Setup default successful response
    mock_response.status_code = 200
    mock_response.json.return_value = []
    mock_response.content = b'[]'
    mock_response.headers = {}
    
    # Make get and post return the mock response
    mock_client.get = AsyncMock(return_value=mock_response)
    mock_client.post = AsyncMock(return_value=mock_response)
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=None)
    
    # Mock the client creation
    def mock_get_client(self):
        return mock_client
    
    monkeypatch.setattr(TodoistService, "_get_client", mock_get_client)
    
    return mock_client, mock_response


class TestGetTasks:
    """Test get_tasks method."""

    @pytest.mark.asyncio
    async def test_get_tasks_no_filter(self, todoist_service, mock_http_client):
        """Test getting tasks without filter."""
        mock_client, mock_response = mock_http_client
        
        # Mock response data
        test_tasks = [
            {"id": "1", "content": "Task 1", "created_at": "2024-01-02T00:00:00Z"},
            {"id": "2", "content": "Task 2", "created_at": "2024-01-01T00:00:00Z"},
        ]
        mock_response.json.return_value = test_tasks
        
        # Test
        tasks = await todoist_service.get_tasks()
        
        # Verify API call
        mock_client.get.assert_called_once_with(
            "https://api.todoist.com/rest/v2/tasks",
            headers=todoist_service.headers,
            params={}
        )
        
        # Verify sorting (newest first)
        assert len(tasks) == 2
        assert tasks[0]["id"] == "1"  # Newer task first

    @pytest.mark.asyncio
    async def test_get_tasks_with_today_filter(self, todoist_service, mock_http_client):
        """Test getting tasks with 'today' filter."""
        mock_client, mock_response = mock_http_client
        
        test_tasks = [{"id": "1", "content": "Today's task"}]
        mock_response.json.return_value = test_tasks
        
        # Test
        tasks = await todoist_service.get_tasks(filter_string="today")
        
        # Verify API call with filter
        mock_client.get.assert_called_once()
        call_args = mock_client.get.call_args
        assert call_args[1]["params"]["filter"] == "today"
        
        assert len(tasks) == 1

    @pytest.mark.asyncio
    async def test_get_tasks_with_priority_filter(self, todoist_service, mock_http_client):
        """Test getting tasks with priority filter."""
        mock_client, mock_response = mock_http_client
        
        # Mock response with mixed priorities
        test_tasks = [
            {"id": "1", "content": "High priority", "priority": 3},
            {"id": "2", "content": "Normal priority", "priority": 1},
            {"id": "3", "content": "Also high", "priority": 3},
        ]
        mock_response.json.return_value = test_tasks
        
        # Test
        tasks = await todoist_service.get_tasks(filter_string="p3")
        
        # Verify client-side filtering
        assert len(tasks) == 2
        assert all(t["priority"] == 3 for t in tasks)

    @pytest.mark.asyncio
    async def test_get_tasks_with_project_filter(self, todoist_service, mock_http_client):
        """Test getting tasks filtered by project."""
        mock_client, mock_response = mock_http_client
        
        test_tasks = [{"id": "1", "content": "Project task"}]
        mock_response.json.return_value = test_tasks
        
        # Test
        tasks = await todoist_service.get_tasks(project_id="project123")
        
        # Verify API call with project_id
        call_args = mock_client.get.call_args
        assert call_args[1]["params"]["project_id"] == "project123"

    @pytest.mark.asyncio
    async def test_get_tasks_with_limit(self, todoist_service, mock_http_client):
        """Test limiting number of returned tasks."""
        mock_client, mock_response = mock_http_client
        
        # Mock many tasks
        test_tasks = [{"id": str(i), "content": f"Task {i}"} for i in range(50)]
        mock_response.json.return_value = test_tasks
        
        # Test
        tasks = await todoist_service.get_tasks(limit=5)
        
        # Verify limit applied
        assert len(tasks) == 5

    @pytest.mark.asyncio
    async def test_get_tasks_error_handling(self, todoist_service, mock_http_client):
        """Test error handling in get_tasks."""
        mock_client, mock_response = mock_http_client
        
        # Test 401 error
        mock_response.status_code = 401
        with pytest.raises(InvalidTokenError):
            await todoist_service.get_tasks()


class TestGetRecentTasks:
    """Test get_recent_tasks method."""

    @pytest.mark.asyncio
    async def test_get_recent_tasks(self, todoist_service, mock_http_client):
        """Test getting recent tasks."""
        mock_client, mock_response = mock_http_client
        
        # Mock response data
        test_tasks = [
            {"id": "1", "content": "Newest", "created_at": "2024-01-03T00:00:00Z"},
            {"id": "2", "content": "Middle", "created_at": "2024-01-02T00:00:00Z"},
            {"id": "3", "content": "Oldest", "created_at": "2024-01-01T00:00:00Z"},
        ]
        mock_response.json.return_value = test_tasks
        
        # Test
        tasks = await todoist_service.get_recent_tasks(limit=2)
        
        # Verify
        assert len(tasks) == 2
        assert tasks[0]["id"] == "1"  # Newest first
        assert tasks[1]["id"] == "2"


class TestReopenTask:
    """Test reopen_task method."""

    @pytest.mark.asyncio
    async def test_reopen_task_success(self, todoist_service, mock_http_client):
        """Test successfully reopening a task."""
        mock_client, mock_response = mock_http_client
        
        # Mock successful response (204 No Content)
        mock_response.status_code = 204
        
        # Test
        result = await todoist_service.reopen_task("task123")
        
        # Verify API call
        mock_client.post.assert_called_once_with(
            "https://api.todoist.com/rest/v2/tasks/task123/reopen",
            headers=todoist_service.headers
        )
        
        assert result is True

    @pytest.mark.asyncio
    async def test_reopen_task_not_found(self, todoist_service, mock_http_client):
        """Test reopening non-existent task."""
        mock_client, mock_response = mock_http_client
        
        # Mock 404 response
        mock_response.status_code = 404
        
        # Test
        result = await todoist_service.reopen_task("nonexistent")
        
        assert result is False

    @pytest.mark.asyncio
    async def test_reopen_task_error(self, todoist_service, mock_http_client):
        """Test error handling in reopen_task."""
        mock_client, mock_response = mock_http_client
        
        # Mock server error
        mock_response.status_code = 500
        mock_response.content = b'{"error": "Server error"}'
        mock_response.json.return_value = {"error": "Server error"}
        
        # Test
        with pytest.raises(TodoistError) as exc_info:
            await todoist_service.reopen_task("task123")
        
        assert "Failed to reopen task" in str(exc_info.value)