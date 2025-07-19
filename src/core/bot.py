"""Bot instance manager."""

import logging

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.redis import RedisStorage
from redis.asyncio import Redis

from src.core.settings import Settings, get_settings

logger = logging.getLogger(__name__)


class BotInstance:
    """Manages bot and dispatcher instances."""

    def __init__(self, settings: Settings | None = None) -> None:
        """Initialize bot instance manager.

        Args:
            settings: Application settings
        """
        self.settings = settings or get_settings()
        self._bot: Bot | None = None
        self._dispatcher: Dispatcher | None = None
        self._redis: Redis | None = None

    async def setup(self) -> None:
        """Initialize bot and dispatcher."""
        # Initialize Redis for FSM storage
        self._redis = Redis.from_url(
            self.settings.redis_url,
            encoding="utf-8",
            decode_responses=True
        )

        # Test Redis connection
        await self._redis.ping()
        logger.info("Redis connection established")

        # Create FSM storage
        storage = RedisStorage(redis=self._redis)

        # Initialize bot
        self._bot = Bot(
            token=self.settings.telegram_token,
            default=DefaultBotProperties(
                parse_mode=ParseMode.HTML,
                link_preview_is_disabled=True
            )
        )

        # Initialize dispatcher
        self._dispatcher = Dispatcher(storage=storage)

        # Get bot info
        bot_info = await self._bot.get_me()
        logger.info(f"Bot initialized: @{bot_info.username}")

    async def close(self) -> None:
        """Close bot and redis connections."""
        if self._bot:
            await self._bot.session.close()
            logger.info("Bot session closed")

        if self._redis:
            await self._redis.close()
            logger.info("Redis connection closed")

    @property
    def bot(self) -> Bot:
        """Get bot instance."""
        if self._bot is None:
            raise RuntimeError("Bot not initialized. Call setup() first.")
        return self._bot

    @property
    def dispatcher(self) -> Dispatcher:
        """Get dispatcher instance."""
        if self._dispatcher is None:
            raise RuntimeError("Dispatcher not initialized. Call setup() first.")
        return self._dispatcher

    async def setup_webhook(self) -> None:
        """Set up webhook for the bot."""
        webhook_url = f"{self.settings.telegram_webhook_url}{self.settings.webhook_path}/{self.settings.telegram_token}"

        # Delete existing webhook
        await self._bot.delete_webhook(drop_pending_updates=True)

        # Set new webhook
        await self._bot.set_webhook(
            url=webhook_url,
            secret_token=self.settings.telegram_webhook_secret.get_secret_value()
            if self.settings.telegram_webhook_secret else None
        )

        logger.info(f"Webhook set to: {webhook_url}")

    async def remove_webhook(self) -> None:
        """Remove webhook."""
        await self._bot.delete_webhook()
        logger.info("Webhook removed")


# Global bot instance
_bot_instance: BotInstance | None = None


def get_bot_instance() -> BotInstance:
    """Get global bot instance."""
    global _bot_instance
    if _bot_instance is None:
        _bot_instance = BotInstance()
    return _bot_instance
