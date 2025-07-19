"""Message handlers for text, voice, and video messages."""

import logging

from aiogram import Bot, F, Router
from aiogram.types import Message

from src.core.database import get_database
from src.core.exceptions import BotError, UnauthorizedError
from src.repositories.user import UserRepository
from src.services.encryption import EncryptionService
from src.services.openai_service import OpenAIService
from src.services.todoist_service import TodoistService
from src.utils.formatters import (
    format_error_message,
    format_processing_message,
    task_to_telegram_html,
)

logger = logging.getLogger(__name__)

# Create router for messages
message_router = Router(name="messages")


@message_router.message(F.text)
async def handle_text_message(message: Message, bot: Bot) -> None:
    """Handle text messages."""
    if not message.from_user or not message.text:
        return

    user_id = message.from_user.id
    logger.info(f"Received text message from {user_id}: {message.text[:50]}...")

    # Send typing action
    await bot.send_chat_action(message.chat.id, "typing")
    
    # Send processing message
    processing_msg = await message.answer(format_processing_message())

    try:
        # Get user from database
        db = get_database()
        async with db.get_session() as session:
            user_repo = UserRepository(session)
            
            # Ensure user exists
            user = await user_repo.create_or_update(
                user_id=user_id,
                username=message.from_user.username,
                first_name=message.from_user.first_name,
                last_name=message.from_user.last_name,
                language_code=message.from_user.language_code
            )
            
            # Check if user has Todoist token
            if not user.todoist_token_encrypted:
                raise UnauthorizedError()
            
            # Decrypt token
            encryption = EncryptionService()
            todoist_token = encryption.decrypt(user.todoist_token_encrypted)
            
            # Parse task with OpenAI
            openai_service = OpenAIService()
            task = await openai_service.parse_task(message.text)
            
            # Create task in Todoist
            async with TodoistService(todoist_token) as todoist:
                # Check if project exists
                if task.project_name:
                    project = await todoist.get_project_by_name(task.project_name)
                    project_id = project["id"] if project else None
                else:
                    project_id = None
                
                # Create the task
                todoist_task = await todoist.create_task(
                    content=task.content,
                    description=task.description,
                    project_id=project_id,
                    labels=task.labels,
                    priority=task.priority or 1,
                    due_string=task.due_string,
                    duration=task.duration,
                )
            
            # Increment task counter
            await user_repo.increment_tasks_count(user_id)
            
            # Delete processing message
            await processing_msg.delete()
            
            # Send success message
            response = task_to_telegram_html(task, todoist_task)
            await message.answer(response, parse_mode="HTML")
            
    except BotError as e:
        logger.warning(f"Bot error for user {user_id}: {e}")
        await processing_msg.delete()
        await message.answer(format_error_message(e))
    except Exception as e:
        logger.error(f"Unexpected error for user {user_id}: {e}", exc_info=True)
        await processing_msg.delete()
        await message.answer(format_error_message(e))


@message_router.message(F.voice)
async def handle_voice_message(message: Message) -> None:
    """Handle voice messages."""
    if message.voice:
        logger.info(f"Received voice message: duration={message.voice.duration}s")

    # TODO: Download voice file
    # TODO: Transcribe with Deepgram/Whisper
    # TODO: Process transcribed text as task

    await message.answer(
        "🎤 Получил голосовое сообщение.\n"
        "Функция распознавания речи скоро будет доступна!"
    )


@message_router.message(F.video_note)
async def handle_video_note(message: Message) -> None:
    """Handle video notes (round videos)."""
    if message.video_note:
        logger.info(f"Received video note: duration={message.video_note.duration}s")

    # TODO: Extract audio from video
    # TODO: Process as voice message

    await message.answer(
        "📹 Получил видео сообщение.\n"
        "Функция обработки видео скоро будет доступна!"
    )


@message_router.message(F.video)
async def handle_video_message(message: Message) -> None:
    """Handle regular video messages."""
    logger.info("Received video message")

    # TODO: Check if video has audio track
    # TODO: Extract and process audio

    await message.answer(
        "📹 Получил видео.\n"
        "Для создания задач используйте текст или голосовые сообщения."
    )


@message_router.message(F.audio)
async def handle_audio_message(message: Message) -> None:
    """Handle audio file messages."""
    if message.audio:
        logger.info(f"Received audio file: {message.audio.file_name}")

    # TODO: Process as voice message

    await message.answer(
        "🎵 Получил аудио файл.\n"
        "Функция обработки аудио скоро будет доступна!"
    )
