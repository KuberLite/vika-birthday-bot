"""
Настройки бота для дня рождения Вики
"""
import os
from pathlib import Path

# Базовые пути
BASE_DIR = Path(__file__).parent.parent
DATA_DIR = BASE_DIR / "data"
MEDIA_DIR = BASE_DIR / "media"
LOGS_DIR = BASE_DIR / "logs"

# Создаем необходимые директории
DATA_DIR.mkdir(exist_ok=True)
LOGS_DIR.mkdir(exist_ok=True)
(MEDIA_DIR / "surprise").mkdir(parents=True, exist_ok=True)

# Настройки бота из переменных окружения
BOT_TOKEN = os.getenv("BOT_TOKEN")
if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN не найден в переменных окружения!")

# ID администраторов (задаются в .env файле)
ADMIN_IDS = [
    int(admin_id.strip()) 
    for admin_id in os.getenv("ADMIN_IDS", "").split(",") 
    if admin_id.strip()
]

if len(ADMIN_IDS) != 2:
    raise ValueError("Должно быть указано ровно 2 ADMIN_IDS в .env файле!")

# База данных
DATABASE_PATH = DATA_DIR / "bot.db"

# Логирование
ERROR_LOG_PATH = LOGS_DIR / "error.log"

# Даты и время
BIRTHDAY_DATE = "2025-09-26"  # День рождения Вики
BIRTHDAY_TIME = "00:01"       # Время доставки поздравлений
REMINDER_DATE = "2025-09-25"  # Дата напоминания
REMINDER_TIME = "19:00"       # Время напоминания
SONG_RESULTS_DATE = "2025-09-27"  # Дата показа результатов голосования
SONG_RESULTS_TIME = "12:00"   # Время показа результатов
ARCHIVE_DATE = "2025-10-31"   # Дата перехода в архивный режим

# Ограничения
MAX_FILES_PER_USER = 5        # Максимум файлов на пользователя в альбоме
RATE_LIMIT_MESSAGES = 5       # Лимит сообщений в минуту
RATE_LIMIT_WINDOW = 60        # Окно для rate limit в секундах

# Настройки альбома
ALBUM_DELAY_DAYS = 7          # Через сколько дней после ДР показать альбом

# Настройки APScheduler
SCHEDULER_TIMEZONE = "Europe/Moscow"

