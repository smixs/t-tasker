"""Bot instance configuration and setup."""

import logging
from typing import Optional

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.fsm.storage.redis import RedisStorage
from redis.asyncio import Redis

from src.core.settings import get_settings

logger = logging.getLogger(__name__)


class BotInstance:
    """Manages bot and dispatcher instances."""
    
    def __init__(self):
        self.settings = get_settings()
        self._bot: Optional[Bot] = None
        self._dispatcher: Optional[Dispatcher] = None
        self._redis: Optional[Redis] = None
    
    async def setup(self) -> None:
        """Initialize bot and dispatcher."""
        # Create bot instance
        self._bot = Bot(
            token=self.settings.telegram_token,
            default=DefaultBotProperties(
                parse_mode=ParseMode.HTML,
                link_preview_is_disabled=True
            )
        )
        
        # Setup FSM storage
        if self.settings.redis_url and self.settings.redis_url != "redis://localhost:6379/0":
            try:
                self._redis = Redis.from_url(
                    self.settings.redis_url,
                    decode_responses=True
                )
                await self._redis.ping()
                storage = RedisStorage(self._redis)
                logger.info("Using Redis storage for FSM")
            except Exception as e:
                logger.warning(f"Failed to connect to Redis: {e}. Using memory storage.")
                storage = MemoryStorage()
        else:
            storage = MemoryStorage()
            logger.info("Using memory storage for FSM")
        
        # Create dispatcher
        self._dispatcher = Dispatcher(storage=storage)
        
        # Setup middleware
        await self._setup_middleware()
        
        # Setup routers
        await self._setup_routers()
        
        logger.info("Bot setup completed")
    
    async def _setup_middleware(self) -> None:
        """Setup bot middleware."""
        from src.core.middleware import (
            LoggingMiddleware,
            ErrorHandlingMiddleware,
            ThrottlingMiddleware,
            DatabaseMiddleware
        )
        
        # Order matters: outermost middleware runs first
        self._dispatcher.message.middleware(LoggingMiddleware())
        self._dispatcher.callback_query.middleware(LoggingMiddleware())
        
        self._dispatcher.message.middleware(ErrorHandlingMiddleware())
        self._dispatcher.callback_query.middleware(ErrorHandlingMiddleware())
        
        self._dispatcher.message.middleware(ThrottlingMiddleware())
        
        self._dispatcher.message.middleware(DatabaseMiddleware())
        self._dispatcher.callback_query.middleware(DatabaseMiddleware())
    
    async def _setup_routers(self) -> None:
        """Setup bot routers."""
        from src.handlers.commands import command_router
        from src.handlers.messages import message_router
        from src.handlers.errors import error_router
        
        # Register routers in order of priority
        self._dispatcher.include_router(error_router)
        self._dispatcher.include_router(command_router)
        self._dispatcher.include_router(message_router)
    
    async def close(self) -> None:
        """Close bot and cleanup resources."""
        if self._bot:
            await self._bot.session.close()
            self._bot = None
        
        if self._redis:
            await self._redis.close()
            self._redis = None
        
        logger.info("Bot closed")
    
    @property
    def bot(self) -> Bot:
        """Get bot instance."""
        if not self._bot:
            raise RuntimeError("Bot not initialized. Call setup() first.")
        return self._bot
    
    @property
    def dispatcher(self) -> Dispatcher:
        """Get dispatcher instance."""
        if not self._dispatcher:
            raise RuntimeError("Dispatcher not initialized. Call setup() first.")
        return self._dispatcher
    
    @property
    def redis(self) -> Optional[Redis]:
        """Get Redis instance if available."""
        return self._redis


# Global bot instance
_bot_instance: Optional[BotInstance] = None


async def get_bot_instance() -> BotInstance:
    """Get or create bot instance."""
    global _bot_instance
    if _bot_instance is None:
        _bot_instance = BotInstance()
        await _bot_instance.setup()
    return _bot_instance


async def close_bot_instance() -> None:
    """Close bot instance."""
    global _bot_instance
    if _bot_instance:
        await _bot_instance.close()
        _bot_instance = None