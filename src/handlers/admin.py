"""Admin command handlers for the bot."""

import asyncio
import logging
from typing import Any

from aiogram import Router
from aiogram.exceptions import (
    TelegramAPIError,
    TelegramBadRequest,
    TelegramForbiddenError,
    TelegramRetryAfter
)
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import Message

from src.core.database import get_database
from src.core.settings import get_settings
from src.handlers.states import BroadcastStates
from src.repositories.user import UserRepository

logger = logging.getLogger(__name__)

# Create router for admin commands
admin_router = Router(name="admin")


async def is_admin(message: Message) -> bool:
    """Check if user is admin."""
    if not message.from_user:
        return False
    
    settings = get_settings()
    return message.from_user.id == settings.admin_id


@admin_router.message(Command("msg"))
async def cmd_msg(message: Message, state: FSMContext) -> None:
    """Handle /msg command - start broadcast message."""
    if not await is_admin(message):
        # Don't respond if not admin to keep command hidden
        return
    
    await state.set_state(BroadcastStates.waiting_for_message)
    await message.answer(
        "📢 **Режим рассылки**\n\n"
        "Отправьте сообщение, которое хотите разослать всем пользователям.\n"
        "Поддерживаются:\n"
        "• Текст (с форматированием)\n"
        "• Фото с подписью\n"
        "• Документы\n\n"
        "Для отмены используйте /cancel",
        parse_mode="Markdown"
    )


async def send_message_to_user(
    bot: Any,
    user_id: int, 
    from_chat_id: int,
    message_id: int
) -> bool:
    """
    Safely send message to a single user.
    
    Returns True if message was sent successfully.
    """
    try:
        await bot.copy_message(
            chat_id=user_id,
            from_chat_id=from_chat_id,
            message_id=message_id
        )
        logger.info(f"Message sent to user {user_id}")
        return True
        
    except TelegramForbiddenError:
        # User blocked the bot
        logger.warning(f"User {user_id} blocked the bot")
    except TelegramBadRequest as e:
        if "chat not found" in str(e).lower():
            logger.warning(f"Chat {user_id} not found")
        elif "user is deactivated" in str(e).lower():
            logger.warning(f"User {user_id} is deactivated")
        else:
            logger.error(f"Bad request for user {user_id}: {e}")
    except TelegramRetryAfter as e:
        logger.warning(f"Rate limit for user {user_id}, retry after {e.retry_after}s")
        await asyncio.sleep(e.retry_after)
        # Retry once after rate limit
        return await send_message_to_user(bot, user_id, from_chat_id, message_id)
    except TelegramAPIError as e:
        logger.error(f"Failed to send to user {user_id}: {e}")
    except Exception as e:
        logger.error(f"Unexpected error sending to user {user_id}: {e}")
        
    return False


@admin_router.message(BroadcastStates.waiting_for_message)
async def process_broadcast(message: Message, state: FSMContext) -> None:
    """Process broadcast message."""
    if not message.from_user or not await is_admin(message):
        return
    
    # Clear state first
    await state.clear()
    
    # Get all users from database
    db = get_database()
    async with db.get_session() as session:
        user_repo = UserRepository(session)
        users = await user_repo.get_all_users()
    
    if not users:
        await message.answer("❌ Нет пользователей для рассылки")
        return
    
    # Send initial status
    status_msg = await message.answer(
        f"🚀 Начинаю рассылку...\n"
        f"Всего пользователей: {len(users)}"
    )
    
    # Send messages with rate limiting
    sent_count = 0
    failed_count = 0
    
    for i, user in enumerate(users):
        # Skip admin to avoid self-messaging
        if user.id == message.from_user.id:
            continue
            
        success = await send_message_to_user(
            bot=message.bot,
            user_id=user.id,
            from_chat_id=message.chat.id,
            message_id=message.message_id
        )
        
        if success:
            sent_count += 1
        else:
            failed_count += 1
        
        # Update status every 10 users
        if (i + 1) % 10 == 0:
            await status_msg.edit_text(
                f"🚀 Рассылка в процессе...\n"
                f"Обработано: {i + 1}/{len(users)}\n"
                f"✅ Отправлено: {sent_count}\n"
                f"❌ Ошибок: {failed_count}"
            )
        
        # Rate limiting - 20 messages per second (conservative)
        await asyncio.sleep(0.05)
    
    # Final status
    await status_msg.edit_text(
        f"✅ **Рассылка завершена!**\n\n"
        f"📊 Статистика:\n"
        f"• Всего пользователей: {len(users) - 1}\n"  # -1 for admin
        f"• Успешно отправлено: {sent_count}\n"
        f"• Не удалось отправить: {failed_count}",
        parse_mode="Markdown"
    )