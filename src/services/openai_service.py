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
from src.models.intent import Intent, TaskCreation, CommandExecution

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

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=4, max=10),
        reraise=True
    )
    async def parse_intent(self, message: str, user_language: str = "ru") -> Intent:
        """Parse user intent from message - either create task or execute command.

        Args:
            message: User message
            user_language: User language code

        Returns:
            Intent object (either TaskCreation or CommandExecution)

        Raises:
            OpenAIError: If parsing fails
            ValidationError: If message is invalid
        """
        # Filter profanity
        filtered_message = self._filter_profanity(message)

        # Check if message is too short
        if len(filtered_message.strip()) < 2:
            raise ValidationError("Message is too short", field="message")

        # Prepare system prompt based on language
        if user_language == "ru":
            system_prompt = """
Ты - интеллектуальный классификатор намерений для Todoist бота. 
Определи, что хочет сделать пользователь: создать новую задачу или выполнить команду с существующими задачами.

ПРАВИЛА КЛАССИФИКАЦИИ:

1. СОЗДАНИЕ ЗАДАЧИ (type: "create_task"):
   - Пользователь описывает что-то, что нужно сделать в будущем
   - Содержит действие/предмет/событие для запоминания
   - Примеры:
     * "Купить молоко завтра"
     * "Встреча с клиентом в 15:00"
     * "Напомни позвонить маме"
     * "Забрать документы из офиса"
     * "Подготовить презентацию к понедельнику"

2. КОМАНДА УПРАВЛЕНИЯ (type: "command"):
   - view_tasks: просмотр существующих задач
     * "Покажи задачи на сегодня"
     * "Что у меня запланировано?"
     * "Какие задачи на завтра?"
     * "Покажи все задачи"
   
   - delete_task: удаление задач
     * "Удали последнюю задачу"
     * "Убери предыдущую"
     * "Удали всё"
   
   - update_task: изменение задач
     * "Измени приоритет последней задачи"
     * "Перенеси на завтра"
     * "Сделай срочной"
   
   - complete_task: завершение задач
     * "Отметь выполненной"
     * "Задача готова"
     * "Выполнено"

ВАЖНО: Если сомневаешься между созданием и командой, выбирай создание задачи.
"""
        else:
            system_prompt = """
You are an intelligent intent classifier for a Todoist bot.
Determine what the user wants to do: create a new task or execute a command on existing tasks.

CLASSIFICATION RULES:

1. TASK CREATION (type: "create_task"):
   - User describes something to be done in the future
   - Contains action/item/event to remember
   - Examples:
     * "Buy milk tomorrow"
     * "Meeting with client at 3pm"
     * "Call mom"
     * "Pick up documents from office"
     * "Prepare presentation for Monday"

2. COMMAND EXECUTION (type: "command"):
   - view_tasks: viewing existing tasks
     * "Show today's tasks"
     * "What's on my schedule?"
     * "List tomorrow's tasks"
     * "Show all tasks"
   
   - delete_task: deleting tasks
     * "Delete the last task"
     * "Remove the previous one"
     * "Delete everything"
   
   - update_task: modifying tasks
     * "Change priority of last task"
     * "Move to tomorrow"
     * "Make it urgent"
   
   - complete_task: completing tasks
     * "Mark as done"
     * "Task completed"
     * "Done"

IMPORTANT: When in doubt between creation and command, choose task creation.
"""

        try:
            # Create messages
            messages: list[ChatCompletionMessageParam] = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": filtered_message}
            ]

            # Use instructor to get structured output
            response: Intent = await self.instructor_client.chat.completions.create(
                model=self.settings.openai_model,
                messages=messages,
                response_model=Intent,  # Union type - Instructor will handle discrimination
                max_retries=self.settings.openai_max_retries,
                temperature=0.2  # Lower temperature for more consistent classification
            )

            # Log the classification result
            intent_type = "task_creation" if isinstance(response, TaskCreation) else "command"
            logger.info(f"Classified intent as: {intent_type}")
            
            return response

        except Exception as e:
            logger.error(f"Failed to parse intent: {e}")
            raise OpenAIError(f"Failed to parse intent: {str(e)}") from e

    async def close(self) -> None:
        """Close OpenAI client."""
        await self.client.close()
        logger.info("OpenAI service closed")
