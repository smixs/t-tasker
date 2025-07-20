"""Callback query handlers for inline keyboards."""

import logging

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery

from src.core.database import get_database
from src.core.exceptions import BotError
from src.handlers.states import EditTaskStates
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
async def handle_edit_task(
    callback: CallbackQuery,
    state: FSMContext,
    user: "User",
    todoist_token: str
) -> None:
    """Handle edit task callback."""
    from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

    from src.handlers.states import EditTaskStates

    # Parse callback data
    parts = callback.data.split(":")
    if len(parts) != 3:
        await callback.answer("❌ Неверный формат данных", show_alert=True)
        return

    _, task_id_str, todoist_id = parts
    task_id = int(task_id_str)

    # Save task info to state
    await state.update_data(
        task_id=task_id,
        todoist_id=todoist_id,
        todoist_token=todoist_token
    )

    # Create edit options keyboard
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📝 Изменить текст", callback_data="edit_field:content")],
        [InlineKeyboardButton(text="📅 Изменить дату", callback_data="edit_field:due_date")],
        [InlineKeyboardButton(text="🔴 Изменить приоритет", callback_data="edit_field:priority")],
        [InlineKeyboardButton(text="❌ Отмена", callback_data="edit_cancel")]
    ])

    # Set state
    await state.set_state(EditTaskStates.choosing_field)

    # Edit message
    if callback.message:
        await callback.message.edit_text(
            "✏️ <b>Редактирование задачи</b>\n\n"
            "Выберите, что хотите изменить:",
            parse_mode="HTML",
            reply_markup=keyboard
        )

    await callback.answer()


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


@callback_router.callback_query(F.data.startswith("edit_field:"), EditTaskStates.choosing_field)
async def handle_edit_field_choice(
    callback: CallbackQuery,
    state: FSMContext
) -> None:
    """Handle field selection for editing."""
    from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

    from src.handlers.states import EditTaskStates

    field = callback.data.split(":")[1]

    # Update state with chosen field
    await state.update_data(edit_field=field)

    # Create cancel keyboard
    cancel_keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="❌ Отмена", callback_data="edit_cancel")]
    ])

    # Set appropriate state and prompt
    if field == "content":
        await state.set_state(EditTaskStates.editing_content)
        prompt = "📝 Введите новый текст задачи:"
    elif field == "due_date":
        await state.set_state(EditTaskStates.editing_due_date)
        prompt = "📅 Введите новую дату (например: завтра, 25 декабря, через неделю):"
    elif field == "priority":
        await state.set_state(EditTaskStates.editing_priority)
        # Create priority keyboard
        cancel_keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🔴 Высокий", callback_data="edit_priority:4")],
            [InlineKeyboardButton(text="🟡 Средний", callback_data="edit_priority:3")],
            [InlineKeyboardButton(text="🔵 Низкий", callback_data="edit_priority:2")],
            [InlineKeyboardButton(text="⚪ Без приоритета", callback_data="edit_priority:1")],
            [InlineKeyboardButton(text="❌ Отмена", callback_data="edit_cancel")]
        ])
        prompt = "🔴 Выберите новый приоритет:"
    else:
        await callback.answer("❌ Неизвестное поле", show_alert=True)
        return

    if callback.message:
        await callback.message.edit_text(
            prompt,
            parse_mode="HTML",
            reply_markup=cancel_keyboard
        )

    await callback.answer()


@callback_router.callback_query(F.data == "edit_cancel")
async def handle_edit_cancel(
    callback: CallbackQuery,
    state: FSMContext
) -> None:
    """Handle edit cancellation."""
    # Clear state
    await state.clear()

    # Delete message
    if callback.message:
        await callback.message.delete()

    await callback.answer("✅ Редактирование отменено")


@callback_router.callback_query(F.data.startswith("edit_priority:"), EditTaskStates.editing_priority)
async def handle_priority_selection(
    callback: CallbackQuery,
    state: FSMContext
) -> None:
    """Handle priority selection."""
    from src.services.todoist_service import TodoistService
    from src.utils.formatters import format_error_message

    priority = int(callback.data.split(":")[1])

    # Get state data
    data = await state.get_data()
    todoist_id = data.get("todoist_id")
    todoist_token = data.get("todoist_token")

    if not todoist_id or not todoist_token:
        await callback.answer("❌ Ошибка: данные задачи не найдены", show_alert=True)
        await state.clear()
        return

    try:
        # Update task in Todoist
        async with TodoistService(todoist_token) as todoist:
            await todoist.update_task(todoist_id, priority=priority)

        # Clear state
        await state.clear()

        # Update message
        priority_text = {
            1: "⚪ Без приоритета",
            2: "🔵 Низкий",
            3: "🟡 Средний",
            4: "🔴 Высокий"
        }

        if callback.message:
            await callback.message.edit_text(
                f"✅ Приоритет задачи изменен на: {priority_text.get(priority, 'Неизвестный')}",
                parse_mode="HTML"
            )

        await callback.answer("✅ Приоритет обновлен")

    except BotError as e:
        logger.warning(f"Bot error updating priority: {e}")
        await callback.answer(format_error_message(e), show_alert=True)
    except Exception as e:
        logger.error(f"Unexpected error updating priority: {e}", exc_info=True)
        await callback.answer("❌ Произошла ошибка при обновлении приоритета", show_alert=True)
    finally:
        await state.clear()
