"""Global error handler for the bot."""

import logging

from aiogram import Router
from aiogram.types import ErrorEvent

from src.core.exceptions import (
    OpenAIError,
    RateLimitError,
    TodoistError,
    TranscriptionError,
    UnauthorizedError,
    ValidationError,
)

logger = logging.getLogger(__name__)

# Create router for errors
error_router = Router(name="errors")


@error_router.error()
async def handle_error(event: ErrorEvent) -> None:
    """Global error handler for all errors."""
    exception = event.exception
    update = event.update

    logger.exception(f"Error handling update {update}: {exception}")

    # Get message object if available
    message = None
    if update and update.message:
        message = update.message
    elif update and update.callback_query and update.callback_query.message:
        message = update.callback_query.message

    if not message:
        logger.error("Cannot send error message: no message object available")
        return

    # Handle specific error types
    if isinstance(exception, RateLimitError):
        await message.answer(
            "⏱ Превышен лимит запросов. Пожалуйста, подождите немного и попробуйте снова."
        )
    elif isinstance(exception, TranscriptionError):
        await message.answer(
            "🎤 Не удалось распознать речь. Попробуйте записать сообщение еще раз "
            "или отправьте текстом."
        )
    elif isinstance(exception, OpenAIError):
        await message.answer(
            "🤖 Ошибка при обработке вашего запроса. Попробуйте сформулировать иначе "
            "или повторите позже."
        )
    elif isinstance(exception, TodoistError):
        await message.answer(
            "📝 Не удалось создать задачу в Todoist. Проверьте подключение к аккаунту "
            "или попробуйте позже."
        )
    elif isinstance(exception, UnauthorizedError):
        await message.answer(
            "🔐 Необходимо подключить аккаунт Todoist. Используйте /setup для настройки."
        )
    elif isinstance(exception, ValidationError):
        await message.answer(
            f"❌ Ошибка валидации: {str(exception)}"
        )
    else:
        # Generic error message
        await message.answer(
            "❌ Произошла неожиданная ошибка. Мы уже работаем над решением.\n"
            "Пожалуйста, попробуйте позже."
        )

    # TODO: Send error to Sentry when configured
