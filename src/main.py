"""Main application entry point with polling mode."""

import asyncio
import logging
import signal
import sys

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.redis import RedisStorage
from redis.asyncio import Redis

from src.core.database import get_database
from src.core.middleware import (
    ErrorHandlingMiddleware,
    LoggingMiddleware,
    RateLimitMiddleware,
    UserContextMiddleware,
)
from src.core.settings import get_settings
from src.handlers import callback_router, command_router, edit_router, error_router, message_router
from src.middleware.auth import AuthMiddleware

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger(__name__)


class Application:
    """Main application class."""

    def __init__(self) -> None:
        """Initialize application."""
        self.settings = get_settings()
        self.bot: Bot | None = None
        self.dispatcher: Dispatcher | None = None
        self.database = get_database()
        self.redis: Redis | None = None
        self._shutdown_event = asyncio.Event()

    async def setup(self) -> None:
        """Setup application components."""
        logger.info("Setting up application...")

        # Initialize database
        await self.database.create_tables()

        # Setup Redis
        self.redis = Redis.from_url(
            self.settings.redis_url,
            decode_responses=True
        )

        # Create bot
        self.bot = Bot(
            token=self.settings.telegram_token,
            default=DefaultBotProperties(parse_mode=ParseMode.HTML)
        )

        # Create dispatcher with Redis storage
        self.dispatcher = Dispatcher(
            storage=RedisStorage(self.redis)
        )

        # Register routers (order matters - edit_router must be before message_router)
        self.dispatcher.include_router(error_router)
        self.dispatcher.include_router(command_router)
        self.dispatcher.include_router(edit_router)  # Edit handlers have priority over message handlers
        self.dispatcher.include_router(message_router)
        self.dispatcher.include_router(callback_router)

        # Register middleware (order matters - auth should be after user context)
        # For messages
        self.dispatcher.message.middleware(RateLimitMiddleware())
        self.dispatcher.message.middleware(UserContextMiddleware())
        self.dispatcher.message.middleware(AuthMiddleware())
        self.dispatcher.message.middleware(ErrorHandlingMiddleware())
        self.dispatcher.message.middleware(LoggingMiddleware())

        # For callback queries
        self.dispatcher.callback_query.middleware(UserContextMiddleware())
        self.dispatcher.callback_query.middleware(AuthMiddleware())
        self.dispatcher.callback_query.middleware(ErrorHandlingMiddleware())

        # Delete webhook if exists
        await self.bot.delete_webhook(drop_pending_updates=True)

        logger.info("Application setup complete")

    async def start(self) -> None:
        """Start the application."""
        logger.info("Starting application...")

        # Setup signal handlers
        for sig in (signal.SIGTERM, signal.SIGINT):
            signal.signal(sig, lambda s, f: asyncio.create_task(self.shutdown()))

        # Get bot info
        bot_info = await self.bot.get_me()
        logger.info(f"Bot @{bot_info.username} is starting in polling mode")

        # Start polling
        try:
            await self.dispatcher.start_polling(self.bot)
        except asyncio.CancelledError:
            logger.info("Polling cancelled")

        # Wait for shutdown
        await self._shutdown_event.wait()

    async def shutdown(self) -> None:
        """Shutdown the application gracefully."""
        logger.info("Shutting down application...")

        # Stop polling
        if self.dispatcher:
            await self.dispatcher.stop_polling()

        # Close bot session
        if self.bot:
            await self.bot.session.close()

        # Close Redis
        if self.redis:
            await self.redis.close()

        # Close database
        await self.database.close()

        # Set shutdown event
        self._shutdown_event.set()

        logger.info("Application shutdown complete")


async def main() -> None:
    """Main entry point."""
    app = Application()

    try:
        await app.setup()
        await app.start()
    except Exception as e:
        logger.error(f"Application error: {e}", exc_info=True)
        raise
    finally:
        await app.shutdown()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Application interrupted by user")
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        sys.exit(1)
