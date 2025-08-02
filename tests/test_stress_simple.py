"""Simple stress test - 50 users sending messages simultaneously."""

import asyncio
import random
import time
from datetime import datetime
from typing import List
from unittest.mock import AsyncMock, Mock, patch

import pytest
from aiogram import Bot, Dispatcher
from aiogram.types import Chat, Message, User, Voice

from src.core.database import get_database
from src.core.redis_storage import RetryRedisStorage
from src.core.settings import get_settings
from src.handlers import callback_router, command_router, edit_router, error_router, message_router
from src.middleware.auth import AuthMiddleware
from src.core.middleware import (
    ErrorHandlingMiddleware,
    LoggingMiddleware,
    RateLimitMiddleware,
    UserContextMiddleware,
)


class StressTestBot:
    """Helper class to create a test bot with real handlers."""
    
    def __init__(self):
        self.settings = get_settings()
        self.database = get_database()
        self.processed_messages = 0
        self.errors = []
        self.success_count = 0
        
    async def setup(self):
        """Setup test bot with real middleware and handlers."""
        # Create bot mock
        self.bot = AsyncMock(spec=Bot)
        self.bot.get_me = AsyncMock(return_value=Mock(username="test_bot"))
        
        # Mock bot methods for message handling
        self.bot.answer = AsyncMock()
        self.bot.send_message = AsyncMock()
        self.bot.edit_message_text = AsyncMock()
        self.bot.get_file = AsyncMock()
        self.bot.download_file = AsyncMock(return_value=b"fake audio data")
        
        # Create real Redis connection for testing
        from redis.asyncio import Redis
        self.redis = Redis.from_url(
            self.settings.redis_url,
            decode_responses=True
        )
        
        # Create dispatcher with real storage
        self.dispatcher = Dispatcher(
            storage=RetryRedisStorage(self.redis)
        )
        
        # Register real routers
        self.dispatcher.include_router(error_router)
        self.dispatcher.include_router(command_router)
        self.dispatcher.include_router(edit_router)
        self.dispatcher.include_router(message_router)
        self.dispatcher.include_router(callback_router)
        
        # Disable rate limiting for stress test
        self.dispatcher.message.middleware(RateLimitMiddleware(max_requests=1000, window=1))
        self.dispatcher.message.middleware(UserContextMiddleware())
        self.dispatcher.message.middleware(AuthMiddleware())
        self.dispatcher.message.middleware(ErrorHandlingMiddleware())
        self.dispatcher.message.middleware(LoggingMiddleware())
        
        # Initialize database
        await self.database.create_tables()
        
        # Create test users in database
        await self._create_test_users()
        
    async def _create_test_users(self):
        """Create test users in database with Todoist tokens."""
        from src.repositories.user import UserRepository
        from src.services.encryption import EncryptionService
        
        encryption = EncryptionService()
        
        async with self.database.get_session() as session:
            user_repo = UserRepository(session)
            
            # Create 100 test users (to support up to 100 concurrent users)
            for user_id in range(1, 101):
                # Create or update user
                user = await user_repo.create_or_update(
                    user_id=user_id,
                    username=f"user{user_id}",
                    first_name=f"User{user_id}",
                    language_code="ru"
                )
                
                # Encrypt and set a fake Todoist token
                encrypted_token = encryption.encrypt(f"fake_todoist_token_{user_id}")
                await user_repo.update_todoist_token(user_id, encrypted_token)
            
            await session.commit()
        
    async def cleanup(self):
        """Cleanup resources."""
        await self.redis.close()
        await self.database.close()


