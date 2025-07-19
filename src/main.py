"""Main application entry point."""

import asyncio
import logging
import signal
import sys
from typing import Any

from src.core.bot import BotInstance
from src.core.database import get_database
from src.core.middleware import (
    ErrorHandlingMiddleware,
    LoggingMiddleware,
    RateLimitMiddleware,
    UserContextMiddleware,
)
from src.core.server import WebhookServer
from src.core.settings import get_settings
from src.handlers import command_router, error_router, message_router

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
        self.bot_instance = BotInstance()
        self.database = get_database()
        self.server: WebhookServer | None = None
        self._shutdown_event = asyncio.Event()

    async def setup(self) -> None:
        """Setup application components."""
        logger.info("Setting up application...")
        
        # Initialize database
        await self.database.create_tables()
        
        # Setup bot
        await self.bot_instance.setup()
        
        # Register routers
        dp = self.bot_instance.dispatcher
        dp.include_router(error_router)
        dp.include_router(command_router)
        dp.include_router(message_router)
        
        # Register middleware
        dp.message.middleware(RateLimitMiddleware())
        dp.message.middleware(UserContextMiddleware())
        dp.message.middleware(ErrorHandlingMiddleware())
        dp.message.middleware(LoggingMiddleware())
        
        # Setup webhook
        await self.bot_instance.setup_webhook()
        
        # Create webhook server
        self.server = WebhookServer(
            bot=self.bot_instance.bot,
            dispatcher=self.bot_instance.dispatcher,
            webhook_path=self.settings.webhook_path,
            webhook_secret=self.settings.webhook_secret,
            host=self.settings.webhook_host,
            port=self.settings.webhook_port
        )
        
        logger.info("Application setup complete")

    async def start(self) -> None:
        """Start the application."""
        logger.info("Starting application...")
        
        # Setup signal handlers
        for sig in (signal.SIGTERM, signal.SIGINT):
            signal.signal(sig, lambda s, f: asyncio.create_task(self.shutdown()))
        
        # Start webhook server
        if self.server:
            await self.server.start()
            logger.info(f"Webhook server started on {self.settings.webhook_host}:{self.settings.webhook_port}")
        
        # Wait for shutdown
        await self._shutdown_event.wait()

    async def shutdown(self) -> None:
        """Shutdown the application gracefully."""
        logger.info("Shutting down application...")
        
        # Stop webhook server
        if self.server:
            await self.server.stop()
        
        # Close bot
        await self.bot_instance.close()
        
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