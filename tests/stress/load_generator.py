"""Load generator for creating realistic user behavior patterns."""

import asyncio
import random
from dataclasses import dataclass
from enum import Enum
from typing import Callable, Optional

from aiogram.types import Message, Update

from .telegram_simulator import TelegramSimulator


class MessageType(Enum):
    """Types of messages to generate."""
    TEXT_TASK = "text_task"
    VOICE_MESSAGE = "voice"
    COMMAND = "command"
    EDIT_MESSAGE = "edit"
    CALLBACK_BUTTON = "callback"


@dataclass
class LoadProfile:
    """Load profile configuration."""
    text_task_percent: float = 0.30
    voice_message_percent: float = 0.20
    command_percent: float = 0.20
    edit_message_percent: float = 0.15
    callback_button_percent: float = 0.15
    
    # Timing parameters
    min_delay_between_messages: float = 0.1
    max_delay_between_messages: float = 2.0
    
    # Burst parameters
    burst_probability: float = 0.1  # 10% chance of burst
    burst_size: int = 5  # Number of messages in burst
    burst_delay: float = 0.05  # Delay between burst messages
    
    def validate(self):
        """Validate that percentages sum to 1.0."""
        total = (
            self.text_task_percent + 
            self.voice_message_percent + 
            self.command_percent + 
            self.edit_message_percent + 
            self.callback_button_percent
        )
        assert abs(total - 1.0) < 0.001, f"Percentages must sum to 1.0, got {total}"


class UserBehavior:
    """Simulates realistic user behavior."""
    
    def __init__(
        self, 
        user_id: int,
        simulator: TelegramSimulator,
        profile: LoadProfile
    ):
        """Initialize user behavior."""
        self.user_id = user_id
        self.simulator = simulator
        self.profile = profile
        self.message_history: list[Message] = []
        self.task_messages: list[Message] = []  # Messages with keyboards
        
    def _choose_message_type(self) -> MessageType:
        """Choose message type based on profile probabilities."""
        rand = random.random()
        
        if rand < self.profile.text_task_percent:
            return MessageType.TEXT_TASK
        elif rand < self.profile.text_task_percent + self.profile.voice_message_percent:
            return MessageType.VOICE_MESSAGE
        elif rand < self.profile.text_task_percent + self.profile.voice_message_percent + self.profile.command_percent:
            return MessageType.COMMAND
        elif rand < 1.0 - self.profile.callback_button_percent:
            return MessageType.EDIT_MESSAGE
        else:
            return MessageType.CALLBACK_BUTTON
            
    async def generate_update(self) -> Optional[Update]:
        """Generate a single update based on user behavior."""
        msg_type = self._choose_message_type()
        
        if msg_type == MessageType.TEXT_TASK:
            return self._create_text_task_update()
        elif msg_type == MessageType.VOICE_MESSAGE:
            return self._create_voice_update()
        elif msg_type == MessageType.COMMAND:
            return self._create_command_update()
        elif msg_type == MessageType.EDIT_MESSAGE:
            return self._create_edit_update()
        elif msg_type == MessageType.CALLBACK_BUTTON:
            return self._create_callback_update()
            
    def _create_text_task_update(self) -> Update:
        """Create a text task update."""
        tasks = self.simulator.get_random_task_texts()
        text = random.choice(tasks)
        
        # Add some variety
        if random.random() < 0.3:
            # Add emoji
            emojis = ["📝", "🔔", "⏰", "📅", "💼"]
            text = f"{random.choice(emojis)} {text}"
            
        message = self.simulator.create_text_message(self.user_id, text)
        self.message_history.append(message)
        
        # Simulate that this might create a task with keyboard
        if random.random() < 0.8:  # 80% chance it's recognized as task
            task_msg = self.simulator.create_task_message_with_keyboard(
                self.user_id,
                text,
                f"task_{message.message_id}"
            )
            self.task_messages.append(task_msg)
            
        return self.simulator.create_message_update(message)
        
    def _create_voice_update(self) -> Update:
        """Create a voice message update."""
        # Random duration between 1 and 15 seconds
        duration = random.randint(1, 15)
        message = self.simulator.create_voice_message(self.user_id, duration)
        self.message_history.append(message)
        return self.simulator.create_message_update(message)
        
    def _create_command_update(self) -> Update:
        """Create a command update."""
        commands = self.simulator.get_random_commands()
        cmd, args = random.choice(commands)
        message = self.simulator.create_command_message(self.user_id, cmd, args)
        self.message_history.append(message)
        return self.simulator.create_message_update(message)
        
    def _create_edit_update(self) -> Optional[Update]:
        """Create an edit message update."""
        # Need a previous message to edit
        if not self.message_history:
            return self._create_text_task_update()
            
        # Get a recent text message
        text_messages = [m for m in self.message_history[-5:] if m.text]
        if not text_messages:
            return self._create_text_task_update()
            
        original = random.choice(text_messages)
        
        # Create edited version
        edits = [
            " (срочно!)",
            " до вечера",
            " - обновлено",
            " + купить хлеб",
            " в 17:00"
        ]
        new_text = original.text + random.choice(edits)
        
        edited_message = self.simulator.create_edited_message(original, new_text)
        return self.simulator.create_edited_message_update(edited_message)
        
    def _create_callback_update(self) -> Optional[Update]:
        """Create a callback query update."""
        # Need a task message with keyboard
        if not self.task_messages:
            return self._create_text_task_update()
            
        # Pick a recent task
        task_msg = random.choice(self.task_messages[-5:] if len(self.task_messages) > 5 else self.task_messages)
        
        # Choose action
        action = random.choice(["complete", "delete"])
        task_id = f"task_{task_msg.message_id}"
        callback_data = f"{action}_{task_id}"
        
        callback_query = self.simulator.create_callback_query(
            self.user_id,
            callback_data,
            task_msg
        )
        
        # Remove from task messages if deleting
        if action == "delete":
            self.task_messages = [m for m in self.task_messages if m != task_msg]
            
        return self.simulator.create_callback_query_update(callback_query)


