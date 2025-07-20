"""Edit mode message handlers for FSM states."""

import logging
from io import BytesIO

from aiogram import Bot, F, Router
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import Message

from src.core.exceptions import BotError, TranscriptionError
from src.handlers.states import EditTaskStates
from src.services.deepgram_service import DeepgramService
from src.services.openai_service import OpenAIService
from src.services.todoist_service import TodoistService
from src.utils.formatters import format_error_message

logger = logging.getLogger(__name__)

# Create router for edit mode messages
edit_router = Router(name="edit")


async def process_content_edit(text: str, state: FSMContext, message: Message) -> None:
    """Process content edit logic - can be called from text or voice handlers."""
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
            await todoist.update_task(todoist_id, content=text)

        # Clear state
        await state.clear()

        # Send success message
        await message.answer(f"✅ Текст задачи обновлен:\n\n<b>{text}</b>", parse_mode="HTML")

    except BotError as e:
        logger.warning(f"Bot error updating content: {e}")
        await message.answer(format_error_message(e))
    except Exception as e:
        logger.error(f"Unexpected error updating content: {e}", exc_info=True)
        await message.answer("❌ Произошла ошибка при обновлении задачи")
    finally:
        await state.clear()


@edit_router.message(EditTaskStates.editing_content)
async def handle_content_edit(message: Message, state: FSMContext) -> None:
    """Handle text input for content editing."""
    if not message.text:
        await message.answer("❌ Пожалуйста, введите текст задачи")
        return

    await process_content_edit(message.text, state, message)


async def process_due_date_edit(text: str, state: FSMContext, message: Message) -> None:
    """Process due date edit logic - can be called from text or voice handlers."""
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
        parsed_date = await openai_service.parse_date_only(text)

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


@edit_router.message(EditTaskStates.editing_due_date)
async def handle_due_date_edit(message: Message, state: FSMContext) -> None:
    """Handle text input for due date editing."""
    if not message.text:
        await message.answer("❌ Пожалуйста, введите дату")
        return

    await process_due_date_edit(message.text, state, message)


@edit_router.message(F.voice | F.video_note | F.video, StateFilter(EditTaskStates.editing_content, EditTaskStates.editing_due_date))
async def handle_voice_in_edit_mode(message: Message, state: FSMContext, bot: Bot) -> None:
    """Handle voice/video messages in any edit state - transcribe and process as text."""
    # Get current state to determine which field we're editing
    current_state = await state.get_state()
    
    try:
        # Determine file type and download
        if message.voice:
            file_id = message.voice.file_id
            mime_type = "audio/ogg;codecs=opus"
        elif message.video_note:
            # Video notes are not supported yet
            await message.answer("📹 Видео сообщения пока не поддерживаются в режиме редактирования")
            return
        elif message.video:
            # Regular videos are not supported yet
            await message.answer("📹 Видео сообщения пока не поддерживаются в режиме редактирования")
            return
        else:
            # This shouldn't happen with our filter
            logger.error("Unexpected message type in voice handler")
            return
        
        # Download voice file
        voice_file = await bot.get_file(file_id)
        voice_buffer = BytesIO()
        await bot.download_file(voice_file.file_path, voice_buffer)
        voice_buffer.seek(0)

        # Send typing action
        await message.chat.do("typing")

        # Transcribe audio
        deepgram_service = DeepgramService()
        transcript = await deepgram_service.transcribe_audio(
            audio_data=voice_buffer.getvalue(),
            mime_type=mime_type,
            filename="voice.ogg"
        )

        if not transcript:
            await message.answer("❌ Не удалось распознать голосовое сообщение")
            return

        # Show transcribed text to user
        await message.answer(f"🎤 Распознано: <i>{transcript}</i>", parse_mode="HTML")

        # Process based on current state
        if current_state == EditTaskStates.editing_content:
            await process_content_edit(transcript, state, message)
        elif current_state == EditTaskStates.editing_due_date:
            await process_due_date_edit(transcript, state, message)

    except TranscriptionError as e:
        logger.warning(f"Transcription error in edit mode: {e}")
        await message.answer("❌ Ошибка распознавания голоса. Попробуйте ещё раз или введите текстом.")
    except Exception as e:
        logger.error(f"Unexpected error handling voice in edit mode: {e}", exc_info=True)
        await message.answer("❌ Произошла ошибка при обработке голосового сообщения")
