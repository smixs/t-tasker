"""Custom exceptions for the application."""


class TaskerBotError(Exception):
    """Base exception for all bot errors."""
    pass


class TranscriptionError(TaskerBotError):
    """Error during audio/video transcription."""
    pass


class OpenAIError(TaskerBotError):
    """Error when calling OpenAI API."""
    pass


class TodoistError(TaskerBotError):
    """Error when calling Todoist API."""
    pass


class RateLimitError(TaskerBotError):
    """Rate limit exceeded error."""
    pass


class AuthenticationError(TaskerBotError):
    """Authentication/authorization error."""
    pass


class ValidationError(TaskerBotError):
    """Input validation error."""
    pass