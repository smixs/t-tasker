"""Comprehensive stress test for TaskerBot with realistic load patterns."""

import asyncio
import logging
import os
import sys
import time
from typing import Optional
from unittest.mock import AsyncMock, Mock, patch

import psutil
import pytest
from aiogram import Bot, Dispatcher
from aiogram.types import Update
from redis.asyncio import Redis

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from src.core.database import get_database
from src.core.middleware import (
    ErrorHandlingMiddleware,
    LoggingMiddleware,
    RateLimitMiddleware,
    UserContextMiddleware,
)
from src.core.redis_storage import RetryRedisStorage
from src.core.settings import get_settings
from src.handlers import callback_router, command_router, edit_router, error_router, message_router
from src.middleware.auth import AuthMiddleware
from src.repositories.user import UserRepository
from src.services.encryption import EncryptionService

from .load_generator import LoadGenerator, LoadProfile
from .metrics_collector import MetricsCollector
from .mock_services import MockBotWithMetrics, RealisticDeepgramMock, RealisticOpenAIMock, RealisticTodoistMock
from .telegram_simulator import TelegramSimulator

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


class StressTestApplication:
    """Stress test application with realistic bot setup."""

    def __init__(self, disable_rate_limit: bool = True):
        """Initialize stress test application."""
        self.settings = get_settings()
        self.database = get_database()
        self.redis: Optional[Redis] = None
        self.dispatcher: Optional[Dispatcher] = None
        self.bot_mock: Optional[MockBotWithMetrics] = None
        self.metrics = MetricsCollector()
        self.disable_rate_limit = disable_rate_limit
        
        # Services
        self.openai_mock = RealisticOpenAIMock()
        self.deepgram_mock = RealisticDeepgramMock()
        self.todoist_mock = RealisticTodoistMock()
        
        # Load generation
        self.telegram_sim = TelegramSimulator()
        self.load_gen = LoadGenerator(self.telegram_sim)
        
    async def setup(self):
        """Setup test application."""
        logger.info("Setting up stress test application...")
        
        # Initialize database
        await self.database.create_tables()
        await self._create_test_users()
        
        # Setup Redis
        self.redis = Redis.from_url(self.settings.redis_url, decode_responses=True)
        await self.redis.ping()
        
        # Create bot mock
        self.bot_mock = MockBotWithMetrics()
        
        # Create dispatcher
        self.dispatcher = Dispatcher(
            storage=RetryRedisStorage(self.redis, max_retries=3, retry_delay=0.1)
        )
        
        # Register routers
        self.dispatcher.include_router(error_router)
        self.dispatcher.include_router(command_router)
        self.dispatcher.include_router(edit_router)
        self.dispatcher.include_router(message_router)
        self.dispatcher.include_router(callback_router)
        
        # Setup middleware
        if self.disable_rate_limit:
            # High limit for stress testing
            self.dispatcher.message.middleware(RateLimitMiddleware(max_requests=10000, window=1))
        else:
            self.dispatcher.message.middleware(RateLimitMiddleware())
            
        self.dispatcher.message.middleware(UserContextMiddleware())
        self.dispatcher.message.middleware(AuthMiddleware())
        self.dispatcher.message.middleware(ErrorHandlingMiddleware())
        self.dispatcher.message.middleware(LoggingMiddleware())
        
        # Also add middleware for callback queries and edited messages
        self.dispatcher.callback_query.middleware(UserContextMiddleware())
        self.dispatcher.callback_query.middleware(AuthMiddleware())
        self.dispatcher.edited_message.middleware(UserContextMiddleware())
        self.dispatcher.edited_message.middleware(AuthMiddleware())
        
        logger.info("Stress test application setup complete")
        
    async def _create_test_users(self, count: int = 200, reuse_existing: bool = True):
        """Create test users with Todoist tokens."""
        logger.info(f"Creating {count} test users...")
        encryption = EncryptionService()
        
        async with self.database.get_session() as session:
            user_repo = UserRepository(session)
            
            for user_id in range(1, count + 1):
                user = await user_repo.create_or_update(
                    user_id=user_id,
                    username=f"stressuser{user_id}",
                    first_name=f"Stress{user_id}",
                    language_code="ru"
                )
                
                # Set encrypted token
                encrypted_token = encryption.encrypt(f"test_todoist_token_{user_id}")
                await user_repo.update_todoist_token(user_id, encrypted_token)
                
            await session.commit()
            
        logger.info("Test users created")
        
    async def cleanup(self):
        """Cleanup resources."""
        if self.redis:
            await self.redis.close()
        if self.database:
            await self.database.close()
            
    async def process_update(self, update: Update):
        """Process a single update through the dispatcher."""
        async with self.metrics.track_request(self._get_update_type(update)):
            # Track API calls
            openai_start = time.time()
            deepgram_start = time.time()
            todoist_start = time.time()
            
            # Patch services with tracking
            with patch('src.services.openai_service.OpenAIService.parse_intent', self.openai_mock.parse_intent), \
                 patch('src.services.deepgram_service.DeepgramService.transcribe', self.deepgram_mock.transcribe), \
                 patch('src.services.todoist_service.TodoistService.create_task', self.todoist_mock.create_task), \
                 patch('src.services.todoist_service.TodoistService.get_projects', self.todoist_mock.get_projects), \
                 patch('src.services.todoist_service.TodoistService.complete_task', self.todoist_mock.complete_task), \
                 patch('src.services.todoist_service.TodoistService.delete_task', self.todoist_mock.delete_task), \
                 patch('src.services.todoist_service.TodoistService.get_tasks', self.todoist_mock.get_tasks):
                
                # Process update
                await self.dispatcher.feed_raw_update(self.bot_mock, update.model_dump())
                
    def _get_update_type(self, update: Update) -> str:
        """Determine update type for metrics."""
        if update.message:
            if update.message.text and update.message.text.startswith("/"):
                return "command"
            elif update.message.voice:
                return "voice_message"
            else:
                return "text_message"
        elif update.edited_message:
            return "edit_message"
        elif update.callback_query:
            return "callback"
        return "unknown"
        
    async def monitor_resources(self, interval: float = 1.0):
        """Monitor system resources during test."""
        process = psutil.Process()
        
        while True:
            try:
                # Get CPU and memory usage
                cpu_percent = process.cpu_percent(interval=0.1)
                memory_info = process.memory_info()
                memory_mb = memory_info.rss / 1024 / 1024
                
                # Get Redis connection count
                redis_info = await self.redis.info()
                redis_connections = redis_info.get('connected_clients', 0)
                
                self.metrics.add_resource_sample(cpu_percent, memory_mb, redis_connections)
                
                await asyncio.sleep(interval)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Resource monitoring error: {e}")
                
    async def run_baseline_test(self):
        """Run baseline test: 50 users, 1 msg/sec each, 5 minutes."""
        logger.info("\n" + "="*80)
        logger.info("BASELINE TEST: 50 users, 1 msg/sec each, 5 minutes")
        logger.info("="*80 + "\n")
        
        self.metrics.start_test()
        
        # Start resource monitoring
        monitor_task = asyncio.create_task(self.monitor_resources())
        
        try:
            # Generate updates for 5 minutes
            num_users = 50
            test_duration = 300  # 5 minutes
            messages_per_user = test_duration  # 1 per second
            
            updates_queue = asyncio.Queue(maxsize=1000)
            
            # Producer task
            async def produce_updates():
                def on_update(update: Update):
                    asyncio.create_task(updates_queue.put(update))
                    
                await self.load_gen.generate_concurrent_load(
                    user_ids=list(range(1, num_users + 1)),
                    messages_per_user=messages_per_user,
                    on_update=on_update
                )
                
            # Consumer tasks
            async def consume_updates():
                while True:
                    try:
                        update = await asyncio.wait_for(updates_queue.get(), timeout=1.0)
                        await self.process_update(update)
                    except asyncio.TimeoutError:
                        if updates_queue.empty():
                            break
                    except Exception as e:
                        logger.error(f"Error processing update: {e}")
                        
            # Start producer
            producer = asyncio.create_task(produce_updates())
            
            # Start multiple consumers
            consumers = [
                asyncio.create_task(consume_updates())
                for _ in range(10)  # 10 concurrent processors
            ]
            
            # Wait for completion
            await producer
            await asyncio.gather(*consumers, return_exceptions=True)
            
        finally:
            monitor_task.cancel()
            self.metrics.end_test()
            
        # Print results
        self.metrics.print_summary()
        logger.info(f"\nBot API calls: {self.bot_mock.get_metrics_summary()}")
        
    async def run_peak_load_test(self):
        """Run peak load test: 100 users, burst of 500 messages in 10 seconds."""
        logger.info("\n" + "="*80)
        logger.info("PEAK LOAD TEST: 100 users, 500 messages burst in 10 seconds")
        logger.info("="*80 + "\n")
        
        self.metrics.start_test()
        
        # Create burst profile
        burst_profile = LoadProfile(
            min_delay_between_messages=0.01,
            max_delay_between_messages=0.02,
            burst_probability=0.8,
            burst_size=10
        )
        burst_gen = LoadGenerator(self.telegram_sim, burst_profile)
        
        # Start resource monitoring
        monitor_task = asyncio.create_task(self.monitor_resources())
        
        try:
            # Generate 500 messages from 100 users in 10 seconds
            num_users = 100
            messages_per_user = 5
            
            updates = []
            
            def on_update(update: Update):
                updates.append(update)
                
            # Generate all updates
            logger.info("Generating burst updates...")
            await burst_gen.generate_concurrent_load(
                user_ids=list(range(1, num_users + 1)),
                messages_per_user=messages_per_user,
                on_update=on_update
            )
            
            logger.info(f"Processing {len(updates)} updates...")
            start_time = time.time()
            
            # Process all updates concurrently
            tasks = [self.process_update(update) for update in updates]
            await asyncio.gather(*tasks, return_exceptions=True)
            
            burst_duration = time.time() - start_time
            logger.info(f"Burst processed in {burst_duration:.2f} seconds")
            
        finally:
            monitor_task.cancel()
            self.metrics.end_test()
            
        # Print results
        self.metrics.print_summary()
        logger.info(f"\nBot API calls: {self.bot_mock.get_metrics_summary()}")
        
    async def run_sustained_load_test(self):
        """Run sustained load test: 50 users, continuous load for 30 minutes."""
        logger.info("\n" + "="*80)
        logger.info("SUSTAINED LOAD TEST: 50 users, 30 minutes continuous")
        logger.info("="*80 + "\n")
        
        self.metrics.start_test()
        
        # Start resource monitoring
        monitor_task = asyncio.create_task(self.monitor_resources())
        
        try:
            # Run for 30 minutes with periodic status updates
            num_users = 50
            test_duration = 1800  # 30 minutes
            messages_per_user = test_duration // 2  # ~1 msg per 2 seconds
            status_interval = 300  # Status every 5 minutes
            
            updates_queue = asyncio.Queue(maxsize=1000)
            start_time = time.time()
            
            # Status reporter
            async def report_status():
                while True:
                    await asyncio.sleep(status_interval)
                    elapsed = time.time() - start_time
                    if elapsed >= test_duration:
                        break
                        
                    summary = self.metrics.get_summary()
                    logger.info(f"\n--- Status at {elapsed/60:.1f} minutes ---")
                    logger.info(f"Processed: {summary['total_requests']:,} requests")
                    logger.info(f"Success rate: {summary['success_rate']:.2f}%")
                    logger.info(f"Current RPS: {summary['throughput']['current_rps']:.2f}")
                    if 'overall' in summary['latency']:
                        logger.info(f"P95 latency: {summary['latency']['overall']['p95']:.2f}ms")
                        
            # Start status reporter
            status_task = asyncio.create_task(report_status())
            
            # Producer task
            async def produce_updates():
                def on_update(update: Update):
                    asyncio.create_task(updates_queue.put(update))
                    
                await self.load_gen.generate_concurrent_load(
                    user_ids=list(range(1, num_users + 1)),
                    messages_per_user=messages_per_user,
                    on_update=on_update
                )
                
            # Consumer tasks
            async def consume_updates():
                while True:
                    try:
                        update = await asyncio.wait_for(updates_queue.get(), timeout=1.0)
                        await self.process_update(update)
                    except asyncio.TimeoutError:
                        if updates_queue.empty() and time.time() - start_time > test_duration:
                            break
                    except Exception as e:
                        logger.error(f"Error processing update: {e}")
                        
            # Start producer
            producer = asyncio.create_task(produce_updates())
            
            # Start consumers
            consumers = [
                asyncio.create_task(consume_updates())
                for _ in range(10)
            ]
            
            # Wait for completion
            await producer
            await asyncio.gather(*consumers, return_exceptions=True)
            status_task.cancel()
            
        finally:
            monitor_task.cancel()
            self.metrics.end_test()
            
        # Print results
        self.metrics.print_summary()
        logger.info(f"\nBot API calls: {self.bot_mock.get_metrics_summary()}")


