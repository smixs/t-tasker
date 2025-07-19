#!/usr/bin/env python
"""Простой запуск бота без webhook."""

import asyncio
import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage

from src.core.settings import get_settings
from src.core.database import get_database
from src.handlers import command_router, error_router, message_router

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def main():
    """Запуск бота в режиме polling."""
    settings = get_settings()
    
    # Создаем бота
    bot = Bot(
        token=settings.telegram_token,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML)
    )
    
    # Создаем диспетчер с памятью вместо Redis
    dp = Dispatcher(storage=MemoryStorage())
    
    # Подключаем обработчики
    dp.include_router(error_router)
    dp.include_router(command_router)
    dp.include_router(message_router)
    
    # База данных
    db = get_database()
    await db.create_tables()
    
    # Удаляем webhook если был
    await bot.delete_webhook(drop_pending_updates=True)
    
    # Информация о боте
    bot_info = await bot.get_me()
    print(f"\n✅ Бот @{bot_info.username} запущен!")
    print("💬 Откройте Telegram и напишите боту /start")
    print("🛑 Для остановки нажмите Ctrl+C\n")
    
    try:
        await dp.start_polling(bot)
    finally:
        await bot.session.close()
        await db.close()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n👋 Бот остановлен")