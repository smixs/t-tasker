"""OpenAI service for task parsing using Instructor."""

import logging
from pathlib import Path

import dspy
import instructor
from better_profanity import profanity
from openai import AsyncOpenAI
from openai.types.chat import ChatCompletionMessageParam
from tenacity import retry, stop_after_attempt, wait_exponential

from src.core.exceptions import OpenAIError, ValidationError
from src.core.settings import Settings, get_settings
from src.models.intent import CommandExecution, Intent, IntentWrapper, TaskCreation
from src.models.task import TaskSchema
from src.services.dspy_parser import RealWorldTodoistParser, is_complex_message

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
        self.client = AsyncOpenAI(api_key=self.settings.openai_api_key.get_secret_value(), timeout=self.settings.openai_timeout)

        # Apply instructor patch for structured outputs
        self.instructor_client = instructor.patch(self.client, mode=instructor.Mode.TOOLS)
        
        # Initialize DSPy parser if enabled
        self.dspy_parser = None
        if self.settings.use_dspy_parser:
            try:
                # Configure DSPy
                dspy.configure(lm=dspy.LM(
                    f"openai/{self.settings.openai_model}",
                    api_key=self.settings.openai_api_key.get_secret_value()
                ))
                
                # Load optimized parser
                model_path = Path(self.settings.dspy_parser_model_path)
                if model_path.exists():
                    self.dspy_parser = RealWorldTodoistParser()
                    self.dspy_parser.load(str(model_path))
                    logger.info(f"DSPy parser loaded from {model_path}")
                else:
                    logger.warning(f"DSPy model not found at {model_path}, using legacy parser")
                    self.settings.use_dspy_parser = False
            except Exception as e:
                logger.error(f"Failed to initialize DSPy parser: {e}")
                self.settings.use_dspy_parser = False

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
        
        # Decide whether to use DSPy parser
        use_dspy = self.settings.use_dspy_parser and self.dspy_parser is not None
        
        # For complex messages, always use DSPy if available
        if use_dspy and is_complex_message(filtered_message):
            return await self._parse_task_dspy(filtered_message, user_language)
        
        # For simple messages or when DSPy is disabled, use legacy
        return await self._parse_task_legacy(filtered_message, user_language)
    
    async def _parse_task_dspy(self, message: str, user_language: str = "ru") -> TaskSchema:
        """Parse task using DSPy parser."""
        try:
            # Use DSPy parser
            task_schema = self.dspy_parser.parse_task(
                message=message,
                user_language=user_language
            )
            
            logger.info(f"Successfully parsed task with DSPy: {task_schema.content}")
            logger.info(f"DSPy parser added tags: {task_schema.labels}")
            
            return task_schema
            
        except Exception as e:
            logger.error(f"DSPy parsing failed: {e}")
            # Fallback to legacy method
            return await self._parse_task_legacy(message, user_language)
    
    async def _parse_task_legacy(self, message: str, user_language: str = "ru") -> TaskSchema:
        """Parse task using legacy prompt-based method."""

        # Prepare system prompt based on language
        if user_language == "ru":
            system_prompt = """
Ты - помощник для создания задач в Todoist. Обработай входящее сообщение пользователя для извлечения ключевых компонентов задачи, включая краткое содержание задачи, подробное описание, дату выполнения, соответствующие сущности и тип действия. Обеспечь ясность и краткость в выводе.

ПРИОРИТЕТ ИЗВЛЕЧЕНИЯ ДАТ:
1. Абсолютные даты и время (15 марта, 20.03.2025, в 14:00) - ВСЕГДА приоритет
2. Относительные даты (завтра, послезавтра) - только если НЕТ абсолютных
3. При наличии и абсолютной и относительной даты - ИГНОРИРОВАТЬ относительную

Правила извлечения:
1. content - КРАТКАЯ СУТЬ задачи (максимум 100 символов). Сократи длинные сообщения до главной сути действия
2. description - ПОЛНЫЙ КОНТЕКСТ, включая все детали, списки, имена - сохрани как есть
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
6. labels - умные теги на основе контекста:
   - Извлеки имена людей, компании, проекты как теги
   - Добавь тип действия: встреча, звонок, документ, решение, проверка
   - Для финансовых тем: кредит, бюджет, финансы
   - Максимум 5 тегов
7. recurrence - повторение (каждый день, каждую неделю)
8. duration - длительность в минутах (если указано)

ПРИМЕРЫ ПРАВИЛЬНОГО ИЗВЛЕЧЕНИЯ:

Пример 1:
Сообщение: "Звонила Островской из IBT. Новости подтвердились. Она в сентябре уходит и будет новый директор. Обещала поделиться контактами, чтобы мы могли встретиться"
content: "Встретиться с новым директором IBT"
description: "Звонила Островской из IBT. Новости подтвердились. Она в сентябре уходит и будет новый директор. Обещала поделиться контактами"
labels: ["встреча", "IBT", "Островская", "контакты"]

Пример 2:
Сообщение: "Не обсудили сегодня статус по открытию юр лица: 1. Проработка драфта документов Нестле-WUNDER. 2. Подписант - Дарья готова. 3. Надо определить учредителей. Дедлайн пятница"
content: "Обсудить статус открытия юрлица"
description: "Не обсудили сегодня статус по открытию юр лица: 1. Проработка драфта документов Нестле-WUNDER. 2. Подписант - Дарья готова. 3. Надо определить учредителей"
due_string: "friday"
labels: ["юрлицо", "документы", "NESTLE", "WUNDER", "срочно"]

Пример 3:
Сообщение: "Позвонить в банк Сбербанк по поводу кредита для компании ООО Ромашка"
content: "Позвонить в Сбербанк по кредиту для ООО Ромашка"
description: "Позвонить в банк Сбербанк по поводу кредита для компании ООО Ромашка"
labels: ["звонок", "Сбербанк", "кредит", "ООО Ромашка", "финансы"]
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
            forward_author: Deprecated parameter, kept for backward compatibility

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
   
   Правила извлечения полей задачи:
   - content: основной текст задачи (обязательно)
   - due_string: дата/время выполнения на английском ("today", "tomorrow", "mar 15 at 14:00")

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

            system_prompt = base_prompt

        try:
            # Log what we're sending to OpenAI
            logger.info(f"Sending to OpenAI - message: '{filtered_message[:100]}...'")
            
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
