#!/usr/bin/env python3
"""Run comprehensive stress tests for TaskerBot."""

import argparse
import asyncio
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from tests.stress.test_real_stress import (
    StressTestApplication,
    test_baseline_scenario,
    test_peak_load_scenario,
    test_sustained_load_scenario,
)


async def run_selected_test(test_name: str):
    """Run a specific test scenario."""
    app = StressTestApplication()
    await app.setup()
    
    try:
        if test_name == "baseline":
            await app.run_baseline_test()
        elif test_name == "peak":
            await app.run_peak_load_test()
        elif test_name == "sustained":
            await app.run_sustained_load_test()
        else:
            print(f"Unknown test: {test_name}")
            print("Available tests: baseline, peak, sustained")
            return
    finally:
        await app.cleanup()


async def run_all_tests():
    """Run all stress test scenarios."""
    app = StressTestApplication()
    await app.setup()
    
    try:
        print("🚀 Running all stress test scenarios...\n")
        
        # Baseline test
        await app.run_baseline_test()
        print("\n⏸️  Pausing for 30 seconds...\n")
        await asyncio.sleep(30)
        
        # Peak load test
        await app.run_peak_load_test()
        print("\n⏸️  Pausing for 30 seconds...\n")
        await asyncio.sleep(30)
        
        # Sustained load test
        await app.run_sustained_load_test()
        
        print("\n✅ All stress tests completed!")
        
    except Exception as e:
        print(f"\n❌ Stress test failed: {e}")
        import traceback
        traceback.print_exc()
        
    finally:
        await app.cleanup()


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Run TaskerBot stress tests")
    parser.add_argument(
        "test",
        nargs="?",
        default="all",
        choices=["all", "baseline", "peak", "sustained"],
        help="Test scenario to run (default: all)"
    )
    parser.add_argument(
        "--quick",
        action="store_true",
        help="Run quick versions of tests (reduced duration)"
    )
    
    args = parser.parse_args()
    
    if args.quick:
        print("⚡ Running quick stress tests (reduced duration)...")
        # Modify test durations for quick testing
        import tests.stress.test_real_stress as stress_module
        # You can add logic here to reduce test durations
    
    if args.test == "all":
        asyncio.run(run_all_tests())
    else:
        asyncio.run(run_selected_test(args.test))


if __name__ == "__main__":
    main()