"""Todoist API service for task management."""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Any

import httpx

from src.core.exceptions import InvalidTokenError, QuotaExceededError, RateLimitError, TodoistError

logger = logging.getLogger(__name__)


class TodoistService:
    """Service for interacting with Todoist API."""

    BASE_URL = "https://api.todoist.com/rest/v2"
    SYNC_URL = "https://api.todoist.com/sync/v9"

    def __init__(self, api_token: str) -> None:
        """Initialize Todoist service.

        Args:
            api_token: Personal API token for Todoist
        """
        self.api_token = api_token
        self.headers = {
            "Authorization": f"Bearer {api_token}",
            "Content-Type": "application/json",
        }
        self._client: httpx.AsyncClient | None = None
        self._rate_limiter = RateLimiter(max_requests=450, window_seconds=900)  # 450 req/15 min
        self._projects_cache: list[dict[str, Any]] | None = None
        self._labels_cache: list[dict[str, Any]] | None = None
        self._cache_expiry: datetime | None = None

    async def __aenter__(self) -> "TodoistService":
        """Async context manager entry."""
        self._client = httpx.AsyncClient(timeout=30.0)
        return self

    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Async context manager exit."""
        if self._client:
            await self._client.aclose()

    async def validate_token(self) -> dict[str, Any]:
        """Validate the API token and return user info.

        Returns:
            User information from Todoist

        Raises:
            InvalidTokenError: If token is invalid
            TodoistError: For other API errors
        """
        try:
            async with self._get_client() as client:
                response = await client.get(
                    f"{self.SYNC_URL}/user",
                    headers=self.headers,
                )

                if response.status_code == 401:
                    raise InvalidTokenError()
                elif response.status_code == 403:
                    raise QuotaExceededError()
                elif response.status_code != 200:
                    raise TodoistError(f"API error: {response.status_code}")

                return response.json()
        except httpx.RequestError as e:
            logger.error(f"Network error validating token: {e}")
            raise TodoistError(f"Network error: {str(e)}")

    async def create_task(
        self,
        content: str,
        description: str | None = None,
        project_id: str | None = None,
        section_id: str | None = None,
        parent_id: str | None = None,
        labels: list[str] | None = None,
        priority: int = 1,
        due_string: str | None = None,
        due_date: str | None = None,
        due_datetime: str | None = None,
        duration: int | None = None,
        duration_unit: str | None = None,
    ) -> dict[str, Any]:
        """Create a new task in Todoist.

        Args:
            content: Task content/title
            description: Task description
            project_id: Project ID to add task to
            section_id: Section ID within project
            parent_id: Parent task ID for subtasks
            labels: List of label names
            priority: Priority level 1-4 (4 is highest)
            due_string: Human-readable due date string
            due_date: Due date in YYYY-MM-DD format
            due_datetime: Due datetime in RFC3339 format
            duration: Estimated duration
            duration_unit: Duration unit (minute or day)

        Returns:
            Created task data

        Raises:
            RateLimitError: If rate limit exceeded
            TodoistError: For other API errors
        """
        await self._rate_limiter.acquire()

        task_data = {
            "content": content,
            "priority": priority,
        }

        if description:
            task_data["description"] = description
        if project_id:
            task_data["project_id"] = project_id
        if section_id:
            task_data["section_id"] = section_id
        if parent_id:
            task_data["parent_id"] = parent_id
        if labels:
            task_data["labels"] = labels
        if due_string:
            task_data["due_string"] = due_string
        elif due_date:
            task_data["due_date"] = due_date
        elif due_datetime:
            task_data["due_datetime"] = due_datetime
        if duration:
            task_data["duration"] = duration
            task_data["duration_unit"] = duration_unit or "minute"

        try:
            async with self._get_client() as client:
                response = await client.post(
                    f"{self.BASE_URL}/tasks",
                    headers=self.headers,
                    json=task_data,
                )

                if response.status_code == 401:
                    raise InvalidTokenError()
                elif response.status_code == 403:
                    raise QuotaExceededError()
                elif response.status_code == 429:
                    retry_after = int(response.headers.get("Retry-After", "60"))
                    raise RateLimitError(retry_after=retry_after)
                elif response.status_code != 200:
                    error_data = response.json() if response.content else {}
                    raise TodoistError(f"Failed to create task: {error_data}")

                return response.json()
        except httpx.RequestError as e:
            logger.error(f"Network error creating task: {e}")
            raise TodoistError(f"Network error: {str(e)}")

    async def get_projects(self) -> list[dict[str, Any]]:
        """Get all projects with caching.

        Returns:
            List of project dictionaries

        Raises:
            TodoistError: For API errors
        """
        if self._is_cache_valid():
            return self._projects_cache or []

        await self._rate_limiter.acquire()

        try:
            async with self._get_client() as client:
                response = await client.get(
                    f"{self.BASE_URL}/projects",
                    headers=self.headers,
                )

                if response.status_code == 401:
                    raise InvalidTokenError()
                elif response.status_code == 403:
                    raise QuotaExceededError()
                elif response.status_code != 200:
                    raise TodoistError(f"Failed to get projects: {response.status_code}")

                self._projects_cache = response.json()
                self._update_cache_expiry()
                return self._projects_cache
        except httpx.RequestError as e:
            logger.error(f"Network error getting projects: {e}")
            raise TodoistError(f"Network error: {str(e)}")

    async def get_labels(self) -> list[dict[str, Any]]:
        """Get all labels with caching.

        Returns:
            List of label dictionaries

        Raises:
            TodoistError: For API errors
        """
        if self._is_cache_valid() and self._labels_cache is not None:
            return self._labels_cache

        await self._rate_limiter.acquire()

        try:
            async with self._get_client() as client:
                response = await client.get(
                    f"{self.BASE_URL}/labels",
                    headers=self.headers,
                )

                if response.status_code == 401:
                    raise InvalidTokenError()
                elif response.status_code == 403:
                    raise QuotaExceededError()
                elif response.status_code != 200:
                    raise TodoistError(f"Failed to get labels: {response.status_code}")

                self._labels_cache = response.json()
                self._update_cache_expiry()
                return self._labels_cache
        except httpx.RequestError as e:
            logger.error(f"Network error getting labels: {e}")
            raise TodoistError(f"Network error: {str(e)}")

    async def get_project_by_name(self, name: str) -> dict[str, Any] | None:
        """Get project by name.

        Args:
            name: Project name to search for

        Returns:
            Project dictionary or None if not found
        """
        projects = await self.get_projects()
        for project in projects:
            if project["name"].lower() == name.lower():
                return project
        return None

    async def update_task(
        self,
        task_id: str,
        **kwargs: Any
    ) -> dict[str, Any]:
        """Update an existing task in Todoist.
        
        Args:
            task_id: Todoist task ID
            **kwargs: Fields to update (content, description, due_string, priority, labels)
            
        Returns:
            Updated task data
            
        Raises:
            TodoistError: For API errors
        """
        await self._rate_limiter.acquire()
        
        # Build update data - only include fields that are provided
        update_data = {}
        allowed_fields = ["content", "description", "due_string", "priority", "labels"]
        
        for field in allowed_fields:
            if field in kwargs and kwargs[field] is not None:
                update_data[field] = kwargs[field]
        
        if not update_data:
            raise TodoistError("No fields to update")
        
        try:
            async with self._get_client() as client:
                response = await client.post(
                    f"{self.BASE_URL}/tasks/{task_id}",
                    headers=self.headers,
                    json=update_data,
                )
                
                if response.status_code == 401:
                    raise InvalidTokenError()
                elif response.status_code == 403:
                    raise QuotaExceededError()
                elif response.status_code == 404:
                    raise TodoistError("Task not found")
                elif response.status_code != 200:
                    raise TodoistError(f"Failed to update task: {response.status_code}")
                
                return response.json()
        except httpx.RequestError as e:
            logger.error(f"Network error updating task: {e}")
            raise TodoistError(f"Network error: {str(e)}")

    async def delete_task(self, task_id: str) -> bool:
        """Delete a task from Todoist.

        Args:
            task_id: Todoist task ID

        Returns:
            True if deleted successfully, False otherwise

        Raises:
            RateLimitError: If rate limit exceeded
            TodoistError: For other API errors
        """
        await self._rate_limiter.acquire()

        try:
            async with self._get_client() as client:
                response = await client.delete(
                    f"{self.BASE_URL}/tasks/{task_id}",
                    headers=self.headers,
                )

                if response.status_code == 204:  # No content - success
                    return True
                elif response.status_code == 404:
                    logger.warning(f"Task {task_id} not found in Todoist")
                    return False
                elif response.status_code == 401:
                    raise InvalidTokenError()
                elif response.status_code == 403:
                    raise QuotaExceededError()
                elif response.status_code == 429:
                    retry_after = int(response.headers.get("Retry-After", "60"))
                    raise RateLimitError(retry_after=retry_after)
                else:
                    error_data = response.json() if response.content else {}
                    raise TodoistError(f"Failed to delete task: {error_data}")
        except httpx.RequestError as e:
            logger.error(f"Network error deleting task: {e}")
            raise TodoistError(f"Network error: {str(e)}")

    async def complete_task(self, task_id: str) -> bool:
        """Mark a task as completed in Todoist.

        Args:
            task_id: Todoist task ID

        Returns:
            True if completed successfully, False otherwise

        Raises:
            RateLimitError: If rate limit exceeded
            TodoistError: For other API errors
        """
        await self._rate_limiter.acquire()

        try:
            async with self._get_client() as client:
                response = await client.post(
                    f"{self.BASE_URL}/tasks/{task_id}/close",
                    headers=self.headers,
                )

                if response.status_code == 204:  # No content - success
                    return True
                elif response.status_code == 404:
                    logger.warning(f"Task {task_id} not found in Todoist")
                    return False
                elif response.status_code == 401:
                    raise InvalidTokenError()
                elif response.status_code == 403:
                    raise QuotaExceededError()
                elif response.status_code == 429:
                    retry_after = int(response.headers.get("Retry-After", "60"))
                    raise RateLimitError(retry_after=retry_after)
                else:
                    error_data = response.json() if response.content else {}
                    raise TodoistError(f"Failed to complete task: {error_data}")
        except httpx.RequestError as e:
            logger.error(f"Network error completing task: {e}")
            raise TodoistError(f"Network error: {str(e)}")

    async def get_tasks(
        self,
        filter_string: str | None = None,
        project_id: str | None = None,
        limit: int = 30
    ) -> list[dict[str, Any]]:
        """Get tasks with optional filtering.

        Args:
            filter_string: Todoist filter string (e.g., "today", "overdue", "p1")
            project_id: Optional project ID to filter by
            limit: Maximum number of tasks to return

        Returns:
            List of task dictionaries

        Raises:
            TodoistError: For API errors
        """
        await self._rate_limiter.acquire()

        params: dict[str, Any] = {}
        if filter_string:
            params["filter"] = filter_string
        if project_id:
            params["project_id"] = project_id

        try:
            async with self._get_client() as client:
                # Get all tasks (up to 300 by default in Todoist API)
                response = await client.get(
                    f"{self.BASE_URL}/tasks",
                    headers=self.headers,
                    params=params,
                )

                if response.status_code == 401:
                    raise InvalidTokenError()
                elif response.status_code == 403:
                    raise QuotaExceededError()
                elif response.status_code != 200:
                    raise TodoistError(f"Failed to get tasks: {response.status_code}")

                tasks = response.json()
                
                # Apply client-side filtering if needed
                if filter_string and filter_string not in ["today", "tomorrow", "overdue"]:
                    # For filters like "p1", "p2", etc., we need to filter manually
                    if filter_string.startswith("p"):
                        try:
                            priority = int(filter_string[1])
                            tasks = [t for t in tasks if t.get("priority", 1) == priority]
                        except (ValueError, IndexError):
                            pass
                
                # Sort by created date (newest first) and limit
                tasks.sort(key=lambda x: x.get("created_at", ""), reverse=True)
                return tasks[:limit]

        except httpx.RequestError as e:
            logger.error(f"Network error getting tasks: {e}")
            raise TodoistError(f"Network error: {str(e)}")

    async def get_recent_tasks(self, limit: int = 10) -> list[dict[str, Any]]:
        """Get recently created tasks.

        Args:
            limit: Maximum number of tasks to return

        Returns:
            List of task dictionaries sorted by creation date (newest first)

        Raises:
            TodoistError: For API errors
        """
        # Use get_tasks without filter to get all tasks, then sort by created date
        tasks = await self.get_tasks(limit=limit)
        return tasks  # Already sorted by created_at in get_tasks

    async def reopen_task(self, task_id: str) -> bool:
        """Reopen a completed task.

        Args:
            task_id: Todoist task ID

        Returns:
            True if reopened successfully, False otherwise

        Raises:
            TodoistError: For API errors
        """
        await self._rate_limiter.acquire()

        try:
            async with self._get_client() as client:
                response = await client.post(
                    f"{self.BASE_URL}/tasks/{task_id}/reopen",
                    headers=self.headers,
                )

                if response.status_code == 204:  # No content - success
                    return True
                elif response.status_code == 404:
                    logger.warning(f"Task {task_id} not found in Todoist")
                    return False
                elif response.status_code == 401:
                    raise InvalidTokenError()
                elif response.status_code == 403:
                    raise QuotaExceededError()
                elif response.status_code == 429:
                    retry_after = int(response.headers.get("Retry-After", "60"))
                    raise RateLimitError(retry_after=retry_after)
                else:
                    error_data = response.json() if response.content else {}
                    raise TodoistError(f"Failed to reopen task: {error_data}")
        except httpx.RequestError as e:
            logger.error(f"Network error reopening task: {e}")
            raise TodoistError(f"Network error: {str(e)}")

    def _get_client(self) -> httpx.AsyncClient:
        """Get or create HTTP client.
        
        Note: This returns a new client instance each time to be used as a context manager.
        The instance client (self._client) is only used when the service itself is used as a context manager.
        """
        return httpx.AsyncClient(timeout=30.0)

    def _is_cache_valid(self) -> bool:
        """Check if cache is still valid."""
        if not self._cache_expiry:
            return False
        return datetime.now() < self._cache_expiry

    def _update_cache_expiry(self) -> None:
        """Update cache expiry to 5 minutes from now."""
        self._cache_expiry = datetime.now() + timedelta(minutes=5)

    def invalidate_cache(self) -> None:
        """Invalidate the cache."""
        self._projects_cache = None
        self._labels_cache = None
        self._cache_expiry = None


class RateLimiter:
    """Token bucket rate limiter for Todoist API."""

    def __init__(self, max_requests: int, window_seconds: int) -> None:
        """Initialize rate limiter.

        Args:
            max_requests: Maximum requests allowed
            window_seconds: Time window in seconds
        """
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self.requests: list[datetime] = []
        self._lock = asyncio.Lock()

    async def acquire(self) -> None:
        """Acquire permission to make a request.

        Raises:
            RateLimitError: If rate limit would be exceeded
        """
        async with self._lock:
            now = datetime.now()
            cutoff = now - timedelta(seconds=self.window_seconds)

            # Remove old requests outside the window
            self.requests = [req_time for req_time in self.requests if req_time > cutoff]

            if len(self.requests) >= self.max_requests:
                # Calculate when the oldest request will expire
                oldest = min(self.requests)
                wait_time = int((oldest + timedelta(seconds=self.window_seconds) - now).total_seconds())
                raise RateLimitError(retry_after=wait_time)

            self.requests.append(now)
