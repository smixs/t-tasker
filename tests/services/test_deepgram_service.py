"""Tests for Deepgram transcription service."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

import httpx

from src.core.exceptions import TranscriptionError
from src.services.deepgram_service import DeepgramService


@pytest.fixture
def deepgram_service():
    """Create DeepgramService instance."""
    return DeepgramService()


@pytest.fixture
def mock_successful_response():
    """Mock successful Deepgram API response."""
    return {
        "results": {
            "channels": [
                {
                    "alternatives": [
                        {
                            "transcript": "Создай задачу встреча с клиентом завтра в 15:00",
                            "confidence": 0.98
                        }
                    ]
                }
            ]
        }
    }


@pytest.fixture
def mock_empty_response():
    """Mock empty Deepgram API response."""
    return {
        "results": {
            "channels": [
                {
                    "alternatives": [
                        {
                            "transcript": "",
                            "confidence": 0.0
                        }
                    ]
                }
            ]
        }
    }


@pytest.mark.asyncio
async def test_transcribe_success(deepgram_service, mock_successful_response):
    """Test successful transcription."""
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = mock_successful_response
    
    with patch("httpx.AsyncClient") as mock_client:
        mock_client.return_value.__aenter__.return_value.post = AsyncMock(return_value=mock_response)
        
        result = await deepgram_service.transcribe(b"audio_data")
        
        assert result == "Создай задачу встреча с клиентом завтра в 15:00"
        
        # Verify API call
        mock_client.return_value.__aenter__.return_value.post.assert_called_once()
        call_args = mock_client.return_value.__aenter__.return_value.post.call_args
        
        # Check URL
        assert call_args[0][0] == "https://api.deepgram.com/v1/listen"
        
        # Check headers
        assert "Authorization" in call_args[1]["headers"]
        assert call_args[1]["headers"]["Content-Type"] == "audio/ogg"
        
        # Check params - should NOT include language for auto-detection
        assert "language" not in call_args[1]["params"]
        assert call_args[1]["params"]["model"] == "nova-3"
        assert call_args[1]["params"]["punctuate"] is True
        assert call_args[1]["params"]["smart_format"] is True


@pytest.mark.asyncio
async def test_transcribe_custom_mime_type(deepgram_service, mock_successful_response):
    """Test transcription with custom MIME type."""
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = mock_successful_response
    
    with patch("httpx.AsyncClient") as mock_client:
        mock_client.return_value.__aenter__.return_value.post = AsyncMock(return_value=mock_response)
        
        await deepgram_service.transcribe(b"audio_data", mime_type="audio/mp4")
        
        call_args = mock_client.return_value.__aenter__.return_value.post.call_args
        assert call_args[1]["headers"]["Content-Type"] == "audio/mp4"


@pytest.mark.asyncio
async def test_transcribe_empty_result(deepgram_service, mock_empty_response):
    """Test transcription with empty result."""
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = mock_empty_response
    
    with patch("httpx.AsyncClient") as mock_client:
        mock_client.return_value.__aenter__.return_value.post = AsyncMock(return_value=mock_response)
        
        with pytest.raises(TranscriptionError) as exc_info:
            await deepgram_service.transcribe(b"audio_data")
        
        assert "Empty transcript" in str(exc_info.value)


@pytest.mark.asyncio
async def test_transcribe_api_error(deepgram_service):
    """Test handling of API error responses."""
    mock_response = MagicMock()
    mock_response.status_code = 401
    mock_response.text = "Invalid API key"
    
    with patch("httpx.AsyncClient") as mock_client:
        mock_client.return_value.__aenter__.return_value.post = AsyncMock(return_value=mock_response)
        
        with pytest.raises(TranscriptionError) as exc_info:
            await deepgram_service.transcribe(b"audio_data")
        
        assert "Deepgram API error: 401" in str(exc_info.value)


@pytest.mark.asyncio
async def test_transcribe_timeout(deepgram_service):
    """Test handling of timeout errors."""
    with patch("httpx.AsyncClient") as mock_client:
        mock_client.return_value.__aenter__.return_value.post = AsyncMock(
            side_effect=httpx.TimeoutException("Request timeout")
        )
        
        with pytest.raises(TranscriptionError) as exc_info:
            await deepgram_service.transcribe(b"audio_data")
        
        assert "Deepgram timeout" in str(exc_info.value)


@pytest.mark.asyncio
async def test_transcribe_request_error(deepgram_service):
    """Test handling of request errors."""
    with patch("httpx.AsyncClient") as mock_client:
        mock_client.return_value.__aenter__.return_value.post = AsyncMock(
            side_effect=httpx.RequestError("Connection failed")
        )
        
        with pytest.raises(TranscriptionError) as exc_info:
            await deepgram_service.transcribe(b"audio_data")
        
        assert "Request error" in str(exc_info.value)


@pytest.mark.asyncio
async def test_transcribe_malformed_response(deepgram_service):
    """Test handling of malformed API responses."""
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"unexpected": "format"}
    
    with patch("httpx.AsyncClient") as mock_client:
        mock_client.return_value.__aenter__.return_value.post = AsyncMock(return_value=mock_response)
        
        with pytest.raises(TranscriptionError) as exc_info:
            await deepgram_service.transcribe(b"audio_data")
        
        assert "Empty transcript" in str(exc_info.value)


def test_extract_transcript_valid(deepgram_service, mock_successful_response):
    """Test transcript extraction from valid response."""
    result = deepgram_service._extract_transcript(mock_successful_response)
    assert result == "Создай задачу встреча с клиентом завтра в 15:00"


def test_extract_transcript_empty(deepgram_service):
    """Test transcript extraction from empty response."""
    result = deepgram_service._extract_transcript({})
    assert result is None


def test_extract_transcript_no_channels(deepgram_service):
    """Test transcript extraction when no channels present."""
    response = {"results": {"channels": []}}
    result = deepgram_service._extract_transcript(response)
    assert result is None


def test_extract_transcript_no_alternatives(deepgram_service):
    """Test transcript extraction when no alternatives present."""
    response = {"results": {"channels": [{"alternatives": []}]}}
    result = deepgram_service._extract_transcript(response)
    assert result is None