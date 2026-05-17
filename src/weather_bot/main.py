import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage

from weather_bot.bot.handlers import router
from weather_bot.config import settings
from weather_bot.storage.db import init_db

logging.basicConfig(level=logging.INFO)


async def main() -> None:
    await init_db()

    bot = Bot(token=settings.TELEGRAM_BOT_TOKEN)
    dp = Dispatcher(storage=MemoryStorage())
    dp.include_router(router)

    logging.info("Starting weather bot...")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
