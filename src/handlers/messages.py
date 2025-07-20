"""Message handlers for text, voice, and video messages."""

import logging

from aiogram import Bot, F, Router
from aiogram.types import Message

from src.core.database import get_database
from src.core.exceptions import BotError, TranscriptionError
from src.models.db import User
from src.models.intent import CommandExecution, TaskCreation
from src.repositories.task import TaskRepository
from src.repositories.user import UserRepository
from src.services.command_executor import CommandExecutor
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


def get_forward_author(message: Message) -> str | None:
    """Extract forward author name from message.
    
    Args:
        message: Telegram message
        
    Returns:
        Author name or None if not a forwarded message
    """
    # Check new API (aiogram 3.x)
    if message.forward_origin:
        # MessageOriginUser - regular user
        if hasattr(message.forward_origin, 'sender_user') and message.forward_origin.sender_user:
            return message.forward_origin.sender_user.full_name
        # MessageOriginHiddenUser - hidden user
        elif hasattr(message.forward_origin, 'sender_user_name'):
            return message.forward_origin.sender_user_name or "Скрытый пользователь"
        # MessageOriginChannel/Chat
        elif hasattr(message.forward_origin, 'chat') and message.forward_origin.chat:
            return message.forward_origin.chat.title

    # Check old API (for compatibility)
    elif message.forward_from:
        return message.forward_from.full_name

    return None

# Create router for messages
message_router = Router(name="messages")


