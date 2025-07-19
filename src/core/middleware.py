"""Bot middleware implementations."""

import logging
import time
from typing import Any, Awaitable, Callable, Dict, Optional

from aiogram import BaseMiddleware
from aiogram.types import Message, CallbackQuery, Update, User

from src.core.settings import get_settings

logger = logging.getLogger(__name__)


class LoggingMiddleware(BaseMiddleware):
    """Logs all incoming updates for debugging."""
    
    async def __call__(
        self,
        handler: Callable[[Update, Dict[str, Any]], Awaitable[Any]],
        event: Update,
        data: Dict[str, Any]
    ) -> Any:
        start_time = time.time()
        
        # Extract user info
        user: Optional[User] = None
        if isinstance(event, Message):
            user = event.from_user
            logger.info(f"Message from {user.id} (@{user.username}): {event.text[:50] if event.text else 'non-text'}")
        elif isinstance(event, CallbackQuery):
            user = event.from_user
            logger.info(f"Callback from {user.id} (@{user.username}): {event.data}")
        
        try:
            result = await handler(event, data)
            elapsed = time.time() - start_time
            logger.info(f"Handler executed in {elapsed:.3f}s")
            return result
        except Exception as e:
            elapsed = time.time() - start_time
            logger.error(f"Handler failed after {elapsed:.3f}s: {str(e)}")
            raise


class ErrorHandlingMiddleware(BaseMiddleware):
    """Global error handler for all updates."""
    
    async def __call__(
        self,
        handler: Callable[[Update, Dict[str, Any]], Awaitable[Any]],
        event: Update,
        data: Dict[str, Any]
    ) -> Any:
        try:
            return await handler(event, data)
        except Exception as e:
            logger.exception(f"Unhandled error: {str(e)}")
            
            # Try to send error message to user
            if isinstance(event, Message):
                try:
                    await event.answer(
                        "❌ Произошла ошибка при обработке вашего запроса. "
                        "Пожалуйста, попробуйте позже или обратитесь в поддержку."
                    )
                except Exception:
                    logger.error("Failed to send error message to user")
            
            # Re-raise for outer handlers
            raise


class ThrottlingMiddleware(BaseMiddleware):
    """Rate limiting middleware to prevent spam."""
    
    def __init__(self, rate_limit: float = 0.5):
        """
        Initialize throttling middleware.
        
        Args:
            rate_limit: Minimum seconds between messages from same user
        """
        self.rate_limit = rate_limit
        self.user_timestamps: Dict[int, float] = {}
    
    async def __call__(
        self,
        handler: Callable[[Update, Dict[str, Any]], Awaitable[Any]],
        event: Update,
        data: Dict[str, Any]
    ) -> Any:
        if not isinstance(event, Message):
            return await handler(event, data)
        
        user = event.from_user
        if not user:
            return await handler(event, data)
        
        current_time = time.time()
        last_time = self.user_timestamps.get(user.id, 0)
        
        if current_time - last_time < self.rate_limit:
            logger.warning(f"Rate limit exceeded for user {user.id}")
            await event.answer("⏱ Пожалуйста, подождите немного перед отправкой следующего сообщения.")
            return
        
        self.user_timestamps[user.id] = current_time
        return await handler(event, data)


class DatabaseMiddleware(BaseMiddleware):
    """Injects database session into handler data."""
    
    async def __call__(
        self,
        handler: Callable[[Update, Dict[str, Any]], Awaitable[Any]],
        event: Update,
        data: Dict[str, Any]
    ) -> Any:
        # TODO: Implement database session injection when database is set up
        # For now, just pass through
        return await handler(event, data)