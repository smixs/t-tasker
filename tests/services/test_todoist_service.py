"""Tests for Todoist service."""

import json
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from src.core.exceptions import InvalidTokenError, QuotaExceededError, RateLimitError, TodoistError
from src.services.todoist_service import RateLimiter, TodoistService


@pytest.fixture
def todoist_service():
    """Create Todoist service instance."""
    return TodoistService(api_token="test_token_123")


@pytest.fixture
def mock_httpx_client():
    """Create mock httpx client."""
    client = AsyncMock(spec=httpx.AsyncClient)
    return client


class TestTodoistService:
    """Test Todoist service functionality."""

    async def test_validate_token_success(self, todoist_service, mock_httpx_client):
        """Test successful token validation."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "email": "test@example.com",
            "full_name": "Test User",
            "id": "123456",
        }
        mock_httpx_client.get.return_value = mock_response

        with patch.object(todoist_service, "_get_client", return_value=mock_httpx_client):
            result = await todoist_service.validate_token()

        assert result["email"] == "test@example.com"
        assert result["full_name"] == "Test User"
        mock_httpx_client.get.assert_called_once_with(
            "https://api.todoist.com/sync/v9/user",
            headers=todoist_service.headers,
        )

    async def test_validate_token_invalid(self, todoist_service, mock_httpx_client):
        """Test token validation with invalid token."""
        mock_response = MagicMock()
        mock_response.status_code = 401
        mock_httpx_client.get.return_value = mock_response

        with patch.object(todoist_service, "_get_client", return_value=mock_httpx_client):
            with pytest.raises(InvalidTokenError):
                await todoist_service.validate_token()

    async def test_validate_token_quota_exceeded(self, todoist_service, mock_httpx_client):
        """Test token validation with quota exceeded."""
        mock_response = MagicMock()
        mock_response.status_code = 403
        mock_httpx_client.get.return_value = mock_response

        with patch.object(todoist_service, "_get_client", return_value=mock_httpx_client):
            with pytest.raises(QuotaExceededError):
                await todoist_service.validate_token()

    async def test_create_task_success(self, todoist_service, mock_httpx_client):
        """Test successful task creation."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "id": "2995104339",
            "content": "Test task",
            "description": "Test description",
            "priority": 4,
            "labels": ["test"],
        }
        mock_httpx_client.post.return_value = mock_response

        with patch.object(todoist_service, "_get_client", return_value=mock_httpx_client):
            with patch.object(todoist_service._rate_limiter, "acquire", new_callable=AsyncMock):
                result = await todoist_service.create_task(
                    content="Test task",
                    description="Test description",
                    priority=4,
                    labels=["test"],
                )

        assert result["content"] == "Test task"
        assert result["priority"] == 4
        mock_httpx_client.post.assert_called_once()

    async def test_create_task_with_all_params(self, todoist_service, mock_httpx_client):
        """Test task creation with all parameters."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"id": "123", "content": "Task"}
        mock_httpx_client.post.return_value = mock_response

        with patch.object(todoist_service, "_get_client", return_value=mock_httpx_client):
            with patch.object(todoist_service._rate_limiter, "acquire", new_callable=AsyncMock):
                await todoist_service.create_task(
                    content="Test task",
                    description="Description",
                    project_id="proj123",
                    section_id="sec123",
                    parent_id="parent123",
                    labels=["label1", "label2"],
                    priority=3,
                    due_string="tomorrow at 10am",
                    duration=30,
                    duration_unit="minute",
                )

        # Check the request body
        call_args = mock_httpx_client.post.call_args
        request_data = call_args.kwargs["json"]
        assert request_data["content"] == "Test task"
        assert request_data["description"] == "Description"
        assert request_data["project_id"] == "proj123"
        assert request_data["labels"] == ["label1", "label2"]
        assert request_data["duration"] == 30

    async def test_create_task_rate_limit(self, todoist_service, mock_httpx_client):
        """Test task creation with rate limit error."""
        mock_response = MagicMock()
        mock_response.status_code = 429
        mock_response.headers = {"Retry-After": "120"}
        mock_httpx_client.post.return_value = mock_response

        with patch.object(todoist_service, "_get_client", return_value=mock_httpx_client):
            with patch.object(todoist_service._rate_limiter, "acquire", new_callable=AsyncMock):
                with pytest.raises(RateLimitError) as exc_info:
                    await todoist_service.create_task(content="Test task")
                
                assert exc_info.value.retry_after == 120

    async def test_get_projects_success(self, todoist_service, mock_httpx_client):
        """Test getting projects."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = [
            {"id": "1", "name": "Inbox"},
            {"id": "2", "name": "Work"},
        ]
        mock_httpx_client.get.return_value = mock_response

        with patch.object(todoist_service, "_get_client", return_value=mock_httpx_client):
            with patch.object(todoist_service._rate_limiter, "acquire", new_callable=AsyncMock):
                result = await todoist_service.get_projects()

        assert len(result) == 2
        assert result[0]["name"] == "Inbox"
        assert result[1]["name"] == "Work"

    async def test_get_projects_cached(self, todoist_service, mock_httpx_client):
        """Test getting projects from cache."""
        # First call - should hit API
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = [{"id": "1", "name": "Inbox"}]
        mock_httpx_client.get.return_value = mock_response

        with patch.object(todoist_service, "_get_client", return_value=mock_httpx_client):
            with patch.object(todoist_service._rate_limiter, "acquire", new_callable=AsyncMock):
                result1 = await todoist_service.get_projects()
                # Second call - should use cache
                result2 = await todoist_service.get_projects()

        assert result1 == result2
        # Should only be called once due to caching
        assert mock_httpx_client.get.call_count == 1

    async def test_get_project_by_name(self, todoist_service, mock_httpx_client):
        """Test getting project by name."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = [
            {"id": "1", "name": "Inbox"},
            {"id": "2", "name": "Work"},
        ]
        mock_httpx_client.get.return_value = mock_response

        with patch.object(todoist_service, "_get_client", return_value=mock_httpx_client):
            with patch.object(todoist_service._rate_limiter, "acquire", new_callable=AsyncMock):
                result = await todoist_service.get_project_by_name("work")

        assert result is not None
        assert result["id"] == "2"
        assert result["name"] == "Work"

    async def test_get_project_by_name_not_found(self, todoist_service, mock_httpx_client):
        """Test getting non-existent project by name."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = [{"id": "1", "name": "Inbox"}]
        mock_httpx_client.get.return_value = mock_response

        with patch.object(todoist_service, "_get_client", return_value=mock_httpx_client):
            with patch.object(todoist_service._rate_limiter, "acquire", new_callable=AsyncMock):
                result = await todoist_service.get_project_by_name("NonExistent")

        assert result is None

    async def test_network_error_handling(self, todoist_service, mock_httpx_client):
        """Test network error handling."""
        mock_httpx_client.get.side_effect = httpx.RequestError("Network error")

        with patch.object(todoist_service, "_get_client", return_value=mock_httpx_client):
            with pytest.raises(TodoistError) as exc_info:
                await todoist_service.validate_token()
            
            assert "Network error" in str(exc_info.value)


