"""
Telegram-бот для дня рождения Вики Ботнарь
Главный файл запуска бота
"""
import asyncio
import logging
import sys
from pathlib import Path

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from dotenv import load_dotenv

from config.settings import (
    BOT_TOKEN, 
    ERROR_LOG_PATH, 
    SCHEDULER_TIMEZONE,
    ADMIN_IDS
)
from handlers import (
    start,
    menu,
    wishes,
    album,
    admin,
    utils,
    songs
)
from handlers.utils import setup_scheduler_jobs, init_database


async def setup_logging():
    """Настройка логирования"""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(ERROR_LOG_PATH, encoding='utf-8'),
            logging.StreamHandler(sys.stdout)
        ]
    )
    
    # Отключаем лишние логи
    logging.getLogger('aiogram').setLevel(logging.WARNING)
    logging.getLogger('apscheduler').setLevel(logging.WARNING)


async def main():
    """Главная функция запуска бота"""
    # Загружаем переменные окружения
    load_dotenv()
    
    # Настраиваем логирование
    await setup_logging()
    logger = logging.getLogger(__name__)
    
    try:
        # Инициализируем базу данных
        await init_database()
        
        # Создаем бота и диспетчер
        bot = Bot(
            token=BOT_TOKEN,
            default=DefaultBotProperties(parse_mode=ParseMode.HTML)
        )
        # Создаем диспетчер с хранилищем состояний
        storage = MemoryStorage()
        dp = Dispatcher(storage=storage)
        
        # Проверяем подключение к Telegram API
        try:
            bot_info = await bot.get_me()
            logger.info(f"✅ Бот подключен: @{bot_info.username} ({bot_info.first_name})")
        except Exception as e:
            logger.error(f"❌ Ошибка подключения к Telegram API: {e}")
            raise
        
        # Настраиваем scheduler
        scheduler = AsyncIOScheduler(timezone=SCHEDULER_TIMEZONE)
        
        # Регистрируем роутеры (admin и songs первыми для FSM, wishes перед album)
        logger.info("Регистрируем роутеры...")
        dp.include_router(admin.router)
        logger.info("✅ admin.router зарегистрирован")
        dp.include_router(songs.router)
        logger.info("✅ songs.router зарегистрирован")
        dp.include_router(start.router)
        logger.info("✅ start.router зарегистрирован")
        dp.include_router(menu.router)
        logger.info("✅ menu.router зарегистрирован")
        dp.include_router(wishes.router)
        logger.info("✅ wishes.router зарегистрирован")
        dp.include_router(album.router)
        logger.info("✅ album.router зарегистрирован")
        dp.include_router(utils.router)
        logger.info("✅ utils.router зарегистрирован")
        
        # Убираем debug обработчик - он блокирует остальные
        # @dp.message()
        # async def debug_all_messages(message):
        #     logger.info(f"🔍 DEBUG: Получено сообщение '{message.text}' от {message.from_user.id}")
        
        # Настраиваем scheduled jobs
        await setup_scheduler_jobs(scheduler, bot)
        
        # Запускаем scheduler
        scheduler.start()
        
        logger.info(f"Бот запущен! Администраторы: {ADMIN_IDS}")
        
        # Удаляем webhook если он был установлен
        await bot.delete_webhook(drop_pending_updates=True)
        logger.info("🔄 Webhook удален, начинаем polling")
        
        # Запускаем бота
        logger.info("🚀 Запускаем polling...")
        await dp.start_polling(bot, polling_timeout=10)
        
    except Exception as e:
        logger.error(f"Ошибка при запуске бота: {e}")
        raise
    finally:
        if 'scheduler' in locals():
            scheduler.shutdown()
        if 'bot' in locals():
            await bot.session.close()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nБот остановлен пользователем")
    except Exception as e:
        print(f"Критическая ошибка: {e}")
        sys.exit(1)
