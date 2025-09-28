"""
Утилиты для бота: таймер, счетчик, гадалка, база данных
"""
import asyncio
import logging
import random
import aiosqlite
from datetime import datetime, date
from pathlib import Path

from aiogram import Bot, Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.utils.keyboard import InlineKeyboardBuilder
from apscheduler.schedulers.asyncio import AsyncIOScheduler

router = Router()

from config.settings import (
    DATABASE_PATH,
    BIRTHDAY_DATE,
    REMINDER_DATE,
    REMINDER_TIME,
    SONG_RESULTS_DATE,
    SONG_RESULTS_TIME,
    ARCHIVE_DATE,
    SCHEDULER_TIMEZONE,
    ADMIN_IDS
)
from config.texts import (
    FORTUNE_LIST,
    FORTUNE_TITLE,
    REMINDER_MESSAGE,
    PRESENTS_SENT,
    ALBUM_SENT
)

logger = logging.getLogger(__name__)


# === БАЗА ДАННЫХ ===
async def init_database():
    """Инициализация базы данных"""
    try:
        async with aiosqlite.connect(DATABASE_PATH) as db:
            # Таблица пользователей
            await db.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    user_id INTEGER PRIMARY KEY,
                    username TEXT,
                    first_name TEXT,
                    last_name TEXT,
                    remembers_vika BOOLEAN DEFAULT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Таблица поздравлений
            await db.execute("""
                CREATE TABLE IF NOT EXISTS wishes (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER,
                    content_type TEXT,
                    content TEXT,
                    is_anonymous BOOLEAN DEFAULT 0,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    delivered BOOLEAN DEFAULT 0,
                    FOREIGN KEY (user_id) REFERENCES users (user_id)
                )
            """)
            
            # Таблица файлов альбома
            await db.execute("""
                CREATE TABLE IF NOT EXISTS album_files (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER,
                    file_id TEXT,
                    file_type TEXT,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users (user_id)
                )
            """)
            
            # Таблица предложений треков
            await db.execute("""
                CREATE TABLE IF NOT EXISTS song_requests (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER,
                    track_text TEXT,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users (user_id)
                )
            """)
            
            # Таблица подтверждения участия
            await db.execute("""
                CREATE TABLE IF NOT EXISTS guest_confirmations (
                    user_id INTEGER PRIMARY KEY,
                    confirmed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Таблица элементов вишлиста
            await db.execute("""
                CREATE TABLE IF NOT EXISTS wishlist_items (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    text TEXT NOT NULL,
                    added_by INTEGER,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (added_by) REFERENCES users (user_id)
                )
            """)
            
            # Таблица стартовых фото
            await db.execute("""
                CREATE TABLE IF NOT EXISTS start_photos (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    response_type TEXT,  -- 'yes' или 'no'
                    file_id TEXT,
                    caption TEXT,
                    is_active BOOLEAN DEFAULT 1,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Старая таблица guest_counter больше не нужна
            # Создаем новую таблицу для подтверждений участия
            
            await db.commit()
            
            # Проверяем и добавляем новое поле remembers_vika если его нет
            try:
                # Проверяем, есть ли уже поле remembers_vika
                cursor = await db.execute("PRAGMA table_info(users)")
                columns = await cursor.fetchall()
                column_names = [column[1] for column in columns]
                
                if 'remembers_vika' not in column_names:
                    logger.info("Добавляем поле remembers_vika в таблицу users")
                    await db.execute("ALTER TABLE users ADD COLUMN remembers_vika BOOLEAN DEFAULT NULL")
                    await db.commit()
                    logger.info("Поле remembers_vika добавлено успешно")
                    
            except Exception as migration_error:
                logger.error(f"Ошибка миграции БД: {migration_error}")
            
            # Проверяем и добавляем новое поле sent_to_users в таблицу album_files если его нет
            try:
                cursor = await db.execute("PRAGMA table_info(album_files)")
                columns = await cursor.fetchall()
                column_names = [column[1] for column in columns]
                
                if 'sent_to_users' not in column_names:
                    logger.info("Добавляем поле sent_to_users в таблицу album_files")
                    await db.execute("ALTER TABLE album_files ADD COLUMN sent_to_users BOOLEAN DEFAULT 0")
                    await db.commit()
                    logger.info("Поле sent_to_users добавлено успешно")
                    
            except Exception as migration_error:
                logger.error(f"Ошибка миграции album_files: {migration_error}")
            
            logger.info("База данных инициализирована")
            
    except Exception as e:
        logger.error(f"Ошибка инициализации БД: {e}")
        raise


async def add_user(user_id: int, username: str = None, first_name: str = None, last_name: str = None):
    """Добавить пользователя в БД"""
    try:
        async with aiosqlite.connect(DATABASE_PATH) as db:
            await db.execute("""
                INSERT OR REPLACE INTO users (user_id, username, first_name, last_name)
                VALUES (?, ?, ?, ?)
            """, (user_id, username, first_name, last_name))
            await db.commit()
    except Exception as e:
        logger.error(f"Ошибка добавления пользователя: {e}")


async def save_user_choice(user_id: int, remembers_vika: bool):
    """Сохранить выбор пользователя (помнит ли Вику)"""
    try:
        async with aiosqlite.connect(DATABASE_PATH) as db:
            # Обновляем поле remembers_vika для существующего пользователя
            await db.execute("""
                UPDATE users SET remembers_vika = ? WHERE user_id = ?
            """, (remembers_vika, user_id))
            
            # Если пользователя нет, создаем запись
            if db.total_changes == 0:
                await db.execute("""
                    INSERT INTO users (user_id, remembers_vika)
                    VALUES (?, ?)
                """, (user_id, remembers_vika))
            
            await db.commit()
            logger.info(f"Сохранен выбор пользователя {user_id}: {'помнит' if remembers_vika else 'не помнит'} Вику")
    except Exception as e:
        logger.error(f"Ошибка сохранения выбора пользователя: {e}")


async def get_user_choice(user_id: int) -> bool:
    """Получить выбор пользователя"""
    try:
        async with aiosqlite.connect(DATABASE_PATH) as db:
            async with db.execute("""
                SELECT remembers_vika FROM users WHERE user_id = ?
            """, (user_id,)) as cursor:
                row = await cursor.fetchone()
                return row[0] if row and row[0] is not None else None
    except Exception as e:
        logger.error(f"Ошибка получения выбора пользователя: {e}")
        return None


# === СТАРТОВЫЕ ФОТО ===
async def get_start_photo(response_type: str) -> tuple:
    """Получить стартовое фото для ответа (yes/no)"""
    try:
        async with aiosqlite.connect(DATABASE_PATH) as db:
            async with db.execute("""
                SELECT file_id, caption FROM start_photos 
                WHERE response_type = ? AND is_active = 1
                ORDER BY created_at DESC
                LIMIT 1
            """, (response_type,)) as cursor:
                row = await cursor.fetchone()
                return row if row else (None, None)
    except Exception as e:
        logger.error(f"Ошибка получения стартового фото: {e}")
        return (None, None)


async def set_start_photo(response_type: str, file_id: str, caption: str = None):
    """Установить стартовое фото для ответа"""
    try:
        async with aiosqlite.connect(DATABASE_PATH) as db:
            # Деактивируем старые фото этого типа
            await db.execute("""
                UPDATE start_photos SET is_active = 0 WHERE response_type = ?
            """, (response_type,))
            
            # Добавляем новое фото
            await db.execute("""
                INSERT INTO start_photos (response_type, file_id, caption)
                VALUES (?, ?, ?)
            """, (response_type, file_id, caption))
            await db.commit()
    except Exception as e:
        logger.error(f"Ошибка установки стартового фото: {e}")


# === СЧЕТЧИК ГОСТЕЙ ===
async def confirm_guest_participation(user_id: int) -> bool:
    """Подтвердить участие пользователя. Возвращает True если это новое подтверждение"""
    try:
        async with aiosqlite.connect(DATABASE_PATH) as db:
            # Проверяем, не подтвердил ли уже пользователь участие
            async with db.execute("SELECT user_id FROM guest_confirmations WHERE user_id = ?", (user_id,)) as cursor:
                existing = await cursor.fetchone()
                
            if existing:
                return False  # Уже подтвердил
            
            # Добавляем новое подтверждение
            await db.execute("INSERT INTO guest_confirmations (user_id) VALUES (?)", (user_id,))
            await db.commit()
            return True  # Новое подтверждение
    except Exception as e:
        logger.error(f"Ошибка подтверждения участия: {e}")
        return False


async def get_guest_count() -> int:
    """Получить количество подтвердивших участие"""
    try:
        async with aiosqlite.connect(DATABASE_PATH) as db:
            async with db.execute("SELECT COUNT(*) FROM guest_confirmations") as cursor:
                result = await cursor.fetchone()
                return result[0] if result else 0
    except Exception as e:
        logger.error(f"Ошибка получения количества гостей: {e}")
        return 0


async def is_guest_confirmed(user_id: int) -> bool:
    """Проверить, подтвердил ли пользователь участие"""
    try:
        async with aiosqlite.connect(DATABASE_PATH) as db:
            async with db.execute("SELECT user_id FROM guest_confirmations WHERE user_id = ?", (user_id,)) as cursor:
                result = await cursor.fetchone()
                return result is not None
    except Exception as e:
        logger.error(f"Ошибка проверки подтверждения: {e}")
        return False


async def get_confirmed_guests_list():
    """Получить список пользователей, подтвердивших участие, с их именами"""
    try:
        async with aiosqlite.connect(DATABASE_PATH) as db:
            async with db.execute("""
                SELECT u.user_id, u.first_name, u.last_name, u.username, gc.confirmed_at
                FROM guest_confirmations gc
                JOIN users u ON gc.user_id = u.user_id
                ORDER BY gc.confirmed_at ASC
            """) as cursor:
                results = await cursor.fetchall()
                
                guests = []
                for row in results:
                    user_id, first_name, last_name, username, confirmed_at = row
                    
                    # Формируем отображаемое имя
                    display_name = first_name or "Неизвестно"
                    if last_name:
                        display_name += f" {last_name}"
                    
                    if username:
                        display_name += f" (@{username})"
                    
                    guests.append({
                        'user_id': user_id,
                        'display_name': display_name,
                        'confirmed_at': confirmed_at
                    })
                
                return guests
    except Exception as e:
        logger.error(f"Ошибка получения списка гостей: {e}")
        return []


async def get_all_users_stats():
    """Получить статистику по всем пользователям бота"""
    try:
        async with aiosqlite.connect(DATABASE_PATH) as db:
            # Общее количество пользователей
            async with db.execute("SELECT COUNT(*) FROM users") as cursor:
                total_users = (await cursor.fetchone())[0]
            
            # Пользователи, которые помнят Вику
            async with db.execute("SELECT COUNT(*) FROM users WHERE remembers_vika = 1") as cursor:
                remembers_count = (await cursor.fetchone())[0]
            
            # Пользователи, которые не помнят Вику
            async with db.execute("SELECT COUNT(*) FROM users WHERE remembers_vika = 0") as cursor:
                not_remembers_count = (await cursor.fetchone())[0]
            
            # Пользователи без ответа
            async with db.execute("SELECT COUNT(*) FROM users WHERE remembers_vika IS NULL") as cursor:
                no_answer_count = (await cursor.fetchone())[0]
            
            # Количество поздравлений
            async with db.execute("SELECT COUNT(*) FROM wishes") as cursor:
                wishes_count = (await cursor.fetchone())[0]
            
            # Количество файлов в альбоме
            async with db.execute("SELECT COUNT(*) FROM album_files") as cursor:
                album_files_count = (await cursor.fetchone())[0]
            
            # Количество предложений треков
            async with db.execute("SELECT COUNT(*) FROM song_requests") as cursor:
                songs_count = (await cursor.fetchone())[0]
            
            # Количество подтвердивших участие
            async with db.execute("SELECT COUNT(*) FROM guest_confirmations") as cursor:
                confirmed_guests_count = (await cursor.fetchone())[0]
            
            return {
                'total_users': total_users,
                'remembers_vika': remembers_count,
                'not_remembers_vika': not_remembers_count,
                'no_answer': no_answer_count,
                'wishes_count': wishes_count,
                'album_files_count': album_files_count,
                'songs_count': songs_count,
                'confirmed_guests_count': confirmed_guests_count
            }
    except Exception as e:
        logger.error(f"Ошибка получения статистики пользователей: {e}")
        return None


# === ТАЙМЕР ДО ДНЯ РОЖДЕНИЯ ===
def get_days_until_birthday() -> int:
    """Получить количество дней до дня рождения"""
    try:
        birthday = datetime.strptime(BIRTHDAY_DATE, "%Y-%m-%d").date()
        today = date.today()
        delta = birthday - today
        return delta.days
    except Exception as e:
        logger.error(f"Ошибка расчета дней до ДР: {e}")
        return 0


def is_after_birthday() -> bool:
    """Проверить, прошла ли дата дня рождения"""
    return get_days_until_birthday() <= 0


def is_archive_mode() -> bool:
    """Проверить, включен ли архивный режим"""
    try:
        archive_date = datetime.strptime(ARCHIVE_DATE, "%Y-%m-%d").date()
        today = date.today()
        return today >= archive_date
    except Exception as e:
        logger.error(f"Ошибка проверки архивного режима: {e}")
        return False


# === ГАДАЛКА ===
def get_random_fortune() -> str:
    """Получить случайное предсказание"""
    fortune = random.choice(FORTUNE_LIST)
    return FORTUNE_TITLE.format(fortune=fortune)


# === ПРЕДЛОЖЕНИЯ ТРЕКОВ ===


# === SCHEDULED JOBS ===
async def setup_scheduler_jobs(scheduler: AsyncIOScheduler, bot: Bot):
    """Настройка запланированных задач"""
    try:
        # Отправка поздравлений в день рождения
        scheduler.add_job(
            send_birthday_wishes,
            'date',
            run_date=f"{BIRTHDAY_DATE} 00:01:00",
            args=[bot],
            id='birthday_wishes',
            timezone=SCHEDULER_TIMEZONE
        )
        
        # Напоминание накануне
        scheduler.add_job(
            send_reminder,
            'date',
            run_date=f"{REMINDER_DATE} {REMINDER_TIME}:00",
            args=[bot],
            id='reminder',
            timezone=SCHEDULER_TIMEZONE
        )
        
        # Результаты голосования больше не нужны (система треков заменена на предложения)
        
        # Создание альбома через неделю после ДР
        from datetime import timedelta
        album_date = datetime.strptime(BIRTHDAY_DATE, "%Y-%m-%d") + timedelta(days=7)
        scheduler.add_job(
            create_album,
            'date',
            run_date=album_date,
            args=[bot],
            id='create_album',
            timezone=SCHEDULER_TIMEZONE
        )
        
        # Автоматическая отправка новых фото каждый час (только после дня рождения)
        birthday_datetime = datetime.strptime(BIRTHDAY_DATE, "%Y-%m-%d")
        if datetime.now() >= birthday_datetime:
            scheduler.add_job(
                send_new_photos_to_users,
                'interval',
                hours=1,
                args=[bot],
                id='auto_send_photos',
                timezone=SCHEDULER_TIMEZONE
            )
            logger.info("📸 Автоматическая отправка новых фото настроена (каждый час)")
        else:
            logger.info("📸 Автоматическая отправка фото будет активирована после дня рождения")
        
        logger.info("Scheduled jobs настроены")
        
    except Exception as e:
        logger.error(f"Ошибка настройки scheduler: {e}")


async def send_birthday_wishes(bot: Bot):
    """Отправить все поздравления в день рождения"""
    try:
        async with aiosqlite.connect(DATABASE_PATH) as db:
            async with db.execute("""
                SELECT w.*, u.first_name, u.username
                FROM wishes w
                JOIN users u ON w.user_id = u.user_id
                WHERE w.delivered = 0
            """) as cursor:
                wishes = await cursor.fetchall()
        
        count = 0
        for wish in wishes:
            try:
                # Отправляем Вике и админам
                for admin_id in ADMIN_IDS:
                    if wish[2] == 'text':  # content_type
                        await bot.send_message(admin_id, f"💌 Поздравление от {wish[7] or wish[8] or 'Анонима'}:\n\n{wish[3]}")
                    else:
                        # Для медиа файлов
                        if wish[2] == 'photo':
                            await bot.send_photo(admin_id, wish[3], caption=f"💌 Поздравление от {wish[7] or wish[8] or 'Анонима'}")
                        elif wish[2] == 'video':
                            await bot.send_video(admin_id, wish[3], caption=f"💌 Поздравление от {wish[7] or wish[8] or 'Анонима'}")
                        elif wish[2] == 'voice':
                            await bot.send_voice(admin_id, wish[3], caption=f"💌 Поздравление от {wish[7] or wish[8] or 'Анонима'}")
                        elif wish[2] == 'sticker':
                            await bot.send_sticker(admin_id, wish[3])
                
                # Отмечаем как доставленное
                async with aiosqlite.connect(DATABASE_PATH) as db:
                    await db.execute("UPDATE wishes SET delivered = 1 WHERE id = ?", (wish[0],))
                    await db.commit()
                
                count += 1
                
            except Exception as e:
                logger.error(f"Ошибка отправки поздравления {wish[0]}: {e}")
        
        # Уведомляем админов
        for admin_id in ADMIN_IDS:
            await bot.send_message(admin_id, PRESENTS_SENT.format(count=count))
        
        logger.info(f"Отправлено {count} поздравлений")
        
    except Exception as e:
        logger.error(f"Ошибка отправки поздравлений: {e}")


async def send_reminder(bot: Bot):
    """Отправить напоминание всем, кто отправил поздравление"""
    try:
        async with aiosqlite.connect(DATABASE_PATH) as db:
            async with db.execute("SELECT DISTINCT user_id FROM wishes") as cursor:
                user_ids = await cursor.fetchall()
        
        for user_id_tuple in user_ids:
            try:
                await bot.send_message(user_id_tuple[0], REMINDER_MESSAGE)
            except Exception as e:
                logger.error(f"Ошибка отправки напоминания пользователю {user_id_tuple[0]}: {e}")
        
        logger.info(f"Отправлено {len(user_ids)} напоминаний")
        
    except Exception as e:
        logger.error(f"Ошибка отправки напоминаний: {e}")




async def create_album(bot: Bot, debug_mode: bool = False):
    """Создать альбом из всех загруженных файлов
    
    Args:
        bot: Экземпляр бота
        debug_mode: Если True, отправляет альбом только админам (без уведомления пользователей)
    """
    try:
        async with aiosqlite.connect(DATABASE_PATH) as db:
            async with db.execute("""
                SELECT file_id, file_type
                FROM album_files
                ORDER BY timestamp
            """) as cursor:
                files = await cursor.fetchall()
        
        # Инициализируем списки файлов
        photos = []
        videos = []
        
        if not files:
            message = "Альбом пуст - никто не загрузил фото с тусовки 😢"
        else:
            # Группируем файлы по типам для создания альбома
            photos = [f[0] for f in files if f[1] == 'photo']
            videos = [f[0] for f in files if f[1] == 'video']
            
            message = f"🎉 Альбом с тусовки готов!\n\nВсего файлов: {len(files)}"
        
        # Отправляем альбом админам (всегда)
        for admin_id in ADMIN_IDS:
            try:
                # Отправляем фото частями по 10 штук (лимит Telegram для media_group)
                if photos:
                    for i in range(0, len(photos), 10):
                        photo_chunk = photos[i:i+10]
                        await bot.send_media_group(admin_id, [{"type": "photo", "media": photo} for photo in photo_chunk])
                        # Небольшая задержка между частями для избежания rate limiting
                        if i + 10 < len(photos):
                            await asyncio.sleep(0.5)
                
                # Отправляем видео по одному
                if videos:
                    for video in videos:
                        await bot.send_video(admin_id, video)
                        
                logger.info(f"✅ Альбом успешно отправлен админу {admin_id}")
                        
            except Exception as e:
                # Более информативное логирование ошибок для админов
                if "chat not found" in str(e).lower():
                    logger.warning(f"⚠️ Админ {admin_id} недоступен (возможно, заблокировал бота или неверный ID)")
                elif "flood control" in str(e).lower():
                    logger.warning(f"⏳ Rate limiting при отправке админу {admin_id}: {e}")
                else:
                    logger.error(f"Ошибка отправки альбома админу {admin_id}: {e}")
        
        # В дебаг режиме уведомляем только админов, иначе всех пользователей
        if debug_mode:
            # В дебаг режиме отправляем сообщение только админам
            for admin_id in ADMIN_IDS:
                try:
                    debug_message = f"🔧 DEBUG MODE\n\n{message}"
                    await bot.send_message(admin_id, debug_message)
                except Exception as e:
                    logger.error(f"Ошибка отправки дебаг сообщения админу {admin_id}: {e}")
            logger.info("Альбом создан и отправлен в дебаг режиме (только админам)")
        else:
            # Обычный режим - отправляем альбом всем пользователям
            async with aiosqlite.connect(DATABASE_PATH) as db:
                async with db.execute("SELECT user_id FROM users") as cursor:
                    user_ids = await cursor.fetchall()
            
            for user_id_tuple in user_ids:
                try:
                    user_id = user_id_tuple[0]
                    
                    # Отправляем фото частями по 10 штук (лимит Telegram для media_group)
                    if photos:
                        for i in range(0, len(photos), 10):
                            photo_chunk = photos[i:i+10]
                            await bot.send_media_group(user_id, [{"type": "photo", "media": photo} for photo in photo_chunk])
                            # Небольшая задержка между частями для избежания rate limiting
                            if i + 10 < len(photos):
                                await asyncio.sleep(0.5)
                    
                    # Отправляем видео по одному, если есть
                    if videos:
                        for video in videos:
                            await bot.send_video(user_id, video)
                    
                    # Отправляем текстовое сообщение
                    await bot.send_message(user_id, message)
                    
                except Exception as e:
                    logger.error(f"Ошибка отправки альбома пользователю {user_id}: {e}")
            logger.info("Альбом создан и отправлен всем пользователям")
            
            # Помечаем все фото как отправленные пользователям
            if files:
                async with aiosqlite.connect(DATABASE_PATH) as db:
                    await db.execute("""
                        UPDATE album_files 
                        SET sent_to_users = 1 
                        WHERE file_type = 'photo'
                    """)
                    await db.commit()
                logger.info("📸 Все фото помечены как отправленные пользователям")
        
    except Exception as e:
        logger.error(f"Ошибка создания альбома: {e}")


async def send_new_photos_to_users(bot: Bot):
    """Автоматически отправить новые фото пользователям (каждый час)"""
    try:
        # Проверяем, не активирован ли архивный режим
        if is_archive_mode():
            logger.info("📸 Архивный режим активирован, автоматическая отправка фото отключена")
            return
        # Находим фото, которые еще не были отправлены пользователям
        async with aiosqlite.connect(DATABASE_PATH) as db:
            async with db.execute("""
                SELECT id, file_id, file_type, user_id
                FROM album_files
                WHERE sent_to_users = 0 AND file_type = 'photo'
                ORDER BY timestamp ASC
            """) as cursor:
                new_photos = await cursor.fetchall()
        
        if not new_photos:
            logger.info("📸 Новых фото для отправки пользователям нет")
            return
        
        logger.info(f"📸 Найдено {len(new_photos)} новых фото для отправки")
        
        # Получаем список всех пользователей
        async with aiosqlite.connect(DATABASE_PATH) as db:
            async with db.execute("SELECT user_id FROM users") as cursor:
                user_ids = await cursor.fetchall()
        
        if not user_ids:
            logger.warning("📸 Нет пользователей для отправки фото")
            return
        
        # Группируем фото по 10 штук для отправки альбомом
        photo_file_ids = [photo[1] for photo in new_photos]
        
        # Отправляем фото всем пользователям
        for user_id_tuple in user_ids:
            try:
                user_id = user_id_tuple[0]
                
                # Отправляем фото частями по 10 штук (лимит Telegram для media_group)
                for i in range(0, len(photo_file_ids), 10):
                    photo_chunk = photo_file_ids[i:i+10]
                    
                    if len(photo_chunk) == 1:
                        # Если одно фото, отправляем как обычное фото с подписью
                        await bot.send_photo(
                            user_id, 
                            photo_chunk[0], 
                            caption="📸 Новое фото добавлено в альбом!"
                        )
                    else:
                        # Если несколько фото, отправляем как альбом
                        media_group = [{"type": "photo", "media": photo} for photo in photo_chunk]
                        # Добавляем подпись только к первому фото
                        media_group[0]["caption"] = f"📸 Добавлено {len(photo_chunk)} новых фото в альбом!"
                        await bot.send_media_group(user_id, media_group)
                    
                    # Увеличенная задержка между частями для избежания rate limiting
                    if i + 10 < len(photo_file_ids):
                        await asyncio.sleep(2.0)  # Увеличиваем до 2 секунд
                
                # Задержка между пользователями для избежания flood control
                await asyncio.sleep(1.0)
                
                logger.info(f"📸 Отправлено {len(photo_file_ids)} фото пользователю {user_id}")
                
            except Exception as e:
                logger.error(f"Ошибка отправки новых фото пользователю {user_id}: {e}")
                # Если ошибка rate limiting, ждем дольше
                if "Flood control exceeded" in str(e) or "Too Many Requests" in str(e):
                    logger.info("⏳ Обнаружен rate limiting, ждем 5 секунд...")
                    await asyncio.sleep(5.0)
        
        # Помечаем фото как отправленные пользователям только в конце, когда все отправлено
        async with aiosqlite.connect(DATABASE_PATH) as db:
            photo_ids = [photo[0] for photo in new_photos]
            placeholders = ','.join('?' * len(photo_ids))
            await db.execute(f"""
                UPDATE album_files 
                SET sent_to_users = 1 
                WHERE id IN ({placeholders})
            """, photo_ids)
            await db.commit()
        
        logger.info(f"📸 Автоматическая отправка завершена: {len(new_photos)} фото отправлено {len(user_ids)} пользователям")
        
    except Exception as e:
        logger.error(f"Ошибка автоматической отправки новых фото: {e}")


# === RATE LIMITING ===
user_messages = {}


async def check_rate_limit(user_id: int) -> bool:
    """Проверить rate limit для пользователя"""
    now = datetime.now()
    
    if user_id not in user_messages:
        user_messages[user_id] = []
    
    # Удаляем старые сообщения (старше минуты)
    user_messages[user_id] = [
        msg_time for msg_time in user_messages[user_id]
        if (now - msg_time).seconds < 60
    ]
    
    # Проверяем лимит
    if len(user_messages[user_id]) >= 5:
        return False
    
    # Добавляем текущее сообщение
    user_messages[user_id].append(now)
    return True


# === ОБРАБОТЧИКИ ГОЛОСОВАНИЯ ===


async def save_song_request(user_id: int, track_text: str):
    """Сохранить предложение трека"""
    try:
        async with aiosqlite.connect(DATABASE_PATH) as db:
            await db.execute("""
                INSERT INTO song_requests (user_id, track_text)
                VALUES (?, ?)
            """, (user_id, track_text))
            await db.commit()
            logger.info(f"Предложение трека сохранено: {user_id} - {track_text}")
    except Exception as e:
        logger.error(f"Ошибка сохранения предложения трека: {e}")
        raise


async def get_all_song_requests():
    """Получить все предложения треков"""
    try:
        async with aiosqlite.connect(DATABASE_PATH) as db:
            async with db.execute("""
                SELECT sr.track_text, u.first_name, u.username, sr.timestamp
                FROM song_requests sr
                LEFT JOIN users u ON sr.user_id = u.user_id
                ORDER BY sr.timestamp DESC
            """) as cursor:
                rows = await cursor.fetchall()
                return rows
    except Exception as e:
        logger.error(f"Ошибка получения предложений треков: {e}")
        return []


# === РАБОТА С ВИШЛИСТОМ ===

async def add_wishlist_item(item_text: str, admin_id: int):
    """Добавить элемент в вишлист"""
    try:
        async with aiosqlite.connect(DATABASE_PATH) as db:
            await db.execute("""
                INSERT INTO wishlist_items (text, added_by)
                VALUES (?, ?)
            """, (item_text, admin_id))
            await db.commit()
            logger.info(f"Элемент вишлиста добавлен: {item_text} (админ {admin_id})")
            return True
    except Exception as e:
        logger.error(f"Ошибка добавления элемента вишлиста: {e}")
        return False


async def get_wishlist_items():
    """Получить все элементы вишлиста"""
    try:
        async with aiosqlite.connect(DATABASE_PATH) as db:
            async with db.execute("""
                SELECT id, text, timestamp
                FROM wishlist_items
                ORDER BY timestamp ASC
            """) as cursor:
                rows = await cursor.fetchall()
                return rows
    except Exception as e:
        logger.error(f"Ошибка получения элементов вишлиста: {e}")
        return []


async def delete_wishlist_item(item_id: int):
    """Удалить элемент из вишлиста"""
    try:
        async with aiosqlite.connect(DATABASE_PATH) as db:
            cursor = await db.execute("""
                DELETE FROM wishlist_items WHERE id = ?
            """, (item_id,))
            await db.commit()
            if cursor.rowcount > 0:
                logger.info(f"Элемент вишлиста удален: ID {item_id}")
                return True
            else:
                logger.warning(f"Элемент вишлиста не найден: ID {item_id}")
                return False
    except Exception as e:
        logger.error(f"Ошибка удаления элемента вишлиста: {e}")
        return False


async def format_wishlist():
    """Форматировать вишлист для отображения"""
    items = await get_wishlist_items()
    
    if not items:
        return "🎁 Вишлист Вики:\n\nЗдесь пока ничего нет 🫠\n\nГлавное - внимание и любовь! ❤️"
    
    wishlist_text = "🎁 Вишлист Вики:\n\n"
    
    for i, (item_id, text, timestamp) in enumerate(items, 1):
        wishlist_text += f"{i}. {text}\n"
    
    wishlist_text += "\nГлавное - внимание и любовь! ❤️"
    
    return wishlist_text
