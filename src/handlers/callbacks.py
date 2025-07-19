"""Callback query handlers for inline keyboards."""

import logging

from aiogram import F, Router
from aiogram.types import CallbackQuery

from src.core.database import get_database
from src.core.exceptions import BotError
from src.models.db import User
from src.repositories.task import TaskRepository
from src.services.todoist_service import TodoistService
from src.utils.formatters import create_recent_tasks_keyboard, format_error_message

logger = logging.getLogger(__name__)

# Create router for callbacks
callback_router = Router(name="callbacks")


@callback_router.callback_query(F.data.startswith("delete_task:"))
async def handle_delete_task(
    callback: CallbackQuery,
    user: "User",
    todoist_token: str
) -> None:
    """Handle delete task callback."""
    # Parse callback data
    parts = callback.data.split(":")
    if len(parts) != 3:
        await callback.answer("❌ Неверный формат данных", show_alert=True)
        return

    _, task_id_str, todoist_id = parts
    task_id = int(task_id_str)

    logger.info(f"User {user.id} deleting task {task_id} (todoist: {todoist_id})")

    try:
        # Delete from Todoist
        async with TodoistService(todoist_token) as todoist:
            success = await todoist.delete_task(todoist_id)

            if success:
                # Delete from database
                db = get_database()
                async with db.get_session() as session:
                    task_repo = TaskRepository(session)
                    await task_repo.delete_task_record(task_id)

                # Update message
                if callback.message:
                    await callback.message.edit_text(
                        f"{callback.message.text}\n\n❌ <b>Задача удалена</b>",
                        parse_mode="HTML"
                    )

                await callback.answer("✅ Задача удалена")
            else:
                await callback.answer(
                    "❌ Не удалось удалить задачу. Возможно, она уже была удалена.",
                    show_alert=True
                )
    except BotError as e:
        logger.warning(f"Bot error deleting task: {e}")
        await callback.answer(format_error_message(e), show_alert=True)
    except Exception as e:
        logger.error(f"Unexpected error deleting task: {e}", exc_info=True)
        await callback.answer("❌ Произошла ошибка при удалении задачи", show_alert=True)


@callback_router.callback_query(F.data.startswith("complete_task:"))
async def handle_complete_task(
    callback: CallbackQuery,
    user: "User",
    todoist_token: str
) -> None:
    """Handle complete task callback."""
    # Parse callback data
    parts = callback.data.split(":")
    if len(parts) != 3:
        await callback.answer("❌ Неверный формат данных", show_alert=True)
        return

    _, task_id_str, todoist_id = parts
    task_id = int(task_id_str)

    logger.info(f"User {user.id} completing task {task_id} (todoist: {todoist_id})")

    try:
        # Complete in Todoist
        async with TodoistService(todoist_token) as todoist:
            success = await todoist.complete_task(todoist_id)

            if success:
                # Update message
                if callback.message:
                    await callback.message.edit_text(
                        f"{callback.message.text}\n\n✅ <b>Задача выполнена</b>",
                        parse_mode="HTML"
                    )

                await callback.answer("✅ Задача отмечена выполненной")
            else:
                await callback.answer(
                    "❌ Не удалось отметить задачу выполненной. Возможно, она уже выполнена.",
                    show_alert=True
                )
    except BotError as e:
        logger.warning(f"Bot error completing task: {e}")
        await callback.answer(format_error_message(e), show_alert=True)
    except Exception as e:
        logger.error(f"Unexpected error completing task: {e}", exc_info=True)
        await callback.answer("❌ Произошла ошибка при выполнении задачи", show_alert=True)


@callback_router.callback_query(F.data.startswith("edit_task:"))
async def handle_edit_task(callback: CallbackQuery) -> None:
    """Handle edit task callback."""
    await callback.answer(
        "✏️ Редактирование задач пока не реализовано.\n"
        "Вы можете удалить задачу и создать новую.",
        show_alert=True
    )


@callback_router.callback_query(F.data == "refresh_recent_tasks")
async def handle_refresh_recent(
    callback: CallbackQuery,
    user: "User"
) -> None:
    """Handle refresh recent tasks callback."""
    if not callback.message:
        return

    user_id = user.id
    logger.info(f"User {user_id} refreshing recent tasks")

    # Get recent tasks
    db = get_database()
    async with db.get_session() as session:
        task_repo = TaskRepository(session)
        recent_tasks = await task_repo.get_recent_tasks(user_id, limit=5)

        if not recent_tasks:
            await callback.message.edit_text("📋 У вас пока нет созданных задач.")
            await callback.answer("Обновлено")
            return

        # Format tasks list
        text = "📋 <b>Последние задачи:</b>\n\n"

        for i, task in enumerate(recent_tasks, 1):
            text += (
                f"{i}. <b>{task.task_content}</b>\n"
                f"   🗓 {task.task_due or 'Без срока'}\n"
                f"   🏷 {task.task_labels or 'Без меток'}\n\n"
            )

        # Update message with new keyboard
        keyboard = create_recent_tasks_keyboard(recent_tasks)

        await callback.message.edit_text(
            text,
            parse_mode="HTML",
            reply_markup=keyboard
        )

        await callback.answer("✅ Список обновлен")
