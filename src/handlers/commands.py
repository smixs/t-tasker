"""Command handlers for the bot."""

import logging

from aiogram import Router
from aiogram.filters import Command, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.types import Message

from src.core.database import get_database
from src.core.exceptions import BotError
from src.handlers.states import SetupStates
from src.models.db import User
from src.repositories.task import TaskRepository
from src.repositories.user import UserRepository
from src.services.encryption import get_encryption_service
from src.services.todoist_service import TodoistService
from src.utils.formatters import format_error_message

logger = logging.getLogger(__name__)

# Create router for commands
command_router = Router(name="commands")


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
        "/undo - Удалить последнюю задачу\n"
        "/recent - Показать последние 5 задач\n"
        "/autodelete - Вкл/выкл автоудаление предыдущей задачи\n"
        "/help - Эта справка\n"
        "/cancel - Отменить текущую операцию",
        parse_mode="Markdown"
    )


@command_router.message(Command("setup"))
async def cmd_setup(message: Message, state: FSMContext) -> None:
    """Handle /setup command - start token setup."""
    import os
    from pathlib import Path

    from aiogram.types import FSInputFile

    if not message.from_user:
        return

    # Create or update user in database first
    async with get_database().get_session() as session:
        user_repo = UserRepository(session)
        await user_repo.create_or_update(
            user_id=message.from_user.id,
            username=message.from_user.username,
            first_name=message.from_user.first_name,
            last_name=message.from_user.last_name,
            language_code=message.from_user.language_code
        )

    await state.set_state(SetupStates.waiting_for_token)

    # Send instruction image first
    image_path = Path("/app/assets/images/todoist_api_token_guide.png")
    logger.info(f"Looking for image at: {image_path}")
    logger.info(f"Image exists: {image_path.exists()}")
    logger.info(f"Current working directory: {os.getcwd()}")

    if image_path.exists():
        photo = FSInputFile(str(image_path))
        await message.answer_photo(
            photo=photo,
            caption=(
                "🔐 **Настройка подключения к Todoist**\n\n"
                "Для подключения мне нужен ваш Personal API Token:\n\n"
                "1. Откройте [Todoist Settings](https://app.todoist.com/app/settings/integrations/developer)\n"
                "2. Скопируйте ваш API token (см. скриншот выше)\n"
                "3. Отправьте его мне в следующем сообщении\n\n"
                "⚠️ Токен будет зашифрован и сохранен безопасно.\n"
                "Никто кроме вас не будет иметь к нему доступ."
            ),
            parse_mode="Markdown"
        )
    else:
        # Fallback to text-only message if image not found
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


@command_router.message(Command("undo"))
async def handle_undo(
    message: Message,
    user: "User",
    todoist_token: str
) -> None:
    """Handle /undo command - delete last created task."""
    if not message.from_user:
        return

    user_id = message.from_user.id
    logger.info(f"User {user_id} requested undo")

    # Get last task from database
    db = get_database()
    async with db.get_session() as session:
        task_repo = TaskRepository(session)
        last_task = await task_repo.get_last_task(user_id)

        if not last_task:
            await message.answer("❌ У вас нет задач для удаления.")
            return

        # Delete from Todoist
        try:
            async with TodoistService(todoist_token) as todoist:
                success = await todoist.delete_task(last_task.todoist_id)

                if success:
                    # Delete from database
                    await task_repo.delete_task_record(last_task.id)

                    await message.answer(
                        f"✅ Задача удалена:\n\n"
                        f"📝 <b>{last_task.task_content}</b>\n"
                        f"🗓 {last_task.task_due or 'Без срока'}",
                        parse_mode="HTML"
                    )
                else:
                    await message.answer(
                        "❌ Не удалось удалить задачу.\n"
                        "Возможно, она уже была удалена в Todoist."
                    )
        except BotError as e:
            logger.warning(f"Bot error deleting task: {e}")
            await message.answer(format_error_message(e))
        except Exception as e:
            logger.error(f"Unexpected error deleting task: {e}", exc_info=True)
            await message.answer("❌ Произошла ошибка при удалении задачи.")


@command_router.message(Command("autodelete"))
async def handle_autodelete(
    message: Message,
    user: "User"
) -> None:
    """Toggle auto-delete previous task setting."""
    if not message.from_user:
        return

    user_id = message.from_user.id

    # Toggle the setting
    db = get_database()
    async with db.get_session() as session:
        user_repo = UserRepository(session)

        # Toggle auto_delete_previous setting
        user.auto_delete_previous = not user.auto_delete_previous
        await user_repo.update(user)

        status = "включено ✅" if user.auto_delete_previous else "выключено ❌"

        await message.answer(
            f"🗑 Автоудаление предыдущей задачи {status}\n\n"
            f"{'Теперь при создании новой задачи предыдущая будет автоматически удаляться.' if user.auto_delete_previous else 'Все созданные задачи будут сохраняться.'}"
        )


@command_router.message(Command("recent"))
async def handle_recent(
    message: Message,
    user: "User"
) -> None:
    """Handle /recent command - show recent tasks with action buttons."""
    if not message.from_user:
        return

    user_id = message.from_user.id
    logger.info(f"User {user_id} requested recent tasks")

    # Get recent tasks
    db = get_database()
    async with db.get_session() as session:
        task_repo = TaskRepository(session)
        recent_tasks = await task_repo.get_recent_tasks(user_id, limit=5)

        if not recent_tasks:
            await message.answer("📋 У вас пока нет созданных задач.")
            return

        # Format tasks list
        text = "📋 <b>Последние задачи:</b>\n\n"

        for i, task in enumerate(recent_tasks, 1):
            text += (
                f"{i}. <b>{task.task_content}</b>\n"
                f"   🗓 {task.task_due or 'Без срока'}\n"
                f"   🏷 {task.task_labels or 'Без меток'}\n\n"
            )

        # Create inline keyboard with task management buttons
        from src.utils.formatters import create_recent_tasks_keyboard
        keyboard = create_recent_tasks_keyboard(recent_tasks)

        await message.answer(
            text,
            parse_mode="HTML",
            reply_markup=keyboard
        )


@command_router.message(Command("cancel"))
async def handle_cancel(message: Message, state: FSMContext) -> None:
    """Cancel current operation."""
    current_state = await state.get_state()

    if current_state:
        await state.clear()
        await message.answer("❌ Операция отменена")
    else:
        await message.answer("Нет активной операции для отмены")
