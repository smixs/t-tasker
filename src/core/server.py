"""Webhook server implementation using aiohttp."""

import logging
from typing import Any, Dict

from aiohttp import web
from aiogram import Bot
from aiogram.webhook.aiohttp_server import SimpleRequestHandler, setup_application

from src.core.settings import get_settings
from src.core.bot import get_bot_instance

logger = logging.getLogger(__name__)


async def health_check(request: web.Request) -> web.Response:
    """Health check endpoint."""
    settings = get_settings()
    bot_instance = await get_bot_instance()
    
    health_data = {
        "status": "ok",
        "service": settings.otel_service_name,
        "version": "0.1.0",
        "checks": {
            "bot": "connected" if bot_instance.bot else "disconnected",
            "redis": "connected" if bot_instance.redis else "not_configured"
        }
    }
    
    # Check bot connection
    try:
        me = await bot_instance.bot.get_me()
        health_data["bot_username"] = me.username
    except Exception as e:
        health_data["status"] = "unhealthy"
        health_data["checks"]["bot"] = f"error: {str(e)}"
        return web.json_response(health_data, status=503)
    
    return web.json_response(health_data)


async def webhook_handler(request: web.Request) -> web.Response:
    """Handle webhook requests with secret validation."""
    settings = get_settings()
    
    # Validate webhook secret if configured
    if settings.telegram_webhook_secret:
        secret_header = request.headers.get("X-Telegram-Bot-Api-Secret-Token")
        expected_secret = settings.telegram_webhook_secret.get_secret_value()
        
        if secret_header != expected_secret:
            logger.warning("Invalid webhook secret received")
            return web.Response(status=401, text="Unauthorized")
    
    # Process webhook will be handled by aiogram
    return web.Response(status=200)


async def on_startup(app: web.Application) -> None:
    """Application startup handler."""
    settings = get_settings()
    bot_instance = await get_bot_instance()
    
    # Set webhook
    webhook_url = f"{settings.telegram_webhook_url}{settings.webhook_path}"
    
    await bot_instance.bot.set_webhook(
        url=webhook_url,
        secret_token=settings.telegram_webhook_secret.get_secret_value() if settings.telegram_webhook_secret else None,
        drop_pending_updates=True,  # Don't process messages sent while bot was offline
        allowed_updates=[
            "message",
            "edited_message",
            "callback_query",
            "inline_query"
        ]
    )
    
    logger.info(f"Webhook set to: {webhook_url}")


async def on_shutdown(app: web.Application) -> None:
    """Application shutdown handler."""
    bot_instance = await get_bot_instance()
    
    # Delete webhook
    await bot_instance.bot.delete_webhook(drop_pending_updates=True)
    
    # Close bot instance
    await bot_instance.close()
    
    logger.info("Application shutdown completed")


async def create_app() -> web.Application:
    """Create aiohttp application with webhook handler."""
    settings = get_settings()
    bot_instance = await get_bot_instance()
    
    # Create aiohttp app
    app = web.Application()
    
    # Setup routes
    app.router.add_get(settings.health_check_path, health_check)
    
    # Setup aiogram webhook handler
    webhook_requests_handler = SimpleRequestHandler(
        dispatcher=bot_instance.dispatcher,
        bot=bot_instance.bot
    )
    webhook_requests_handler.register(app, path=settings.webhook_path)
    
    # Setup lifecycle handlers
    app.on_startup.append(on_startup)
    app.on_shutdown.append(on_shutdown)
    
    # Setup aiogram application
    setup_application(app, bot_instance.dispatcher, bot=bot_instance.bot)
    
    return app


def run_webhook_server() -> None:
    """Run webhook server."""
    settings = get_settings()
    
    # Configure logging
    logging.basicConfig(
        level=getattr(logging, settings.log_level),
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    
    # Create and run app
    app = create_app()
    
    logger.info(f"Starting webhook server on {settings.server_host}:{settings.server_port}")
    
    web.run_app(
        app,
        host=settings.server_host,
        port=settings.server_port,
        access_log_format='%a "%r" %s %b "%{User-Agent}i" %Tf'
    )


if __name__ == "__main__":
    run_webhook_server()