def create_fake_message(user_id: int, text: str = None, voice: bool = False) -> Message:
    """Create a fake Telegram message for testing."""
    user = User(
        id=user_id,
        is_bot=False,
        first_name=f"User{user_id}",
        username=f"user{user_id}",
        language_code="ru"
    )
    
    chat = Chat(
        id=user_id,
        type="private",
        first_name=f"User{user_id}",
        username=f"user{user_id}"
    )
    
    message_id = random.randint(1000, 99999)
    
    if voice:
        # Create voice message
        voice_obj = Voice(
            file_id=f"voice_{message_id}",
            file_unique_id=f"voice_unique_{message_id}",
            duration=random.randint(1, 10)
        )
        return Message(
            message_id=message_id,
            date=datetime.now(),
            chat=chat,
            from_user=user,
            voice=voice_obj
        )
    else:
        # Create text message
        return Message(
            message_id=message_id,
            date=datetime.now(),
            chat=chat,
            from_user=user,
            text=text or f"Тестовое сообщение от пользователя {user_id}"
        )


async def simulate_user_activity(
    bot: StressTestBot,
    user_id: int,
    messages_count: int = 10
) -> dict:
    """Simulate one user sending multiple messages."""
    results = {
        "user_id": user_id,
        "sent": 0,
        "errors": 0,
        "timings": []
    }
    
    # Mix of message types
    for i in range(messages_count):
        try:
            start = time.time()
            
            # 70% text, 30% voice
            if random.random() < 0.7:
                message = create_fake_message(
                    user_id,
                    text=random.choice([
                        "Купить молоко завтра",
                        "Позвонить маме в 18:00",
                        "Встреча с клиентом в понедельник в 10:00",
                        "Оплатить счета до конца месяца",
                        "Записаться к врачу на следующей неделе"
                    ])
                )
            else:
                message = create_fake_message(user_id, voice=True)
            
            # Attach answer method to message for handlers to use
            message.answer = bot.bot.send_message
            message.bot = bot.bot
            
            # Process message through dispatcher
            update = {"message": message, "update_id": random.randint(1, 999999)}
            await bot.dispatcher.feed_update(bot.bot, update)
            
            elapsed = time.time() - start
            results["timings"].append(elapsed)
            results["sent"] += 1
            
            # Small random delay between messages
            await asyncio.sleep(random.uniform(0.1, 0.5))
            
        except Exception as e:
            results["errors"] += 1
            bot.errors.append(f"User {user_id}: {str(e)}")
    
    return results


@pytest.mark.asyncio
async def test_stress_50_concurrent_users():
    """Test 50 users sending messages concurrently."""
    print("\n=== STARTING STRESS TEST: 50 CONCURRENT USERS ===\n")
    
    # Mock external services to avoid real API calls
    with patch('src.services.openai_service.OpenAIService.parse_intent') as mock_openai, \
         patch('src.services.deepgram_service.DeepgramService.transcribe') as mock_deepgram, \
         patch('src.services.todoist_service.TodoistService.create_task') as mock_todoist:
        
        # Setup mocks
        mock_openai.return_value = Mock(
            intent_type="task_creation",
            task=Mock(content="Test task", project_name="Inbox")
        )
        mock_deepgram.return_value = "Транскрибированный текст"
        mock_todoist.return_value = Mock(
            id="123",
            content="Test task",
            project_id="456"
        )
        
        # Create and setup test bot
        bot = StressTestBot()
        await bot.setup()
        
        try:
            # Start timing
            start_time = time.time()
            
            # Create tasks for 50 concurrent users
            tasks = []
            num_users = 50
            messages_per_user = 10
            
            print(f"Creating {num_users} users, each sending {messages_per_user} messages...")
            print(f"Total messages: {num_users * messages_per_user}\n")
            
            for user_id in range(1, num_users + 1):
                task = simulate_user_activity(bot, user_id, messages_per_user)
                tasks.append(task)
            
            # Run all users concurrently
            print("Starting concurrent message sending...")
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Calculate statistics
            total_time = time.time() - start_time
            
            # Handle exceptions in results
            exceptions = [r for r in results if isinstance(r, Exception)]
            successful_results = [r for r in results if isinstance(r, dict)]
            
            if exceptions:
                print(f"\n⚠️  {len(exceptions)} user simulations failed completely:")
                for i, exc in enumerate(exceptions[:5]):
                    print(f"  - {exc}")
                if len(exceptions) > 5:
                    print(f"  ... and {len(exceptions) - 5} more")
            
            total_sent = sum(r["sent"] for r in successful_results)
            total_errors = sum(r["errors"] for r in successful_results) + len(exceptions) * messages_per_user
            all_timings = []
            
            for r in successful_results:
                if r["timings"]:
                    all_timings.extend(r["timings"])
            
            # Print results
            print("\n=== STRESS TEST RESULTS ===\n")
            print(f"Total time: {total_time:.2f} seconds")
            print(f"Total messages sent: {total_sent}")
            print(f"Total errors: {total_errors}")
            if total_sent > 0:
                print(f"Success rate: {(total_sent - total_errors) / total_sent * 100:.1f}%")
                print(f"Messages per second: {total_sent / total_time:.2f}")
            else:
                print("No messages were sent successfully!")
            
            if all_timings:
                avg_time = sum(all_timings) / len(all_timings)
                p95_time = sorted(all_timings)[int(len(all_timings) * 0.95)]
                p99_time = sorted(all_timings)[int(len(all_timings) * 0.99)]
                
                print(f"\nLatency statistics:")
                print(f"Average: {avg_time * 1000:.2f}ms")
                print(f"P95: {p95_time * 1000:.2f}ms")
                print(f"P99: {p99_time * 1000:.2f}ms")
            
            if bot.errors:
                print(f"\nFirst 10 errors:")
                for error in bot.errors[:10]:
                    print(f"- {error}")
            
            # Assert basic success criteria
            assert total_errors < total_sent * 0.1, f"Too many errors: {total_errors}/{total_sent}"
            assert total_time < 120, f"Test took too long: {total_time}s"
            
            print("\n✅ STRESS TEST PASSED!")
            
        finally:
            await bot.cleanup()


