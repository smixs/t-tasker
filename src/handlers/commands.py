"""Command handlers for the bot."""

import logging

from aiogram import Router
from aiogram.filters import Command, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import Message

from src.core.database import get_database
from src.repositories.user import UserRepository
from src.services.encryption import get_encryption_service

logger = logging.getLogger(__name__)

# Create router for commands
command_router = Router(name="commands")


class SetupStates(StatesGroup):
    """States for setup process."""

    waiting_for_token = State()


@command_router.message(CommandStart())
async def cmd_start(message: Message) -> None:
    """Handle /start command."""
    if not message.from_user:
        return
    
    # Create or update user in database
    async with get_database().get_session() as session:
        user_repo = UserRepository(session)
        await user_repo.create_or_update(
            user_id=message.from_user.id,
            username=message.from_user.username,
            first_name=message.from_user.first_name,
            last_name=message.from_user.last_name,
            language_code=message.from_user.language_code
        )
    
    await message.answer(
        "👋 Привет! Я помогу превратить ваши сообщения в задачи Todoist.\n\n"
        "Что я умею:\n"
        "• Создавать задачи из текстовых сообщений\n"
        "• Распознавать голосовые сообщения\n"
        "• Извлекать задачи из видео сообщений\n\n"
        "Для начала работы подключите ваш аккаунт Todoist командой /setup"
    )


@command_router.message(Command("help"))
async def cmd_help(message: Message) -> None:
    """Handle /help command."""
    await message.answer(
        "📖 **Как использовать бота:**\n\n"
        "1. Подключите Todoist: /setup\n"
        "2. Отправьте сообщение с задачей\n"
        "3. Бот создаст задачу в Todoist\n\n"
        "**Примеры сообщений:**\n"
        "• Купить молоко завтра\n"
        "• Встреча с клиентом в пятницу в 15:00\n"
        "• Оплатить счета до конца месяца !высокий приоритет\n\n"
        "**Команды:**\n"
        "/start - Начать работу\n"
        "/setup - Подключить Todoist\n"
        "/status - Проверить статус подключения\n"
        "/help - Эта справка\n"
        "/cancel - Отменить текущую операцию",
        parse_mode="Markdown"
    )


@command_router.message(Command("setup"))
async def cmd_setup(message: Message, state: FSMContext) -> None:
    """Handle /setup command - start token setup."""
    await state.set_state(SetupStates.waiting_for_token)
    
    await message.answer(
        "🔐 **Настройка подключения к Todoist**\n\n"
        "Для подключения мне нужен ваш Personal API Token:\n\n"
        "1. Откройте [Todoist Settings](https://app.todoist.com/app/settings/integrations/developer)\n"
        "2. Скопируйте ваш API token\n"
        "3. Отправьте его мне в следующем сообщении\n\n"
        "⚠️ Токен будет зашифрован и сохранен безопасно.\n"
        "Никто кроме вас не будет иметь к нему доступ.",
        parse_mode="Markdown",
        disable_web_page_preview=True
    )


@command_router.message(SetupStates.waiting_for_token)
async def process_token(message: Message, state: FSMContext) -> None:
    """Process Todoist token."""
    if not message.text or not message.from_user:
        await message.answer("❌ Пожалуйста, отправьте токен текстом.")
        return
    
    token = message.text.strip()
    
    # Basic validation
    if len(token) < 20 or len(token) > 100:
        await message.answer(
            "❌ Неверный формат токена. Токен должен быть длиной 40 символов.\n"
            "Попробуйте еще раз или используйте /cancel для отмены."
        )
        return
    
    # Delete message with token for security
    await message.delete()
    
    # Encrypt and save token
    try:
        encryption = get_encryption_service()
        encrypted_token = encryption.encrypt(token)
        
        async with get_database().get_session() as session:
            user_repo = UserRepository(session)
            success = await user_repo.update_todoist_token(
                user_id=message.from_user.id,
                encrypted_token=encrypted_token
            )
        
        if success:
            await message.answer(
                "✅ Токен успешно сохранен!\n\n"
                "Теперь вы можете отправлять мне сообщения, "
                "и я буду создавать из них задачи в Todoist."
            )
            await state.clear()
        else:
            await message.answer(
                "❌ Не удалось сохранить токен. Попробуйте позже."
            )
    except Exception as e:
        logger.error(f"Failed to save token: {e}")
        await message.answer(
            "❌ Произошла ошибка при сохранении токена. Попробуйте позже."
        )


@command_router.message(Command("status"))
async def cmd_status(message: Message) -> None:
    """Check connection status."""
    if not message.from_user:
        return
    
    async with get_database().get_session() as session:
        user_repo = UserRepository(session)
        user = await user_repo.get_by_id(message.from_user.id)
    
    if not user or not user.todoist_token_encrypted:
        await message.answer(
            "❌ Todoist не подключен.\n"
            "Используйте /setup для настройки."
        )
    else:
        await message.answer(
            f"✅ Todoist подключен\n\n"
            f"📊 Статистика:\n"
            f"• Создано задач: {user.tasks_created}\n"
            f"• Последняя задача: {user.last_task_at.strftime('%d.%m.%Y %H:%M') if user.last_task_at else 'Нет'}"
        )


@command_router.message(Command("cancel"))
async def cmd_cancel(message: Message, state: FSMContext) -> None:
    """Cancel current operation."""
    current_state = await state.get_state()
    
    if current_state is None:
        await message.answer("Нет активных операций для отмены.")
    else:
        await state.clear()
        await message.answer("❌ Операция отменена.")