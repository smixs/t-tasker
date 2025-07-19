"""OpenAI service for task parsing using Instructor."""

import logging

import instructor
from better_profanity import profanity
from openai import AsyncOpenAI
from openai.types.chat import ChatCompletionMessageParam
from tenacity import retry, stop_after_attempt, wait_exponential

from src.core.exceptions import OpenAIError, ValidationError
from src.core.settings import Settings, get_settings
from src.models.task import TaskSchema

logger = logging.getLogger(__name__)

# Initialize profanity filter
profanity.load_censor_words()


class OpenAIService:
    """Service for interacting with OpenAI API."""

    def __init__(self, settings: Settings | None = None) -> None:
        """Initialize OpenAI service.

        Args:
            settings: Application settings
        """
        self.settings = settings or get_settings()

        # Initialize OpenAI client
        self.client = AsyncOpenAI(
            api_key=self.settings.openai_key,
            timeout=self.settings.openai_timeout
        )

        # Apply instructor patch for structured outputs
        self.instructor_client: instructor.AsyncInstructor = instructor.patch(
            self.client,
            mode=instructor.Mode.TOOLS
        )

        logger.info("OpenAI service initialized")

    def _filter_profanity(self, text: str) -> str:
        """Filter profanity from text.

        Args:
            text: Input text

        Returns:
            Censored text
        """
        return profanity.censor(text)

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=4, max=10),
        reraise=True
    )
    async def parse_task(self, message: str, user_language: str = "ru") -> TaskSchema:
        """Parse task from user message.

        Args:
            message: User message
            user_language: User language code

        Returns:
            Parsed task schema

        Raises:
            OpenAIError: If parsing fails
            ValidationError: If message is invalid
        """
        # Filter profanity
        filtered_message = self._filter_profanity(message)

        # Check if message is too short
        if len(filtered_message.strip()) < 3:
            raise ValidationError("Message is too short", field="message")

        # Prepare system prompt based on language
        if user_language == "ru":
            system_prompt = """
Ты - помощник для создания задач в Todoist. Извлеки информацию о задаче из сообщения пользователя.

Правила:
1. content - основной текст задачи (обязательно)
2. description - дополнительное описание (если есть)
3. due_string - дата/время на русском (завтра, в пятницу, 15 марта в 14:00)
4. priority - приоритет: 1 (обычный), 2 (средний), 3 (высокий), 4 (срочный)
5. project_name - название проекта (если указано)
6. labels - метки/теги (если есть)
7. recurrence - повторение (каждый день, каждую неделю)
8. duration - длительность в минутах (если указано)

Примеры дат: "завтра", "послезавтра", "в понедельник", "через неделю", "15 марта", "в 15:00"
"""
        else:
            system_prompt = """
You are an assistant for creating tasks in Todoist. Extract task information from the user's message.

Rules:
1. content - main task text (required)
2. description - additional description (if any)
3. due_string - date/time in natural language (tomorrow, next Friday, March 15 at 2pm)
4. priority - priority: 1 (normal), 2 (medium), 3 (high), 4 (urgent)
5. project_name - project name (if specified)
6. labels - tags/labels (if any)
7. recurrence - recurrence pattern (every day, every week)
8. duration - duration in minutes (if specified)

Date examples: "tomorrow", "next Monday", "in 2 days", "March 15", "at 3pm"
"""

        try:
            # Create messages
            messages: list[ChatCompletionMessageParam] = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": filtered_message}
            ]

            # Use instructor to get structured output
            response: TaskSchema = await self.instructor_client.chat.completions.create(
                model=self.settings.openai_model,
                messages=messages,
                response_model=TaskSchema,
                max_retries=self.settings.openai_max_retries,
                temperature=0.3
            )

            logger.info(f"Successfully parsed task: {response.content}")
            return response

        except Exception as e:
            logger.error(f"Failed to parse task: {e}")
            raise OpenAIError(f"Failed to parse task: {str(e)}") from e

    async def close(self) -> None:
        """Close OpenAI client."""
        await self.client.close()
        logger.info("OpenAI service closed")