@pytest.mark.asyncio
@pytest.mark.stress
async def test_baseline_scenario():
    """Test baseline scenario."""
    app = StressTestApplication()
    await app.setup()
    
    try:
        await app.run_baseline_test()
    finally:
        await app.cleanup()
        

@pytest.mark.asyncio
@pytest.mark.stress
async def test_peak_load_scenario():
    """Test peak load scenario."""
    app = StressTestApplication()
    await app.setup()
    
    try:
        await app.run_peak_load_test()
    finally:
        await app.cleanup()
        

@pytest.mark.asyncio
@pytest.mark.stress
async def test_sustained_load_scenario():
    """Test sustained load scenario."""
    app = StressTestApplication()
    await app.setup()
    
    try:
        await app.run_sustained_load_test()
    finally:
        await app.cleanup()


async def main():
    """Run all stress tests."""
    logger.info("🚀 Starting comprehensive TaskerBot stress tests...\n")
    
    app = StressTestApplication()
    await app.setup()
    
    try:
        # Run tests in sequence
        await app.run_baseline_test()
        
        # Short break between tests
        logger.info("\n⏸️  Pausing for 30 seconds between tests...\n")
        await asyncio.sleep(30)
        
        await app.run_peak_load_test()
        
        # Another break
        logger.info("\n⏸️  Pausing for 30 seconds between tests...\n")
        await asyncio.sleep(30)
        
        await app.run_sustained_load_test()
        
        logger.info("\n✅ All stress tests completed!")
        
    except Exception as e:
        logger.error(f"\n❌ Stress test failed: {e}")
        import traceback
        traceback.print_exc()
        
    finally:
        await app.cleanup()


if __name__ == "__main__":
    asyncio.run(main())