@pytest.mark.asyncio 
async def test_stress_burst_traffic():
    """Test burst traffic - all users send messages at exactly the same time."""
    print("\n=== STARTING BURST TEST: 50 USERS SIMULTANEOUS ===\n")
    
    with patch('src.services.openai_service.OpenAIService.parse_intent') as mock_openai, \
         patch('src.services.deepgram_service.DeepgramService.transcribe') as mock_deepgram, \
         patch('src.services.todoist_service.TodoistService.create_task') as mock_todoist:
        
        # Setup mocks with delays to simulate real processing
        async def delayed_parse(*args, **kwargs):
            await asyncio.sleep(random.uniform(0.1, 0.3))  # Simulate API delay
            return Mock(
                intent_type="task_creation",
                task=Mock(content="Test task", project_name="Inbox")
            )
        
        mock_openai.side_effect = delayed_parse
        mock_deepgram.return_value = "Транскрибированный текст"
        mock_todoist.return_value = Mock(id="123", content="Test task")
        
        bot = StressTestBot()
        await bot.setup()
        
        try:
            num_users = 50
            
            # Create all messages first
            messages = []
            for user_id in range(1, num_users + 1):
                msg = create_fake_message(user_id, "Срочная задача!")
                messages.append((user_id, msg))
            
            print(f"Sending {num_users} messages simultaneously...")
            start_time = time.time()
            
            # Send all messages at once
            tasks = []
            for user_id, msg in messages:
                task = bot.dispatcher.feed_update(bot.bot, {"message": msg})
                tasks.append(task)
            
            # Wait for all to complete
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            total_time = time.time() - start_time
            errors = [r for r in results if isinstance(r, Exception)]
            
            print(f"\nBurst test completed in {total_time:.2f}s")
            print(f"Successful: {len(results) - len(errors)}")
            print(f"Errors: {len(errors)}")
            print(f"Processing rate: {len(results) / total_time:.2f} msg/s")
            
            if errors:
                print(f"\nFirst 5 errors:")
                for error in errors[:5]:
                    print(f"- {error}")
            
            assert len(errors) < len(results) * 0.2, "Too many errors in burst test"
            
        finally:
            await bot.cleanup()


if __name__ == "__main__":
    # Run tests directly
    asyncio.run(test_stress_50_concurrent_users())
    asyncio.run(test_stress_burst_traffic())