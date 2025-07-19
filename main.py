"""Main entry point for the TaskerBot application."""

import asyncio
import logging
import sys
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from src.core.settings import get_settings
from src.core.server import run_webhook_server


def setup_logging() -> None:
    """Configure logging for the application."""
    settings = get_settings()
    
    logging.basicConfig(
        level=getattr(logging, settings.log_level),
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[
            logging.StreamHandler(sys.stdout)
        ]
    )
    
    # Set aiogram logging level
    logging.getLogger("aiogram").setLevel(logging.INFO)
    
    # Reduce noise from other libraries
    logging.getLogger("aiohttp").setLevel(logging.WARNING)
    logging.getLogger("asyncio").setLevel(logging.WARNING)


def main() -> None:
    """Main function to start the bot."""
    try:
        # Setup logging
        setup_logging()
        
        logger = logging.getLogger(__name__)
        logger.info("Starting TaskerBot...")
        
        # Validate settings
        settings = get_settings()
        logger.info(f"Bot configured for: {settings.otel_service_name}")
        
        # Run webhook server
        run_webhook_server()
        
    except KeyboardInterrupt:
        logger.info("Bot stopped by user")
    except Exception as e:
        logger.exception(f"Failed to start bot: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
