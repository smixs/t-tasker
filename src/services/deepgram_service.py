"""Deepgram transcription service for voice messages."""

import logging
from typing import Optional

import httpx

from src.core.exceptions import TranscriptionError
from src.core.settings import get_settings

logger = logging.getLogger(__name__)


class DeepgramService:
    """Service for transcribing audio using Deepgram API."""

    def __init__(self) -> None:
        """Initialize Deepgram service."""
        self.settings = get_settings()
        self.api_key = self.settings.deepgram_api_key
        self.base_url = "https://api.deepgram.com/v1"
        self.timeout = self.settings.deepgram_timeout

    async def transcribe(self, audio_bytes: bytes, mime_type: str = "audio/ogg") -> str:
        """Transcribe audio bytes to text.

        Args:
            audio_bytes: Audio file content
            mime_type: MIME type of the audio file

        Returns:
            Transcribed text

        Raises:
            TranscriptionError: If transcription fails
        """
        headers = {
            "Authorization": f"Token {self.api_key}",
            "Content-Type": mime_type,
        }

        params = {
            "model": "nova-3",  # nova-3 - latest model with auto language detection
            "punctuate": True,
            "smart_format": True,
            # NOT specifying language - let Deepgram auto-detect!
        }

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    f"{self.base_url}/listen",
                    headers=headers,
                    content=audio_bytes,
                    params=params,
                )

                if response.status_code != 200:
                    error_text = response.text
                    logger.error(f"Deepgram API error: {response.status_code} - {error_text}")
                    raise TranscriptionError(f"Deepgram API error: {response.status_code}")

                result = response.json()
                
                # Extract transcript from response
                transcript = self._extract_transcript(result)
                
                if not transcript:
                    logger.warning("Empty transcript received from Deepgram")
                    raise TranscriptionError("Empty transcript")

                logger.info(f"Successfully transcribed audio, length: {len(transcript)} chars")
                return transcript

        except httpx.TimeoutException:
            logger.error("Deepgram API timeout")
            raise TranscriptionError("Deepgram timeout")
        except httpx.RequestError as e:
            logger.error(f"Deepgram request error: {e}")
            raise TranscriptionError(f"Request error: {str(e)}")
        except Exception as e:
            logger.error(f"Unexpected error in Deepgram transcription: {e}")
            raise TranscriptionError(f"Unexpected error: {str(e)}")

    def _extract_transcript(self, result: dict) -> Optional[str]:
        """Extract transcript text from Deepgram response.

        Args:
            result: Deepgram API response

        Returns:
            Transcript text or None
        """
        try:
            channels = result.get("results", {}).get("channels", [])
            if not channels:
                return None

            alternatives = channels[0].get("alternatives", [])
            if not alternatives:
                return None

            transcript = alternatives[0].get("transcript", "").strip()
            return transcript if transcript else None

        except (KeyError, IndexError, TypeError) as e:
            logger.error(f"Failed to extract transcript from response: {e}")
            return None