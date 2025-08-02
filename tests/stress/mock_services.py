"""Realistic mock implementations of external services for stress testing."""

import asyncio
import random
import time
from datetime import datetime
from typing import Optional
from unittest.mock import AsyncMock, Mock

from src.core.exceptions import OpenAIError, RateLimitError, TodoistError, TranscriptionError
from src.models.intent import CommandExecution, Intent, TaskCreation
from src.models.task import TaskSchema


class RealisticOpenAIMock:
    """Realistic mock of OpenAI service with delays and rate limiting."""
    
    def __init__(self, failure_rate: float = 0.02, rate_limit_threshold: int = 100):
        """Initialize mock with configurable failure rate."""
        self.failure_rate = failure_rate
        self.rate_limit_threshold = rate_limit_threshold
        self.request_count = 0
        self.request_times: list[float] = []
        
    async def parse_intent(self, text: str, user_language: str = "ru", forward_author: Optional[str] = None) -> Intent:
        """Mock intent parsing with realistic delays."""
        # Track requests for rate limiting
        now = time.time()
        self.request_times = [t for t in self.request_times if now - t < 60]  # Keep last minute
        self.request_times.append(now)
        self.request_count += 1
        
        # Check rate limit
        if len(self.request_times) > self.rate_limit_threshold:
            await asyncio.sleep(random.uniform(0.5, 1.0))
            raise RateLimitError("OpenAI rate limit exceeded")
            
        # Simulate API delay (100-300ms)
        delay = random.uniform(0.1, 0.3)
        await asyncio.sleep(delay)
        
        # Random failures
        if random.random() < self.failure_rate:
            if random.random() < 0.5:
                raise OpenAIError("OpenAI API error: Internal server error")
            else:
                raise RateLimitError("Rate limit exceeded")
                
        # Parse intent based on text patterns
        text_lower = text.lower()
        
        # Check if it's a command
        if any(word in text_lower for word in ["покажи", "показать", "удали", "удалить", "выполни", "выполнить"]):
            # Return a command execution intent
            command_type = "view_tasks"
            if "удали" in text_lower:
                command_type = "delete_task"
            elif "выполни" in text_lower:
                command_type = "complete_task"
                
            return CommandExecution(
                type="command",
                command_type=command_type,
                target="last"
            )
            
        # Default to task creation
        project = "Inbox"
        if "работ" in text_lower:
            project = "Работа"
        elif "дом" in text_lower or "личн" in text_lower:
            project = "Личное"
            
        # Extract due date patterns
        due_string = None
        if "завтра" in text_lower:
            due_string = "tomorrow"
        elif "сегодня" in text_lower:
            due_string = "today"
        elif "понедельник" in text_lower:
            due_string = "monday"
        elif "вечер" in text_lower:
            due_string = "today 18:00"
            
        # Generate labels
        labels = []
        if "важн" in text_lower or "срочн" in text_lower:
            labels.append("важное")
        if "встреч" in text_lower:
            labels.append("встречи")
        if "звон" in text_lower or "позвон" in text_lower:
            labels.append("звонки")
            
        # Create task schema
        task_schema = TaskSchema(
            content=text.strip(),
            project_name=project,
            labels=labels,
            priority=4 if "срочн" in text_lower else 1,
            due_string=due_string
        )
        
        # Return task creation intent
        return TaskCreation(
            type="create_task",
            task=task_schema
        )


class RealisticDeepgramMock:
    """Realistic mock of Deepgram service with delays."""
    
    def __init__(self, failure_rate: float = 0.01):
        """Initialize mock."""
        self.failure_rate = failure_rate
        self.transcriptions = [
            "Позвонить маме вечером",
            "Купить молоко и хлеб завтра",
            "Встреча с клиентом в понедельник в 15:00",
            "Записаться к врачу на следующей неделе",
            "Оплатить счета до конца месяца",
            "Подготовить презентацию к пятнице",
            "Забрать документы из офиса"
        ]
        
    async def transcribe(self, audio_data: bytes, mime_type: str) -> str:
        """Mock audio transcription with realistic delays."""
        # Simulate transcription delay based on audio "duration"
        # Assume 1KB ≈ 0.1s of audio, transcription takes 0.1-0.2x real-time
        audio_duration = len(audio_data) / 10000  # Rough estimate
        processing_time = audio_duration * random.uniform(0.1, 0.2)
        processing_time = max(0.2, min(processing_time, 2.0))  # Clamp between 0.2-2s
        
        await asyncio.sleep(processing_time)
        
        # Random failures
        if random.random() < self.failure_rate:
            raise TranscriptionError("Deepgram transcription failed")
            
        # Return random transcription
        return random.choice(self.transcriptions)


