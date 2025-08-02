"""Quick verification test to ensure stress test framework works."""

import asyncio
import logging
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from tests.stress.load_generator import LoadProfile
from tests.stress.test_real_stress import StressTestApplication

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def test_quick_verify():
    """Run a very quick test to verify the framework works."""
    logger.info("Running quick verification test...")
    
    # Create app with custom quick profile
    app = StressTestApplication()
    
    # Override with quick settings
    quick_profile = LoadProfile(
        min_delay_between_messages=0.01,
        max_delay_between_messages=0.05
    )
    app.load_gen.profile = quick_profile
    
    # Override to create fewer users
    original_create_users = app._create_test_users
    async def create_fewer_users(*args, **kwargs):
        kwargs['count'] = 10  # Only create 10 users for quick test
        return await original_create_users(*args, **kwargs)
    app._create_test_users = create_fewer_users
    
    await app.setup()
    
    try:
        # Run a mini version of baseline test
        logger.info("Testing with 5 users, 10 messages each...")
        app.metrics.start_test()
        
        # Generate test load
        updates = []
        
        def on_update(update):
            updates.append(update)
            
        await app.load_gen.generate_concurrent_load(
            user_ids=[1, 2, 3, 4, 5],
            messages_per_user=10,
            on_update=on_update
        )
        
        logger.info(f"Generated {len(updates)} updates")
        
        # Log sample update types
        update_types = {}
        for update in updates[:20]:
            if update.message:
                update_types['message'] = update_types.get('message', 0) + 1
            elif update.callback_query:
                update_types['callback'] = update_types.get('callback', 0) + 1
            elif update.edited_message:
                update_types['edit'] = update_types.get('edit', 0) + 1
        logger.info(f"Update types: {update_types}")
        
        # Process updates
        process_tasks = [app.process_update(update) for update in updates[:20]]  # Process first 20
        results = await asyncio.gather(*process_tasks, return_exceptions=True)
        
        errors = [r for r in results if isinstance(r, Exception)]
        logger.info(f"Processed {len(results)} updates, {len(errors)} errors")
        
        if errors:
            logger.error("Sample errors:")
            for err in errors[:3]:
                logger.error(f"  - {type(err).__name__}: {err}")
        
        app.metrics.end_test()
        
        # Print summary
        summary = app.metrics.get_summary()
        logger.info(f"\nQuick test results:")
        logger.info(f"Total requests: {summary['total_requests']}")
        logger.info(f"Success rate: {summary['success_rate']:.2f}%")
        logger.info(f"Test duration: {summary['test_duration_seconds']:.2f}s")
        
        if 'overall' in summary['latency']:
            logger.info(f"P95 latency: {summary['latency']['overall']['p95']:.2f}ms")
            
        logger.info("\n✅ Quick verification test passed!")
        
    except Exception as e:
        logger.error(f"❌ Quick test failed: {e}")
        import traceback
        traceback.print_exc()
        raise
        
    finally:
        await app.cleanup()


if __name__ == "__main__":
    asyncio.run(test_quick_verify())