#!/usr/bin/env python3
"""Run TaskerBot stress tests.

Usage:
    python run_stress_test.py           # Run all tests
    python run_stress_test.py baseline  # Run only baseline test
    python run_stress_test.py peak      # Run only peak load test
    python run_stress_test.py sustained # Run only sustained load test
"""

import asyncio
import logging
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from tests.stress.test_real_stress import StressTestApplication

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


async def run_test(test_type: str = "all"):
    """Run stress test(s)."""
    logger.info(f"🚀 Starting TaskerBot stress test: {test_type}")
    
    app = StressTestApplication()
    await app.setup()
    
    try:
        if test_type == "baseline" or test_type == "all":
            await app.run_baseline_test()
            if test_type == "all":
                logger.info("\n⏸️  Pausing for 30 seconds between tests...\n")
                await asyncio.sleep(30)
        
        if test_type == "peak" or test_type == "all":
            await app.run_peak_load_test()
            if test_type == "all":
                logger.info("\n⏸️  Pausing for 30 seconds between tests...\n")
                await asyncio.sleep(30)
        
        if test_type == "sustained" or test_type == "all":
            await app.run_sustained_load_test()
        
        logger.info("\n✅ Stress test completed!")
        
    except Exception as e:
        logger.error(f"\n❌ Stress test failed: {e}")
        import traceback
        traceback.print_exc()
        
    finally:
        await app.cleanup()


def main():
    """Main entry point."""
    # Parse command line arguments
    test_type = "all"
    if len(sys.argv) > 1:
        test_type = sys.argv[1].lower()
        if test_type not in ["all", "baseline", "peak", "sustained"]:
            print(__doc__)
            sys.exit(1)
    
    # Run the test
    asyncio.run(run_test(test_type))


if __name__ == "__main__":
    main()