class RealisticTodoistMock:
    """Realistic mock of Todoist service with rate limiting."""
    
    def __init__(self, failure_rate: float = 0.01):
        """Initialize mock."""
        self.failure_rate = failure_rate
        self.request_times: list[float] = []
        self.task_counter = 1000
        self.projects = {
            "Inbox": "123456",
            "Работа": "234567",
            "Личное": "345678"
        }
        self.rate_limit = 450  # 450 requests per 15 minutes
        
    async def _check_rate_limit(self):
        """Check Todoist rate limit (450 req/15 min)."""
        now = time.time()
        # Keep requests from last 15 minutes
        self.request_times = [t for t in self.request_times if now - t < 900]
        
        if len(self.request_times) >= self.rate_limit:
            raise RateLimitError("Todoist API rate limit exceeded")
            
        self.request_times.append(now)
        
    async def create_task(
        self,
        content: str,
        project_id: Optional[str] = None,
        labels: Optional[list[str]] = None,
        priority: int = 1,
        due_string: Optional[str] = None,
        due_date: Optional[str] = None
    ) -> Mock:
        """Mock task creation with realistic delays."""
        await self._check_rate_limit()
        
        # Simulate API delay (50-150ms)
        await asyncio.sleep(random.uniform(0.05, 0.15))
        
        # Random failures
        if random.random() < self.failure_rate:
            raise TodoistError("Failed to create task")
            
        self.task_counter += 1
        
        # Create mock task
        task = Mock()
        task.id = str(self.task_counter)
        task.content = content
        task.project_id = project_id or self.projects["Inbox"]
        task.labels = labels or []
        task.priority = priority
        task.due = Mock(string=due_string) if due_string else None
        task.created_at = datetime.now().isoformat()
        
        return task
        
    async def get_projects(self) -> list[Mock]:
        """Mock getting projects."""
        await self._check_rate_limit()
        await asyncio.sleep(random.uniform(0.05, 0.1))
        
        projects = []
        for name, pid in self.projects.items():
            project = Mock()
            project.name = name
            project.id = pid
            projects.append(project)
            
        return projects
        
    async def complete_task(self, task_id: str) -> bool:
        """Mock task completion."""
        await self._check_rate_limit()
        await asyncio.sleep(random.uniform(0.05, 0.1))
        
        if random.random() < self.failure_rate:
            raise TodoistError("Failed to complete task")
            
        return True
        
    async def delete_task(self, task_id: str) -> bool:
        """Mock task deletion."""
        await self._check_rate_limit()
        await asyncio.sleep(random.uniform(0.05, 0.1))
        
        if random.random() < self.failure_rate:
            raise TodoistError("Failed to delete task")
            
        return True
        
    async def get_tasks(self, filter: Optional[str] = None) -> list[Mock]:
        """Mock getting tasks."""
        await self._check_rate_limit()
        await asyncio.sleep(random.uniform(0.1, 0.2))
        
        # Return some mock tasks
        tasks = []
        for i in range(5):
            task = Mock()
            task.id = str(self.task_counter - i)
            task.content = f"Task {i+1}"
            task.created_at = datetime.now().isoformat()
            tasks.append(task)
            
        return tasks


class MockBotWithMetrics:
    """Mock bot that tracks all method calls for metrics."""
    
    def __init__(self):
        """Initialize mock bot."""
        self.metrics = {
            "send_message": 0,
            "answer": 0,
            "edit_message_text": 0,
            "answer_callback_query": 0,
            "delete_message": 0,
            "get_file": 0,
            "download_file": 0,
            "send_chat_action": 0
        }
        self.errors = []
        
        # Bot attributes required by aiogram
        self.id = 123456789  # Bot ID
        
        # Create async mocks
        self.send_message = self._create_tracked_mock("send_message")
        self.answer = self._create_tracked_mock("answer")
        self.edit_message_text = self._create_tracked_mock("edit_message_text")
        self.answer_callback_query = self._create_tracked_mock("answer_callback_query")
        self.delete_message = self._create_tracked_mock("delete_message")
        self.get_file = self._create_tracked_mock("get_file", return_value=Mock(file_path="fake_path"))
        self.download_file = self._create_tracked_mock("download_file", return_value=b"fake audio data")
        self.send_chat_action = self._create_tracked_mock("send_chat_action", return_value=True)
        
        # Bot info
        self.get_me = AsyncMock(return_value=Mock(id=self.id, username="test_bot", first_name="Test Bot"))
    
    async def __call__(self, method, request_timeout=None):
        """Handle method calls from aiogram."""
        # Get method name from the method object
        method_name = method.__api_method__ if hasattr(method, '__api_method__') else type(method).__name__
        
        # Track the call
        if method_name.lower() in self.metrics:
            self.metrics[method_name.lower()] += 1
        else:
            # Track under general category
            self.metrics["send_message"] += 1
        
        # Add small delay to simulate network
        await asyncio.sleep(random.uniform(0.01, 0.03))
        
        # Return appropriate mock response based on method type
        if method_name == "SendMessage" or method_name == "sendMessage":
            return Mock(
                message_id=random.randint(1000, 9999),
                date=datetime.now(),
                chat=Mock(id=method.chat_id if hasattr(method, 'chat_id') else 123),
                text=method.text if hasattr(method, 'text') else "test"
            )
        elif method_name == "EditMessageText" or method_name == "editMessageText":
            return Mock(
                message_id=method.message_id if hasattr(method, 'message_id') else random.randint(1000, 9999),
                date=datetime.now(),
                edited=True
            )
        elif method_name == "AnswerCallbackQuery" or method_name == "answerCallbackQuery":
            return True
        elif method_name == "DeleteMessage" or method_name == "deleteMessage":
            return True
        elif method_name == "GetFile" or method_name == "getFile":
            return Mock(file_path="fake_path", file_id="fake_id")
        elif method_name == "SendChatAction" or method_name == "sendChatAction":
            return True
        else:
            # Generic response
            return Mock()
        
    def _create_tracked_mock(self, method_name: str, **kwargs):
        """Create a mock that tracks calls."""
        async def tracked_method(*args, **kw):
            self.metrics[method_name] += 1
            # Add small delay to simulate network
            await asyncio.sleep(random.uniform(0.01, 0.03))
            if "return_value" in kwargs:
                return kwargs["return_value"]
            return Mock()
            
        return tracked_method
        
    def get_metrics_summary(self) -> dict:
        """Get summary of all bot method calls."""
        total_calls = sum(self.metrics.values())
        return {
            "total_calls": total_calls,
            "methods": self.metrics.copy(),
            "errors": len(self.errors)
        }