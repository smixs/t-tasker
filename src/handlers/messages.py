"""Message handlers for text, voice, and video messages."""

import logging

from aiogram import Bot, F, Router
from aiogram.types import Message

from src.core.database import get_database
from src.core.exceptions import BotError, TranscriptionError
from src.models.db import User
from src.repositories.task import TaskRepository
from src.repositories.user import UserRepository
from src.services.deepgram_service import DeepgramService
from src.services.openai_service import OpenAIService
from src.services.todoist_service import TodoistService
from src.utils.formatters import (
    create_task_keyboard,
    format_error_message,
    format_processing_message,
    task_to_telegram_html,
)

logger = logging.getLogger(__name__)

# Create router for messages
message_router = Router(name="messages")


@message_router.message(F.text)
async def handle_text_message(
    message: Message,
    bot: Bot,
    user: "User",  # Injected by auth middleware
    todoist_token: str  # Injected by auth middleware
) -> None:
    """Handle text messages.
    
    Note: This handler requires auth middleware to be registered.
    The user and todoist_token are injected by the middleware.
    """
    if not message.from_user or not message.text:
        return

    user_id = message.from_user.id
    logger.info(f"Received text message from {user_id}: {message.text[:50]}...")

    # Send typing action
    await bot.send_chat_action(message.chat.id, "typing")

    # Send processing message
    processing_msg = await message.answer(format_processing_message())

    try:
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

        # Save task to database
        db = get_database()
        async with db.get_session() as session:
            task_repo = TaskRepository(session)
            created_task = await task_repo.create(
                user_id=user_id,
                message_text=message.text,
                message_type="text",
                task_schema=task,
                todoist_id=todoist_task["id"],
                todoist_url=todoist_task.get("url")
            )

            user_repo = UserRepository(session)
            await user_repo.increment_tasks_count(user_id)

        # Delete processing message
        await processing_msg.delete()

        # Send success message with inline keyboard
        response = task_to_telegram_html(task, todoist_task)
        keyboard = create_task_keyboard(created_task.id, todoist_task["id"])
        await message.answer(response, parse_mode="HTML", reply_markup=keyboard)

    except BotError as e:
        logger.warning(f"Bot error for user {user_id}: {e}")
        await processing_msg.delete()
        await message.answer(format_error_message(e))
    except Exception as e:
        logger.error(f"Unexpected error for user {user_id}: {e}", exc_info=True)
        await processing_msg.delete()
        await message.answer(format_error_message(e))


@message_router.message(F.voice)
async def handle_voice_message(
    message: Message,
    bot: Bot,
    user: "User",
    todoist_token: str
) -> None:
    """Handle voice messages."""
    if not message.voice:
        return

    user_id = message.from_user.id if message.from_user else 0
    logger.info(f"Received voice message from {user_id}: duration={message.voice.duration}s")

    # Check duration limit (5 minutes)
    if message.voice.duration > 300:
        await message.answer(
            "❌ Голосовое сообщение слишком длинное.\n"
            "Максимальная длительность: 5 минут."
        )
        return

    # Send typing action
    await bot.send_chat_action(message.chat.id, "typing")

    # Send processing message
    processing_msg = await message.answer("🎤 Распознаю голосовое сообщение...")

    try:
        # Download voice file
        file = await bot.get_file(message.voice.file_id)
        if not file.file_path:
            raise TranscriptionError("No file path in response")

        audio_io = await bot.download_file(file.file_path)
        if not audio_io:
            raise TranscriptionError("Failed to download audio")

        audio_bytes = audio_io.read()

        # Transcribe with Deepgram
        deepgram = DeepgramService()
        text = await deepgram.transcribe(audio_bytes, mime_type="audio/ogg;codecs=opus")

        # Update message with transcribed text
        await processing_msg.edit_text(
            f"📝 Распознано: {text}\n\n"
            "⏳ Создаю задачу..."
        )

        # Process transcribed text through OpenAI
        openai_service = OpenAIService()
        task = await openai_service.parse_task(text)

        # Create task in Todoist
        async with TodoistService(todoist_token) as todoist:
            if task.project_name:
                project = await todoist.get_project_by_name(task.project_name)
                project_id = project["id"] if project else None
            else:
                project_id = None

            todoist_task = await todoist.create_task(
                content=task.content,
                description=task.description,
                project_id=project_id,
                labels=task.labels,
                priority=task.priority or 1,
                due_string=task.due_string,
                duration=task.duration,
            )

        # Save task to database
        db = get_database()
        async with db.get_session() as session:
            task_repo = TaskRepository(session)
            created_task = await task_repo.create(
                user_id=user_id,
                message_text=text,  # Распознанный текст из голосового сообщения
                message_type="voice",
                task_schema=task,
                todoist_id=todoist_task["id"],
                todoist_url=todoist_task.get("url")
            )

            user_repo = UserRepository(session)
            await user_repo.increment_tasks_count(user_id)

        # Delete processing message
        await processing_msg.delete()

        # Send success message with inline keyboard
        response = task_to_telegram_html(task, todoist_task)
        keyboard = create_task_keyboard(created_task.id, todoist_task["id"])
        await message.answer(response, parse_mode="HTML", reply_markup=keyboard)

    except TranscriptionError as e:
        logger.warning(f"Transcription error for user {user_id}: {e}")
        await processing_msg.delete()
        await message.answer(format_error_message(e))
    except BotError as e:
        logger.warning(f"Bot error for user {user_id}: {e}")
        await processing_msg.delete()
        await message.answer(format_error_message(e))
    except Exception as e:
        logger.error(f"Unexpected error for user {user_id}: {e}", exc_info=True)
        await processing_msg.delete()
        await message.answer(
            "❌ Произошла ошибка при обработке голосового сообщения.\n"
            "Попробуйте еще раз."
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