class TestRateLimiter:
    """Test rate limiter functionality."""

    async def test_rate_limiter_allows_requests(self):
        """Test rate limiter allows requests within limit."""
        limiter = RateLimiter(max_requests=5, window_seconds=60)
        
        # Should allow 5 requests
        for _ in range(5):
            await limiter.acquire()
        
        # 6th request should raise
        with pytest.raises(RateLimitError):
            await limiter.acquire()

    async def test_rate_limiter_window_expiry(self):
        """Test rate limiter window expiry."""
        limiter = RateLimiter(max_requests=2, window_seconds=1)
        
        # Use up the limit
        await limiter.acquire()
        await limiter.acquire()
        
        # Should be rate limited
        with pytest.raises(RateLimitError):
            await limiter.acquire()
        
        # Wait for window to expire
        await asyncio.sleep(1.1)
        
        # Should allow new request
        await limiter.acquire()

    async def test_rate_limiter_retry_after(self):
        """Test rate limiter provides correct retry_after."""
        limiter = RateLimiter(max_requests=1, window_seconds=60)
        
        # First request
        await limiter.acquire()
        
        # Second request should fail with retry_after
        with pytest.raises(RateLimitError) as exc_info:
            await limiter.acquire()
        
        # Retry after should be around 60 seconds
        assert 55 <= exc_info.value.retry_after <= 60