@message_router.message(F.text)
async def handle_text_message(
    message: Message,
    bot: Bot,
    user: "User",  # Injected by auth middleware
    todoist_token: str,  # Injected by auth middleware
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
        # Check if auto-delete is enabled
        if user.auto_delete_previous:
            # Get and delete previous task
            db = get_database()
            async with db.get_session() as session:
                task_repo = TaskRepository(session)
                last_task = await task_repo.get_last_task(user_id)

                if last_task and last_task.todoist_id:
                    try:
                        # Delete from Todoist silently
                        async with TodoistService(todoist_token) as todoist:
                            await todoist.delete_task(last_task.todoist_id)
                        # Delete from database
                        await task_repo.delete_task_record(last_task.id)
                        logger.info(f"Auto-deleted previous task {last_task.id} for user {user_id}")
                    except Exception as e:
                        logger.warning(f"Failed to auto-delete previous task: {e}")
                        # Continue with new task creation even if deletion fails

        # Extract forward author if this is a forwarded message
        forward_author = get_forward_author(message)
        if forward_author:
            logger.info(f"Processing forwarded message from: {forward_author}")
            logger.debug(f"Full message text: {message.text}")
            logger.debug(f"Forward origin: {message.forward_origin}")
        else:
            logger.debug("Not a forwarded message")

        # Parse intent with OpenAI
        openai_service = OpenAIService()
        intent = await openai_service.parse_intent(
            message.text,
            user_language=user.language_code,
            forward_author=None  # Don't pass forward_author to OpenAI anymore
        )

        # Route based on intent type
        if isinstance(intent, TaskCreation):
            # Existing task creation logic
            task = intent.task
            
            # If this is a forwarded message, add author to task content
            if forward_author:
                task.content = f"{forward_author}: {task.content}"
                logger.info(f"Modified forwarded task - content: '{task.content}'")
            
            logger.info(f"Task parsed - content: '{task.content}', due_string: '{task.due_string}'")

            # Create task in Todoist
            async with TodoistService(todoist_token) as todoist:
                # Check if project exists
                if task.project_name:
                    project = await todoist.get_project_by_name(task.project_name)
                    project_id = project["id"] if project else None
                else:
                    project_id = None

                # Parse due_string if present
                parsed_due_string = task.due_string
                if task.due_string:
                    parsed_due_string = await openai_service.parse_date_only(
                        task.due_string,
                        user_language=user.language_code
                    )
                    logger.info(f"Parsed due_string: '{task.due_string}' -> '{parsed_due_string}'")

                # Create the task
                todoist_task = await todoist.create_task(
                    content=task.content,
                    description=task.description,
                    project_id=project_id,
                    labels=task.labels,
                    priority=task.priority or 1,
                    due_string=parsed_due_string,
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
                    todoist_url=todoist_task.get("url"),
                )

                user_repo = UserRepository(session)
                await user_repo.increment_tasks_count(user_id)

            # Delete processing message
            await processing_msg.delete()

            # Send success message with inline keyboard
            response = task_to_telegram_html(task, todoist_task)
            keyboard = create_task_keyboard(created_task.id, todoist_task["id"])
            await message.answer(response, parse_mode="HTML", reply_markup=keyboard)

        elif isinstance(intent, CommandExecution):
            # Execute command through CommandExecutor
            executor = CommandExecutor()

            # Delete processing message before showing command result
            await processing_msg.delete()

            # Execute command and send response
            try:
                response = await executor.execute(intent, user_id, todoist_token)
                await message.answer(response, parse_mode="HTML")
            except BotError as e:
                # Command execution error
                await message.answer(format_error_message(e))
        else:
            # Should not happen, but handle gracefully
            logger.error(f"Unknown intent type: {type(intent)}")
            await processing_msg.delete()
            await message.answer("❌ Не удалось понять команду. Попробуйте еще раз.")

    except BotError as e:
        logger.warning(f"Bot error for user {user_id}: {e}")
        await processing_msg.delete()
        await message.answer(format_error_message(e))
    except Exception as e:
        logger.error(f"Unexpected error for user {user_id}: {e}", exc_info=True)
        await processing_msg.delete()
        await message.answer(format_error_message(e))


@message_router.message(F.voice)
async def handle_voice_message(message: Message, bot: Bot, user: "User", todoist_token: str) -> None:
    """Handle voice messages."""
    if not message.voice:
        return

    user_id = message.from_user.id if message.from_user else 0
    logger.info(f"Received voice message from {user_id}: duration={message.voice.duration}s")

    # Check duration limit (5 minutes)
    if message.voice.duration > 300:
        await message.answer("❌ Голосовое сообщение слишком длинное.\n" "Максимальная длительность: 5 минут.")
        return

    # Send typing action
    await bot.send_chat_action(message.chat.id, "typing")

    # Send processing message
    processing_msg = await message.answer("🎤 Распознаю голосовое сообщение...")

    try:
        # Check if auto-delete is enabled
        if user.auto_delete_previous:
            # Get and delete previous task
            db = get_database()
            async with db.get_session() as session:
                task_repo = TaskRepository(session)
                last_task = await task_repo.get_last_task(user_id)

                if last_task and last_task.todoist_id:
                    try:
                        # Delete from Todoist silently
                        async with TodoistService(todoist_token) as todoist:
                            await todoist.delete_task(last_task.todoist_id)
                        # Delete from database
                        await task_repo.delete_task_record(last_task.id)
                        logger.info(f"Auto-deleted previous task {last_task.id} for user {user_id}")
                    except Exception as e:
                        logger.warning(f"Failed to auto-delete previous task: {e}")
                        # Continue with new task creation even if deletion fails

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
        await processing_msg.edit_text(f"📝 Распознано: {text}\n\n" "⏳ Создаю задачу...")

        # Extract forward author if this is a forwarded message
        forward_author = get_forward_author(message)
        if forward_author:
            logger.info(f"Processing forwarded voice message from: {forward_author}")

        # Process transcribed text through OpenAI for intent
        openai_service = OpenAIService()
        intent = await openai_service.parse_intent(
            text,
            user_language=user.language_code,
            forward_author=None  # Don't pass forward_author to OpenAI anymore
        )

        # Route based on intent type
        if isinstance(intent, TaskCreation):
            # Existing task creation logic
            task = intent.task
            
            # If this is a forwarded message, add author to task content
            if forward_author:
                task.content = f"{forward_author}: {task.content}"
                logger.info(f"Modified forwarded voice task - content: '{task.content}'")

            # Create task in Todoist
            async with TodoistService(todoist_token) as todoist:
                if task.project_name:
                    project = await todoist.get_project_by_name(task.project_name)
                    project_id = project["id"] if project else None
                else:
                    project_id = None

                # Parse due_string if present
                parsed_due_string = task.due_string
                if task.due_string:
                    parsed_due_string = await openai_service.parse_date_only(
                        task.due_string,
                        user_language=user.language_code
                    )
                    logger.info(f"Parsed due_string: '{task.due_string}' -> '{parsed_due_string}'")

                todoist_task = await todoist.create_task(
                    content=task.content,
                    description=task.description,
                    project_id=project_id,
                    labels=task.labels,
                    priority=task.priority or 1,
                    due_string=parsed_due_string,
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
                    todoist_url=todoist_task.get("url"),
                )

                user_repo = UserRepository(session)
                await user_repo.increment_tasks_count(user_id)

            # Delete processing message
            await processing_msg.delete()

            # Send success message with inline keyboard
            response = task_to_telegram_html(task, todoist_task)
            keyboard = create_task_keyboard(created_task.id, todoist_task["id"])
            await message.answer(response, parse_mode="HTML", reply_markup=keyboard)

        elif isinstance(intent, CommandExecution):
            # Execute command through CommandExecutor
            executor = CommandExecutor()

            # Delete processing message before showing command result
            await processing_msg.delete()

            # Execute command and send response
            try:
                response = await executor.execute(intent, user_id, todoist_token)
                await message.answer(response, parse_mode="HTML")
            except BotError as e:
                # Command execution error
                await message.answer(format_error_message(e))
        else:
            # Should not happen, but handle gracefully
            logger.error(f"Unknown intent type from voice: {type(intent)}")
            await processing_msg.delete()
            await message.answer("❌ Не удалось понять команду из голосового сообщения.")

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
        await message.answer("❌ Произошла ошибка при обработке голосового сообщения.\n" "Попробуйте еще раз.")


@message_router.message(F.video_note)
async def handle_video_note(message: Message) -> None:
    """Handle video notes (round videos)."""
    if message.video_note:
        logger.info(f"Received video note: duration={message.video_note.duration}s")

    # TODO: Extract audio from video
    # TODO: Process as voice message

    await message.answer("📹 Получил видео сообщение.\n" "Функция обработки видео скоро будет доступна!")


@message_router.message(F.video)
async def handle_video_message(message: Message) -> None:
    """Handle regular video messages."""
    logger.info("Received video message")

    # TODO: Check if video has audio track
    # TODO: Extract and process audio

    await message.answer("📹 Получил видео.\n" "Для создания задач используйте текст или голосовые сообщения.")


@message_router.message(F.audio)
async def handle_audio_message(message: Message) -> None:
    """Handle audio file messages."""
    if message.audio:
        logger.info(f"Received audio file: {message.audio.file_name}")

    # TODO: Process as voice message

    await message.answer("🎵 Получил аудио файл.\n" "Функция обработки аудио скоро будет доступна!")