class LoadGenerator:
    """Generates load for stress testing."""
    
    def __init__(
        self,
        simulator: TelegramSimulator,
        profile: LoadProfile = LoadProfile()
    ):
        """Initialize load generator."""
        self.simulator = simulator
        self.profile = profile
        self.profile.validate()
        self.users: dict[int, UserBehavior] = {}
        
    def get_or_create_user(self, user_id: int) -> UserBehavior:
        """Get or create user behavior."""
        if user_id not in self.users:
            self.users[user_id] = UserBehavior(user_id, self.simulator, self.profile)
        return self.users[user_id]
        
    async def generate_user_session(
        self,
        user_id: int,
        message_count: int,
        on_update: Callable[[Update], None]
    ) -> dict:
        """Generate a session of user activity."""
        user = self.get_or_create_user(user_id)
        stats = {
            "user_id": user_id,
            "messages_sent": 0,
            "message_types": {t.value: 0 for t in MessageType},
            "errors": 0
        }
        
        for i in range(message_count):
            try:
                # Check for burst behavior
                if random.random() < self.profile.burst_probability:
                    # Send burst
                    burst_count = min(self.profile.burst_size, message_count - i)
                    for j in range(burst_count):
                        update = await user.generate_update()
                        if update:
                            on_update(update)
                            stats["messages_sent"] += 1
                            # Track type
                            if update.message:
                                if update.message.text and update.message.text.startswith("/"):
                                    stats["message_types"][MessageType.COMMAND.value] += 1
                                elif update.message.voice:
                                    stats["message_types"][MessageType.VOICE_MESSAGE.value] += 1
                                else:
                                    stats["message_types"][MessageType.TEXT_TASK.value] += 1
                            elif update.edited_message:
                                stats["message_types"][MessageType.EDIT_MESSAGE.value] += 1
                            elif update.callback_query:
                                stats["message_types"][MessageType.CALLBACK_BUTTON.value] += 1
                                
                        if j < burst_count - 1:
                            await asyncio.sleep(self.profile.burst_delay)
                    i += burst_count - 1
                else:
                    # Normal message
                    update = await user.generate_update()
                    if update:
                        on_update(update)
                        stats["messages_sent"] += 1
                        
                # Delay between messages
                delay = random.uniform(
                    self.profile.min_delay_between_messages,
                    self.profile.max_delay_between_messages
                )
                await asyncio.sleep(delay)
                
            except Exception as e:
                stats["errors"] += 1
                
        return stats
        
    async def generate_concurrent_load(
        self,
        user_ids: list[int],
        messages_per_user: int,
        on_update: Callable[[Update], None]
    ) -> list[dict]:
        """Generate load from multiple users concurrently."""
        tasks = []
        for user_id in user_ids:
            task = self.generate_user_session(user_id, messages_per_user, on_update)
            tasks.append(task)
            
        return await asyncio.gather(*tasks, return_exceptions=True)