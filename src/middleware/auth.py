"""Authentication middleware for checking user authorization."""

import logging
from collections.abc import Awaitable, Callable
from typing import Any

from aiogram import BaseMiddleware
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, TelegramObject

from src.core.database import get_database
from src.handlers.states import SetupStates
from src.repositories.user import UserRepository
from src.services.encryption import EncryptionService

logger = logging.getLogger(__name__)


class AuthMiddleware(BaseMiddleware):
    """Middleware for checking user authorization."""

    def __init__(self) -> None:
        """Initialize middleware."""
        self.db = get_database()
        self.encryption = EncryptionService()
        # Commands that don't require auth
        self.public_commands = {"/start", "/help", "/setup", "/cancel"}

    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any]
    ) -> Any:
        """Process the update."""
        if not isinstance(event, Message):
            return await handler(event, data)

        # Skip auth for non-user messages
        if not event.from_user:
            return await handler(event, data)

        # Check if it's a public command
        if event.text and any(event.text.startswith(cmd) for cmd in self.public_commands):
            return await handler(event, data)

        user_id = event.from_user.id

        # Check if user is in setup state
        state: FSMContext = data.get("state")
        if state:
            current_state = await state.get_state()
            if current_state == SetupStates.waiting_for_token.state:
                # Allow token processing
                return await handler(event, data)

        # Get user from database
        async with self.db.get_session() as session:
            user_repo = UserRepository(session)
            user = await user_repo.get_by_id(user_id)

            # Check if user has Todoist token
            if not user or not user.todoist_token_encrypted:
                logger.info(f"Unauthorized access attempt by user {user_id}")
                await event.answer(
                    "🔐 Для использования бота необходимо настроить интеграцию с Todoist.\n"
                    "Используйте команду /setup для начала настройки."
                )
                return  # Don't call the handler

            # Add user and decrypted token to data
            data["user"] = user
            data["todoist_token"] = self.encryption.decrypt(user.todoist_token_encrypted)

        return await handler(event, data)
