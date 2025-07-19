"""Message handlers for text, voice, and video messages."""

import logging

from aiogram import Router, F
from aiogram.types import Message

logger = logging.getLogger(__name__)

# Create router for messages
message_router = Router(name="messages")


@message_router.message(F.text)
async def handle_text_message(message: Message) -> None:
    """Handle text messages."""
    logger.info(f"Received text message: {message.text[:50]}...")
    
    # TODO: Implement task parsing with OpenAI
    # TODO: Create task in Todoist
    
    await message.answer(
        " >;CG8; 20H5 A>>1I5=85!\n\n"
        "=§ $C=:F8O A>740=8O 7040G ?>:0 2 @07@01>B:5.\n"
        f"0H B5:AB: {message.text}"
    )


@message_router.message(F.voice)
async def handle_voice_message(message: Message) -> None:
    """Handle voice messages."""
    logger.info(f"Received voice message, duration: {message.voice.duration}s")
    
    # TODO: Download voice file
    # TODO: Transcribe with Deepgram/Whisper
    # TODO: Parse task with OpenAI
    # TODO: Create task in Todoist
    
    await message.answer(
        "<¤ >;CG8; 3>;>A>2>5 A>>1I5=85!\n\n"
        "=§ $C=:F8O @0A?>7=020=8O @5G8 ?>:0 2 @07@01>B:5.\n"
        f";8B5;L=>ABL: {message.voice.duration} A5:"
    )


@message_router.message(F.video_note | F.video)
async def handle_video_message(message: Message) -> None:
    """Handle video and video note messages."""
    if message.video_note:
        logger.info(f"Received video note, duration: {message.video_note.duration}s")
        duration = message.video_note.duration
    else:
        logger.info(f"Received video, duration: {message.video.duration}s")
        duration = message.video.duration
    
    # TODO: Download video file
    # TODO: Extract audio
    # TODO: Transcribe with Deepgram/Whisper
    # TODO: Parse task with OpenAI
    # TODO: Create task in Todoist
    
    await message.answer(
        "=ù >;CG8; 2845> A>>1I5=85!\n\n"
        "=§ $C=:F8O @0A?>7=020=8O @5G8 87 2845> ?>:0 2 @07@01>B:5.\n"
        f";8B5;L=>ABL: {duration} A5:"
    )


@message_router.message(F.audio)
async def handle_audio_message(message: Message) -> None:
    """Handle audio file messages."""
    logger.info(f"Received audio file: {message.audio.file_name}")
    
    # TODO: Download audio file
    # TODO: Transcribe with Deepgram/Whisper
    # TODO: Parse task with OpenAI
    # TODO: Create task in Todoist
    
    await message.answer(
        "<µ >;CG8; 0C48> D09;!\n\n"
        "=§ $C=:F8O @0A?>7=020=8O 0C48> ?>:0 2 @07@01>B:5.\n"
        f"$09;: {message.audio.file_name}"
    )


@message_router.message()
async def handle_unsupported_message(message: Message) -> None:
    """Handle all other message types."""
    logger.warning(f"Received unsupported message type: {message.content_type}")
    
    await message.answer(
        "L 728=8B5, O ?>:0 =5 C<5N >1@010BK20BL B0:>9 B8? A>>1I5=89.\n\n"
        "/ ?>=8<0N:\n"
        "" "5:AB>2K5 A>>1I5=8O\n"
        "" >;>A>2K5 A>>1I5=8O\n"
        "" 845> A>>1I5=8O\n"
        "" C48> D09;K"
    )