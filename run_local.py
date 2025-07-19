#!/usr/bin/env python
"""Script to run bot locally for testing."""

import asyncio
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent))

from src.main import main

if __name__ == "__main__":
    print("🚀 Starting TaskerBot locally...")
    print("📝 Use ngrok to expose webhook: ngrok http 8443")
    print("🔗 Then update TELEGRAM_WEBHOOK_URL in .env")
    print("-" * 50)
    
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n👋 Bot stopped by user")