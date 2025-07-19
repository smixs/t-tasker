"""Middleware for the bot."""

import logging
import time
import uuid
from collections.abc import Awaitable, Callable
from typing import Any

from aiogram import BaseMiddleware
from aiogram.types import Message, TelegramObject

from src.core.exceptions import BotError

logger = logging.getLogger(__name__)


class LoggingMiddleware(BaseMiddleware):
    """Middleware for logging requests and responses."""

    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any]
    ) -> Any:
        """Process update with logging."""
        # Generate request ID
        request_id = str(uuid.uuid4())
        data["request_id"] = request_id

        # Start timing
        start_time = time.monotonic()

        # Extract user info
        user = None
        if hasattr(event, "from_user"):
            user = event.from_user
        elif hasattr(event, "message") and event.message and hasattr(event.message, "from_user"):
            user = event.message.from_user

        user_info = f"user_id={user.id}, username={user.username}" if user else "unknown"

        # Log request
        event_type = type(event).__name__
        logger.info(
            f"Request {request_id}: {event_type} from {user_info}"
        )

        try:
            # Process request
            result = await handler(event, data)

            # Calculate duration
            duration = time.monotonic() - start_time

            # Log response
            logger.info(
                f"Response {request_id}: completed in {duration:.2f}s"
            )

            return result

        except Exception as e:
            # Calculate duration
            duration = time.monotonic() - start_time

            # Log error
            logger.error(
                f"Error {request_id}: {type(e).__name__} after {duration:.2f}s",
                exc_info=True
            )

            raise


class ErrorHandlingMiddleware(BaseMiddleware):
    """Middleware for handling errors."""

    async def __call__(
        self,
        handler: Callable[[Message, dict[str, Any]], Awaitable[Any]],
        event: Message,
        data: dict[str, Any]
    ) -> Any:
        """Process message with error handling."""
        try:
            return await handler(event, data)
        except BotError as e:
            # Send user-friendly error message
            logger.warning(f"Bot error: {e}")
            await event.answer(f"❌ {e.user_message}")
        except Exception as e:
            # Log unexpected error
            request_id = data.get("request_id", "unknown")
            logger.error(
                f"Unexpected error in request {request_id}: {type(e).__name__}: {e}",
                exc_info=True
            )

            # Send generic error message
            await event.answer(
                "❌ Произошла неожиданная ошибка. Попробуйте позже."
            )


class UserContextMiddleware(BaseMiddleware):
    """Middleware to add user context to data."""

    def __init__(self, user_repository: Any | None = None) -> None:
        """Initialize middleware.

        Args:
            user_repository: User repository for database operations
        """
        self.user_repository = user_repository

    async def __call__(
        self,
        handler: Callable[[Message, dict[str, Any]], Awaitable[Any]],
        event: Message,
        data: dict[str, Any]
    ) -> Any:
        """Add user context to data."""
        # Extract user
        user = event.from_user
        if not user:
            return await handler(event, data)

        # Add basic user info
        data["user_id"] = user.id
        data["username"] = user.username
        data["language_code"] = user.language_code or "ru"

        # Load user from database if repository is available
        if self.user_repository:
            try:
                db_user = await self.user_repository.get_by_telegram_id(user.id)
                data["db_user"] = db_user
                data["has_token"] = bool(db_user and db_user.todoist_token_encrypted)
            except Exception as e:
                logger.error(f"Failed to load user from database: {e}")
                data["db_user"] = None
                data["has_token"] = False

        return await handler(event, data)


class RateLimitMiddleware(BaseMiddleware):
    """Middleware for rate limiting."""

    def __init__(self, max_requests: int = 10, window: int = 60) -> None:
        """Initialize rate limit middleware.

        Args:
            max_requests: Maximum requests per window
            window: Time window in seconds
        """
        self.max_requests = max_requests
        self.window = window
        self.user_requests: dict[int, list[float]] = {}

    async def __call__(
        self,
        handler: Callable[[Message, dict[str, Any]], Awaitable[Any]],
        event: Message,
        data: dict[str, Any]
    ) -> Any:
        """Check rate limit before processing."""
        user_id = data.get("user_id")
        if not user_id:
            return await handler(event, data)

        current_time = time.time()

        # Clean old requests
        if user_id in self.user_requests:
            self.user_requests[user_id] = [
                timestamp for timestamp in self.user_requests[user_id]
                if current_time - timestamp < self.window
            ]
        else:
            self.user_requests[user_id] = []

        # Check rate limit
        if len(self.user_requests[user_id]) >= self.max_requests:
            oldest_request = min(self.user_requests[user_id])
            retry_after = int(self.window - (current_time - oldest_request))

            await event.answer(
                f"⏱ Слишком много запросов. Попробуйте через {retry_after} секунд."
            )
            return

        # Add current request
        self.user_requests[user_id].append(current_time)

        return await handler(event, data)
