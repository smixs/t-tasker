"""Custom exceptions for the bot application."""



class BotError(Exception):
    """Base exception for all bot errors."""

    def __init__(self, message: str, user_message: str | None = None) -> None:
        """Initialize bot error.

        Args:
            message: Internal error message for logging
            user_message: User-friendly message to display
        """
        super().__init__(message)
        self.user_message = user_message or "Произошла ошибка. Попробуйте позже."


class OpenAIError(BotError):
    """Error from OpenAI API."""

    def __init__(self, message: str) -> None:
        super().__init__(
            message,
            user_message="Не удалось обработать ваше сообщение. Попробуйте переформулировать."
        )


class TranscriptionError(BotError):
    """Error during audio/video transcription."""

    def __init__(self, message: str) -> None:
        super().__init__(
            message,
            user_message="Не удалось распознать голосовое сообщение. Попробуйте записать еще раз."
        )


class TodoistError(BotError):
    """Error from Todoist API."""

    def __init__(self, message: str) -> None:
        super().__init__(
            message,
            user_message="Не удалось создать задачу в Todoist. Проверьте настройки интеграции."
        )


class RateLimitError(BotError):
    """Rate limit exceeded error."""

    def __init__(self, retry_after: int | None = None) -> None:
        message = "Rate limit exceeded"
        if retry_after:
            user_message = f"Слишком много запросов. Попробуйте через {retry_after} секунд."
        else:
            user_message = "Слишком много запросов. Попробуйте через несколько минут."

        super().__init__(message, user_message)
        self.retry_after = retry_after


class ValidationError(BotError):
    """Validation error for user input."""

    def __init__(self, message: str, field: str | None = None) -> None:
        user_message = f"Неверное значение поля {field}" if field else "Неверный формат данных"
        super().__init__(message, user_message)
        self.field = field


class UnauthorizedError(BotError):
    """User is not authorized to perform action."""

    def __init__(self, message: str = "User not authorized") -> None:
        super().__init__(
            message,
            user_message="Сначала настройте интеграцию с Todoist через команду /setup"
        )


class QuotaExceededError(TodoistError):
    """Todoist quota exceeded error."""

    def __init__(self) -> None:
        super().__init__("Todoist API quota exceeded")
        self.user_message = "Превышен лимит запросов к Todoist. Попробуйте позже."


class InvalidTokenError(TodoistError):
    """Invalid Todoist token error."""

    def __init__(self) -> None:
        super().__init__("Invalid Todoist token")
        self.user_message = "Неверный токен Todoist. Используйте /setup для обновления."
