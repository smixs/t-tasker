"""OpenAI service for task parsing using Instructor."""

import logging

import instructor
from better_profanity import profanity
from openai import AsyncOpenAI
from openai.types.chat import ChatCompletionMessageParam
from tenacity import retry, stop_after_attempt, wait_exponential

from src.core.exceptions import OpenAIError, ValidationError
from src.core.settings import Settings, get_settings
from src.models.intent import Intent, IntentWrapper, TaskCreation
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
        self.client = AsyncOpenAI(api_key=self.settings.openai_key, timeout=self.settings.openai_timeout)

        # Apply instructor patch for structured outputs
        self.instructor_client = instructor.patch(self.client, mode=instructor.Mode.TOOLS)

        logger.info("OpenAI service initialized")

    def _filter_profanity(self, text: str) -> str:
        """Filter profanity from text.

        Args:
            text: Input text

        Returns:
            Censored text
        """
        return profanity.censor(text)

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10), reraise=True)
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

ПРИОРИТЕТ ИЗВЛЕЧЕНИЯ ДАТ:
1. Абсолютные даты и время (15 марта, 20.03.2025, в 14:00) - ВСЕГДА приоритет
2. Относительные даты (завтра, послезавтра) - только если НЕТ абсолютных
3. При наличии и абсолютной и относительной даты - ИГНОРИРОВАТЬ относительную

Правила извлечения:
1. content - основной текст задачи (обязательно)
2. description - дополнительное описание (если есть)  
3. due_string - КОНВЕРТИРОВАТЬ В АНГЛИЙСКИЙ ФОРМАТ:
   - Дни недели: "понедельник"→"monday", "вторник"→"tuesday", "среда"→"wednesday", "четверг"→"thursday", "пятница"→"friday", "суббота"→"saturday", "воскресенье"→"sunday"
   - Месяцы: "января"→"jan", "февраля"→"feb", "марта"→"mar", "апреля"→"apr", "мая"→"may", "июня"→"jun", "июля"→"jul", "августа"→"aug", "сентября"→"sep", "октября"→"oct", "ноября"→"nov", "декабря"→"dec"
   - Относительные: "сегодня"→"today", "завтра"→"tomorrow", "послезавтра"→"day after tomorrow"
   - Время: "в 14:00"→"at 14:00", "в 9:30"→"at 9:30"
   - Примеры: "15 марта"→"mar 15", "четверг в 12:00"→"thursday at 12:00", "завтра в 15:00"→"tomorrow at 15:00"
   ВАЖНО: УДАЛЯТЬ любые указания места/тайм-зоны:
   - "по Минску", "по Ташкенту", "по Москве" → удалить
   - "четверг в 12:00 по Минску" → "thursday at 12:00"
   - "завтра в 15:00 по Ташкенту" → "tomorrow at 15:00"
4. priority - приоритет: 1 (обычный), 2 (средний), 3 (высокий), 4 (срочный)
5. project_name - название проекта (если указано)
6. labels - метки/теги (если есть)
7. recurrence - повторение (каждый день, каждую неделю)
8. duration - длительность в минутах (если указано)

ПРИМЕРЫ ПРАВИЛЬНОГО ИЗВЛЕЧЕНИЯ:
- "Встреча завтра 15 марта в 14:00" → due_string: "mar 15 at 14:00" (НЕ "tomorrow")
- "Позвонить клиенту послезавтра 20.03 в 10:00" → due_string: "mar 20 at 10:00"
- "Сделать отчет завтра" → due_string: "tomorrow" (нет абсолютной даты)
- "Встреча в офисе 25 марта" → due_string: "mar 25"
- "В четверг в 12:00 по Минску встреча" → due_string: "thursday at 12:00" (БЕЗ "по Минску")
"""
        else:
            system_prompt = """
You are an assistant for creating tasks in Todoist. Extract task information from the user's message.

DATE EXTRACTION PRIORITY:
1. Absolute dates and times (March 15, 03/20/2025, at 2:00 PM) - ALWAYS priority
2. Relative dates (tomorrow, day after tomorrow) - only if NO absolute dates exist
3. When both absolute and relative dates are present - IGNORE relative

Extraction rules:
1. content - main task text (required)
2. description - additional description (if any)
3. due_string - SEARCH IN THIS ORDER:
   - Specific date: "March 15", "03/20", "03/20/2025"
   - Specific time: "at 2:00 PM", "at 9:30 AM"
   - Combination: "March 15 at 2:00 PM", "03/20/2025 at 4:30 PM"
   - Relative date ONLY if no specific date: "tomorrow", "day after tomorrow"
4. priority - priority: 1 (normal), 2 (medium), 3 (high), 4 (urgent)
5. project_name - project name (if specified)
6. labels - tags/labels (if any)
7. recurrence - recurrence pattern (every day, every week)
8. duration - duration in minutes (if specified)

CORRECT EXTRACTION EXAMPLES:
- "Meeting tomorrow March 15 at 2:00 PM" → due_string: "March 15 at 2:00 PM" (NOT "tomorrow")
- "Call client day after tomorrow 03/20 at 10:00 AM" → due_string: "03/20 at 10:00 AM"
- "Complete report tomorrow" → due_string: "tomorrow" (no absolute date)
- "Office meeting March 25" → due_string: "March 25"
"""

        try:
            # Create messages
            messages: list[ChatCompletionMessageParam] = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": filtered_message},
            ]

            # Use instructor to get structured output
            response: TaskSchema = await self.instructor_client.chat.completions.create(
                model=self.settings.openai_model,
                messages=messages,
                response_model=TaskSchema,
                max_retries=self.settings.openai_max_retries,
                temperature=0.3,
            )

            logger.info(f"Successfully parsed task: {response.content}")
            return response

        except Exception as e:
            logger.error(f"Failed to parse task: {e}")
            raise OpenAIError(f"Failed to parse task: {str(e)}") from e

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10), reraise=True)
    async def parse_intent(self, message: str, user_language: str = "ru", forward_author: str | None = None) -> Intent:
        """Parse user intent from message - either create task or execute command.

        Args:
            message: User message
            user_language: User language code
            forward_author: Name of the person who forwarded the message (if applicable)

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
            base_prompt = """
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

            # Add forward author context if provided
            if forward_author:
                system_prompt = base_prompt + f"""

