"""Todoist API service for task management."""

import asyncio
import json
import logging
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

import httpx

from src.core.exceptions import InvalidTokenError, QuotaExceededError, RateLimitError, TodoistError
from src.core.settings import settings

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
        self._client: Optional[httpx.AsyncClient] = None
        self._rate_limiter = RateLimiter(max_requests=450, window_seconds=900)  # 450 req/15 min
        self._projects_cache: Optional[List[Dict[str, Any]]] = None
        self._labels_cache: Optional[List[Dict[str, Any]]] = None
        self._cache_expiry: Optional[datetime] = None

    async def __aenter__(self) -> "TodoistService":
        """Async context manager entry."""
        self._client = httpx.AsyncClient(timeout=30.0)
        return self

    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Async context manager exit."""
        if self._client:
            await self._client.aclose()

    async def validate_token(self) -> Dict[str, Any]:
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
        description: Optional[str] = None,
        project_id: Optional[str] = None,
        section_id: Optional[str] = None,
        parent_id: Optional[str] = None,
        labels: Optional[List[str]] = None,
        priority: int = 1,
        due_string: Optional[str] = None,
        due_date: Optional[str] = None,
        due_datetime: Optional[str] = None,
        duration: Optional[int] = None,
        duration_unit: Optional[str] = None,
    ) -> Dict[str, Any]:
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

    async def get_projects(self) -> List[Dict[str, Any]]:
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

    async def get_labels(self) -> List[Dict[str, Any]]:
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

    async def get_project_by_name(self, name: str) -> Optional[Dict[str, Any]]:
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

    def _get_client(self) -> httpx.AsyncClient:
        """Get or create HTTP client."""
        if not self._client:
            self._client = httpx.AsyncClient(timeout=30.0)
        return self._client

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
        self.requests: List[datetime] = []
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