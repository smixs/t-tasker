"""Custom Redis storage with retry logic."""

import asyncio
import logging
from typing import Any, Optional

from aiogram.fsm.storage.redis import RedisStorage
from redis.asyncio import Redis
from redis.exceptions import RedisError, ReadOnlyError, ConnectionError as RedisConnectionError

logger = logging.getLogger(__name__)


class RetryRedisStorage(RedisStorage):
    """Redis storage with automatic retry on errors."""
    
    def __init__(
        self,
        redis: Redis,
        max_retries: int = 3,
        retry_delay: float = 0.5,
        exponential_backoff: bool = True
    ) -> None:
        """Initialize storage with retry configuration.
        
        Args:
            redis: Redis client
            max_retries: Maximum number of retry attempts
            retry_delay: Initial delay between retries in seconds
            exponential_backoff: Whether to use exponential backoff
        """
        super().__init__(redis)
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self.exponential_backoff = exponential_backoff
    
    async def _execute_with_retry(self, operation: Any, *args: Any, **kwargs: Any) -> Any:
        """Execute operation with retry logic.
        
        Args:
            operation: Async operation to execute
            *args: Positional arguments for operation
            **kwargs: Keyword arguments for operation
            
        Returns:
            Operation result
            
        Raises:
            RedisError: If all retries failed
        """
        last_error = None
        
        for attempt in range(self.max_retries):
            try:
                return await operation(*args, **kwargs)
            except ReadOnlyError as e:
                last_error = e
                logger.warning(f"Redis read-only error on attempt {attempt + 1}/{self.max_retries}: {e}")
            except RedisConnectionError as e:
                last_error = e
                logger.warning(f"Redis connection error on attempt {attempt + 1}/{self.max_retries}: {e}")
            except RedisError as e:
                last_error = e
                logger.warning(f"Redis error on attempt {attempt + 1}/{self.max_retries}: {e}")
            
            if attempt < self.max_retries - 1:
                delay = self.retry_delay * (2 ** attempt if self.exponential_backoff else 1)
                await asyncio.sleep(delay)
        
        logger.error(f"All {self.max_retries} Redis retry attempts failed")
        raise last_error
    
    async def set_state(self, *args: Any, **kwargs: Any) -> None:
        """Set state with retry logic."""
        await self._execute_with_retry(super().set_state, *args, **kwargs)
    
    async def get_state(self, *args: Any, **kwargs: Any) -> Optional[str]:
        """Get state with retry logic."""
        return await self._execute_with_retry(super().get_state, *args, **kwargs)
    
    async def set_data(self, *args: Any, **kwargs: Any) -> None:
        """Set data with retry logic."""
        await self._execute_with_retry(super().set_data, *args, **kwargs)
    
    async def get_data(self, *args: Any, **kwargs: Any) -> dict[str, Any]:
        """Get data with retry logic."""
        return await self._execute_with_retry(super().get_data, *args, **kwargs)
    
    async def update_data(self, *args: Any, **kwargs: Any) -> dict[str, Any]:
        """Update data with retry logic."""
        return await self._execute_with_retry(super().update_data, *args, **kwargs)
    
    async def close(self) -> None:
        """Close storage with retry logic."""
        try:
            await self._execute_with_retry(super().close)
        except Exception as e:
            logger.error(f"Error closing Redis storage: {e}")