ВАЖНО: ПЕРЕСЛАННОЕ СООБЩЕНИЕ!
Это сообщение переслано от другого человека: {forward_author}

При создании задачи из ПЕРЕСЛАННОГО сообщения:
- Это сообщение/просьба/задание исходит ОТ {forward_author} (не от текущего пользователя!)
- ОБЯЗАТЕЛЬНО включи имя {forward_author} в текст задачи, чтобы было понятно, от кого это
- НЕ создавай задачу от имени пользователя - укажи реального автора {forward_author}

Примеры правильной обработки ПЕРЕСЛАННЫХ сообщений:
  * "Встреча завтра" от Ивана → content: "Встреча с Иваном завтра"
  * "Нужен отчет" от начальника → content: "Отчет для начальника"
  * "Созвон в 15:00" от Анны → content: "Созвон с Анной в 15:00"
  * "Сергей, надо работу" от Виолетты → content: "Работа от Виолетты для Сергея"
  
Помни: обычные сообщения (не пересланные) обрабатываются как есть, без добавления автора!
"""
            else:
                system_prompt = base_prompt
        else:
            base_prompt = """
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

            # Add forward author context if provided
            if forward_author:
                system_prompt = base_prompt + f"""

IMPORTANT: FORWARDED MESSAGE!
This message is forwarded from another person: {forward_author}

When creating a task from a FORWARDED message:
- This message/request/task originates FROM {forward_author} (not from the current user!)
- ALWAYS include {forward_author}'s name in the task text to clarify who it's from
- DO NOT create the task as if from the user - indicate the real author {forward_author}

Examples of correct FORWARDED message processing:
  * "Meeting tomorrow" from Ivan → content: "Meeting with Ivan tomorrow"
  * "Need report" from manager → content: "Report for manager"
  * "Call at 3:00 PM" from Anna → content: "Call with Anna at 3:00 PM"
  * "John, need work done" from Violet → content: "Work from Violet for John"
  
Remember: regular messages (not forwarded) are processed as-is, without adding any author!
"""
            else:
                system_prompt = base_prompt

        try:
            # Create messages
            messages: list[ChatCompletionMessageParam] = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": filtered_message},
            ]

            # Use instructor to get structured output
            wrapper: IntentWrapper = await self.instructor_client.chat.completions.create(
                model=self.settings.openai_model,
                messages=messages,
                response_model=IntentWrapper,
                max_retries=self.settings.openai_max_retries,
                temperature=0.2,  # Lower temperature for more consistent classification
            )

            # Convert wrapper to proper intent type
            intent = wrapper.to_intent()

            # Log the classification result
            intent_type = "task_creation" if isinstance(intent, TaskCreation) else "command"
            logger.info(f"Classified intent as: {intent_type}")

            return intent

        except Exception as e:
            logger.error(f"Failed to parse intent: {e}")
            raise OpenAIError(f"Failed to parse intent: {str(e)}") from e

    async def parse_date_only(self, text: str, user_language: str = "ru") -> str:
        """Parse only date from text without intent classification.

        Used for editing tasks where we need to convert user input to Todoist date format.

        Args:
            text: User input text
            user_language: User language code

        Returns:
            Parsed date string for Todoist API
        """
        system_prompt = """
You are a date parser assistant. Your task is to convert user text to Todoist date format.

Rules for Russian month names:
- "января" → "jan"
- "февраля" → "feb"
- "марта" → "mar"
- "апреля" → "apr"
- "мая" → "may"
- "июня" → "jun"
- "июля" → "jul"
- "августа" → "aug"
- "сентября" → "sep"
- "октября" → "oct"
- "ноября" → "nov"
- "декабря" → "dec"

General rules:
- "сегодня" → "today"
- "завтра" → "tomorrow"  
- "послезавтра" → "day after tomorrow"
- "понедельник", "вторник" etc → "monday", "tuesday" etc
- "через 3 дня" → "in 3 days"
- "через неделю" → "in 1 week"
- "22 июля" → "jul 22"
- "1 января" → "jan 1"
- "15 марта" → "mar 15"
- "в 14:00" → "at 14:00"
- "завтра в 15:00" → "tomorrow at 15:00"

IMPORTANT: Remove any timezone/location references:
- "в 12:00 по Минску" → "at 12:00"
- "15:00 по Ташкенту" → "at 15:00"
- "завтра в 10:00 по Москве" → "tomorrow at 10:00"

If you cannot parse the date, return the original text unchanged

Respond ONLY with the date string, no explanations.
"""

        try:
            response = await self.client.chat.completions.create(
                model=self.settings.openai_model,
                messages=[{"role": "system", "content": system_prompt}, {"role": "user", "content": text}],
                temperature=0.1,
                max_tokens=50,
            )

            content = response.choices[0].message.content
            if content is None:
                logger.warning("OpenAI returned None content for date parsing")
                return text
            parsed_date = content.strip()
            logger.info(f"Parsed date '{text}' to '{parsed_date}'")
            return parsed_date

        except Exception as e:
            logger.error(f"Failed to parse date: {e}")
            # Fallback to original text
            return text

    async def close(self) -> None:
        """Close OpenAI client."""
        await self.client.close()
        logger.info("OpenAI service closed")
