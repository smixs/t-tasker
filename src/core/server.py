"""Web server for webhook handling."""

import logging

from aiogram import Bot, Dispatcher
from aiogram.webhook.aiohttp_server import SimpleRequestHandler, setup_application
from aiohttp import web

from src.core.settings import Settings

logger = logging.getLogger(__name__)


class WebhookServer:
    """Webhook server for handling Telegram updates."""

    def __init__(
        self,
        bot: Bot,
        dispatcher: Dispatcher,
        settings: Settings
    ) -> None:
        """Initialize webhook server.

        Args:
            bot: Bot instance
            dispatcher: Dispatcher instance
            settings: Application settings
        """
        self.bot = bot
        self.dispatcher = dispatcher
        self.settings = settings
        self.app = web.Application()

        # Set up webhook handler
        webhook_path = f"{self.settings.webhook_path}/{self.settings.telegram_token}"
        webhook_handler = SimpleRequestHandler(
            dispatcher=self.dispatcher,
            bot=self.bot
        )
        webhook_handler.register(self.app, path=webhook_path)
        setup_application(self.app, self.dispatcher, bot=self.bot)

        # Add health check endpoint
        self.app.router.add_get(self.settings.health_check_path, self.health_check)

        # Add metrics endpoint placeholder
        self.app.router.add_get("/metrics", self.metrics)

        logger.info(f"Webhook server configured on {webhook_path}")

    async def health_check(self, request: web.Request) -> web.Response:
        """Health check endpoint."""
        try:
            # Check bot connection
            bot_info = await self.bot.get_me()

            # Check Redis connection if available
            redis_status = "unknown"
            if hasattr(self.dispatcher.storage, "_redis"):
                try:
                    await self.dispatcher.storage._redis.ping()
                    redis_status = "ok"
                except Exception:
                    redis_status = "error"

            return web.json_response({
                "status": "healthy",
                "bot": {
                    "username": bot_info.username,
                    "id": bot_info.id
                },
                "redis": redis_status
            })
        except Exception as e:
            logger.error(f"Health check failed: {e}")
            return web.json_response(
                {"status": "unhealthy", "error": str(e)},
                status=503
            )

    async def metrics(self, request: web.Request) -> web.Response:
        """Metrics endpoint for Prometheus."""
        # TODO: Implement actual metrics collection
        return web.Response(
            text="# HELP taskerbot_up Bot status\n"
                 "# TYPE taskerbot_up gauge\n"
                 "taskerbot_up 1\n",
            content_type="text/plain"
        )

    def get_app(self) -> web.Application:
        """Get aiohttp application."""
        return self.app

    async def start(self) -> None:
        """Start webhook server."""
        runner = web.AppRunner(self.app)
        await runner.setup()

        site = web.TCPSite(
            runner,
            self.settings.server_host,
            self.settings.server_port
        )

        await site.start()
        logger.info(
            f"Webhook server started on "
            f"{self.settings.server_host}:{self.settings.server_port}"
        )
