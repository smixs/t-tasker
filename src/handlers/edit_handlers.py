"""Edit mode message handlers for FSM states."""

import logging

from aiogram import Router
from aiogram.fsm.context import FSMContext
from aiogram.types import Message

from src.core.exceptions import BotError
from src.handlers.states import EditTaskStates
from src.services.openai_service import OpenAIService
from src.services.todoist_service import TodoistService
from src.utils.formatters import format_error_message

logger = logging.getLogger(__name__)

# Create router for edit mode messages
edit_router = Router(name="edit")


@edit_router.message(EditTaskStates.editing_content)
async def handle_content_edit(message: Message, state: FSMContext) -> None:
    """Handle text input for content editing."""
    if not message.text:
        await message.answer("❌ Пожалуйста, введите текст задачи")
        return

    # Get state data
    data = await state.get_data()
    todoist_id = data.get("todoist_id")
    todoist_token = data.get("todoist_token")

    if not todoist_id or not todoist_token:
        await message.answer("❌ Ошибка: данные задачи не найдены")
        await state.clear()
        return

    try:
        # Update task in Todoist
        async with TodoistService(todoist_token) as todoist:
            await todoist.update_task(todoist_id, content=message.text)

        # Clear state
        await state.clear()

        # Send success message
        await message.answer(f"✅ Текст задачи обновлен:\n\n<b>{message.text}</b>", parse_mode="HTML")

    except BotError as e:
        logger.warning(f"Bot error updating content: {e}")
        await message.answer(format_error_message(e))
    except Exception as e:
        logger.error(f"Unexpected error updating content: {e}", exc_info=True)
        await message.answer("❌ Произошла ошибка при обновлении задачи")
    finally:
        await state.clear()


@edit_router.message(EditTaskStates.editing_due_date)
async def handle_due_date_edit(message: Message, state: FSMContext) -> None:
    """Handle text input for due date editing."""
    if not message.text:
        await message.answer("❌ Пожалуйста, введите дату")
        return

    # Get state data
    data = await state.get_data()
    todoist_id = data.get("todoist_id")
    todoist_token = data.get("todoist_token")

    if not todoist_id or not todoist_token:
        await message.answer("❌ Ошибка: данные задачи не найдены")
        await state.clear()
        return

    try:
        # Parse date using OpenAI without intent classification
        openai_service = OpenAIService()
        parsed_date = await openai_service.parse_date_only(message.text)

        # Update task in Todoist
        async with TodoistService(todoist_token) as todoist:
            await todoist.update_task(todoist_id, due_string=parsed_date)

        # Clear state
        await state.clear()

        # Send success message
        await message.answer(f"✅ Дата задачи обновлена: <b>{parsed_date}</b>", parse_mode="HTML")

    except BotError as e:
        logger.warning(f"Bot error updating due date: {e}")
        await message.answer(format_error_message(e))
    except Exception as e:
        logger.error(f"Unexpected error updating due date: {e}", exc_info=True)
        await message.answer("❌ Произошла ошибка при обновлении даты")
    finally:
        await state.clear()
