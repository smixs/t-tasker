"""Telegram API simulator for stress testing with proper aiogram 3 Update objects."""

import random
import time
from datetime import datetime
from typing import Optional
from unittest.mock import AsyncMock

from aiogram.types import (
    CallbackQuery,
    Chat,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Message,
    MessageEntity,
    Update,
    User,
    Voice,
)


class TelegramSimulator:
    """Simulates Telegram API interactions with proper Update objects."""

    def __init__(self):
        """Initialize the simulator."""
        self.update_id_counter = random.randint(100000, 999999)
        self.message_id_counter = random.randint(1000, 9999)
        
    def _next_update_id(self) -> int:
        """Get next update ID."""
        self.update_id_counter += 1
        return self.update_id_counter
        
    def _next_message_id(self) -> int:
        """Get next message ID."""
        self.message_id_counter += 1
        return self.message_id_counter
        
    def create_user(self, user_id: int) -> User:
        """Create a User object."""
        return User(
            id=user_id,
            is_bot=False,
            first_name=f"User{user_id}",
            last_name=f"Test{user_id}",
            username=f"user{user_id}",
            language_code="ru"
        )
        
    def create_chat(self, user_id: int) -> Chat:
        """Create a private Chat object."""
        return Chat(
            id=user_id,
            type="private",
            first_name=f"User{user_id}",
            last_name=f"Test{user_id}",
            username=f"user{user_id}"
        )
        
    def create_text_message(
        self, 
        user_id: int, 
        text: str,
        message_id: Optional[int] = None
    ) -> Message:
        """Create a text Message object."""
        return Message(
            message_id=message_id or self._next_message_id(),
            date=datetime.now(),
            chat=self.create_chat(user_id),
            from_user=self.create_user(user_id),
            text=text,
            entities=[]
        )
        
    def create_voice_message(
        self, 
        user_id: int,
        duration: int = 5,
        message_id: Optional[int] = None
    ) -> Message:
        """Create a voice Message object."""
        msg_id = message_id or self._next_message_id()
        return Message(
            message_id=msg_id,
            date=datetime.now(),
            chat=self.create_chat(user_id),
            from_user=self.create_user(user_id),
            voice=Voice(
                file_id=f"voice_{msg_id}_{user_id}",
                file_unique_id=f"voice_unique_{msg_id}",
                duration=duration,
                mime_type="audio/ogg"
            )
        )
        
    def create_command_message(
        self, 
        user_id: int, 
        command: str,
        args: str = ""
    ) -> Message:
        """Create a command Message object."""
        text = f"/{command}"
        if args:
            text += f" {args}"
            
        msg_id = self._next_message_id()
        
        # Create command entity
        entities = [
            MessageEntity(
                type="bot_command",
                offset=0,
                length=len(f"/{command}")
            )
        ]
        
        return Message(
            message_id=msg_id,
            date=datetime.now(),
            chat=self.create_chat(user_id),
            from_user=self.create_user(user_id),
            text=text,
            entities=entities
        )
        
    def create_callback_query(
        self,
        user_id: int,
        callback_data: str,
        message: Message
    ) -> CallbackQuery:
        """Create a CallbackQuery object."""
        return CallbackQuery(
            id=str(random.randint(100000, 999999)),
            from_user=self.create_user(user_id),
            message=message,
            data=callback_data,
            chat_instance=str(user_id)
        )
        
    def create_edited_message(
        self,
        original_message: Message,
        new_text: str
    ) -> Message:
        """Create an edited Message object."""
        # Create a new message with same ID but different text
        return Message(
            message_id=original_message.message_id,
            date=original_message.date,
            chat=original_message.chat,
            from_user=original_message.from_user,
            text=new_text,
            edit_date=datetime.now(),
            entities=[]
        )
        
    def create_message_update(self, message: Message) -> Update:
        """Create an Update with a message."""
        return Update(
            update_id=self._next_update_id(),
            message=message
        )
        
    def create_edited_message_update(self, edited_message: Message) -> Update:
        """Create an Update with an edited message."""
        return Update(
            update_id=self._next_update_id(),
            edited_message=edited_message
        )
        
    def create_callback_query_update(self, callback_query: CallbackQuery) -> Update:
        """Create an Update with a callback query."""
        return Update(
            update_id=self._next_update_id(),
            callback_query=callback_query
        )
        
    def create_task_message_with_keyboard(
        self,
        user_id: int,
        task_text: str,
        task_id: str
    ) -> Message:
        """Create a message with inline keyboard (as bot would send)."""
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(text="✅ Готово", callback_data=f"complete_{task_id}"),
                InlineKeyboardButton(text="🗑 Удалить", callback_data=f"delete_{task_id}")
            ]
        ])
        
        msg = self.create_text_message(user_id, f"✅ Задача создана:\n\n{task_text}")
        # In real scenario, this would be sent by bot, but for testing we simulate it
        msg.reply_markup = keyboard
        return msg
        
    def attach_mock_bot_to_message(self, message: Message, bot_mock: AsyncMock) -> None:
        """Attach mock bot to message for handlers that expect message.bot."""
        # Since Message is frozen, we can't add attributes
        # Instead, handlers should get bot from context data
        pass
        
    def get_random_task_texts(self) -> list[str]:
        """Get list of random task texts for testing."""
        return [
            "Купить молоко завтра в 10:00",
            "Позвонить маме вечером",
            "Встреча с клиентом в понедельник в 15:00",
            "Оплатить счета до конца месяца",
            "Записаться к врачу на следующей неделе",
            "Подготовить презентацию к пятнице",
            "Отправить отчет руководителю до 18:00",
            "Забрать документы из офиса",
            "Проверить почту и ответить на важные письма",
            "Сделать резервную копию данных"
        ]
        
    def get_random_commands(self) -> list[tuple[str, str]]:
        """Get list of random commands for testing."""
        return [
            ("start", ""),
            ("help", ""),
            ("setup", ""),
            ("recent", ""),
            ("recent", "5"),
            ("undo", ""),
            ("autodelete", ""),
            ("status", "")
        ]