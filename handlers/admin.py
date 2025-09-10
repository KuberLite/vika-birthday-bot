"""
Админские команды
"""
import logging
from datetime import datetime

from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram import Bot

from config.settings import ADMIN_IDS
from config.texts import (
    ADMIN_ONLY,
    PRESENTS_SENT,
    ALBUM_SENT,
    STATS_MESSAGE
)
from handlers.utils import send_birthday_wishes, create_album

router = Router()
logger = logging.getLogger(__name__)


def is_admin(user_id: int) -> bool:
    """Проверить, является ли пользователь администратором"""
    logger.info(f"Проверка админа: user_id={user_id}, ADMIN_IDS={ADMIN_IDS}, результат={user_id in ADMIN_IDS}")
    return user_id in ADMIN_IDS


@router.message(F.text == "/open_presents")
async def cmd_open_presents(message: Message, bot: Bot):
    """Вручную отправить все поздравления"""
    try:
        user_id = message.from_user.id
        
        if not is_admin(user_id):
            await message.answer(ADMIN_ONLY)
            return
        
        await message.answer("📦 Отправляю все поздравления...")
        
        # Отправляем поздравления
        await send_birthday_wishes(bot)
        
        await message.answer("✅ Все поздравления отправлены!")
        
        logger.info(f"Админ {user_id} вручную отправил поздравления")
        
    except Exception as e:
        logger.error(f"Ошибка в cmd_open_presents: {e}")
        await message.answer("❌ Произошла ошибка при отправке поздравлений.")


@router.message(F.text == "/get_album")
async def cmd_get_album(message: Message, bot: Bot):
    """Получить собранный альбом"""
    try:
        user_id = message.from_user.id
        
        if not is_admin(user_id):
            await message.answer(ADMIN_ONLY)
            return
        
        await message.answer("📸 Создаю альбом...")
        
        # Создаем альбом
        await create_album(bot)
        
        await message.answer("✅ Альбом создан и отправлен!")
        
        logger.info(f"Админ {user_id} вручную создал альбом")
        
    except Exception as e:
        logger.error(f"Ошибка в cmd_get_album: {e}")
        await message.answer("❌ Произошла ошибка при создании альбома.")


@router.message(F.text == "/stats")
async def cmd_stats(message: Message):
    """Показать статистику бота"""
    try:
        user_id = message.from_user.id
        
        if not is_admin(user_id):
            await message.answer(ADMIN_ONLY)
            return
        
        # Получаем статистику
        stats = await get_bot_stats()
        
        await message.answer(
            STATS_MESSAGE.format(
                users=stats['users'],
                wishes=stats['wishes'],
                files=stats['files'],
                songs=stats['songs'],
                timestamp=datetime.now().strftime("%d.%m.%Y %H:%M")
            )
        )
        
        logger.info(f"Админ {user_id} запросил статистику")
        
    except Exception as e:
        logger.error(f"Ошибка в cmd_stats: {e}")
        await message.answer("❌ Произошла ошибка при получении статистики.")


async def get_bot_stats() -> dict:
    """Получить статистику бота"""
    try:
        import aiosqlite
        from config.settings import DATABASE_PATH
        
        async with aiosqlite.connect(DATABASE_PATH) as db:
            # Количество пользователей
            async with db.execute("SELECT COUNT(*) FROM users") as cursor:
                users_row = await cursor.fetchone()
                users = users_row[0] if users_row else 0
            
            # Количество поздравлений
            async with db.execute("SELECT COUNT(*) FROM wishes") as cursor:
                wishes_row = await cursor.fetchone()
                wishes = wishes_row[0] if wishes_row else 0
            
            # Количество файлов в альбоме
            async with db.execute("SELECT COUNT(*) FROM album_files") as cursor:
                files_row = await cursor.fetchone()
                files = files_row[0] if files_row else 0
            
            # Количество предложений треков
            async with db.execute("SELECT COUNT(*) FROM song_requests") as cursor:
                songs_row = await cursor.fetchone()
                songs = songs_row[0] if songs_row else 0
            
            return {
                'users': users,
                'wishes': wishes,
                'files': files,
                'songs': songs
            }
            
    except Exception as e:
        logger.error(f"Ошибка получения статистики: {e}")
        return {
            'users': 0,
            'wishes': 0,
            'files': 0,
            'songs': 0
        }


@router.message(F.text == "/test")
async def cmd_test(message: Message):
    """Тестовая команда для проверки работы роутера"""
    logger.info(f"🧪 Тестовая команда от {message.from_user.id}")
    await message.answer("✅ Роутер админа работает!")


# Убираем catch_all - он перехватывает все сообщения
# @router.message()
# async def catch_all_admin_messages(message: Message):
#     """Ловим все сообщения для отладки"""
#     logger.info(f"🔍 Поймано сообщение в admin.py: {message.text} от {message.from_user.id}")
#     # Не отвечаем, просто логируем


@router.message(F.text == "/admin")
async def cmd_admin_help(message: Message):
    """Показать список админских команд"""
    try:
        user_id = message.from_user.id
        logger.info(f"Команда /admin от пользователя {user_id}")
        
        if not is_admin(user_id):
            logger.warning(f"Пользователь {user_id} не является админом")
            await message.answer(ADMIN_ONLY)
            return
        
        help_text = """
🔧 <b>Админские команды:</b>

/open_presents - Вручную отправить все поздравления
/get_album - Получить собранный альбом
/stats - Показать статистику бота
/broadcast &lt;текст&gt; - Рассылка сообщения всем пользователям
/set_start_photo yes|no - Установить стартовое фото (ответить на фото)
/get_start_photos - Показать текущие стартовые фото
/get_song_requests - Показать предложения треков
/admin - Показать это сообщение

📊 <b>Статистика:</b>
• Пользователи: количество зарегистрированных
• Поздравления: количество отправленных поздравлений
• Файлы: количество файлов в альбоме
• Треки: количество предложений треков

📸 <b>Стартовые фото:</b>
• Отправьте фото и ответьте командой /set_start_photo yes
• Отправьте фото и ответьте командой /set_start_photo no
        """
        
        await message.answer(help_text)
        
    except Exception as e:
        logger.error(f"Ошибка в cmd_admin_help: {e}")
        await message.answer("❌ Произошла ошибка.")


@router.message(F.text.startswith("/broadcast"))
async def cmd_broadcast(message: Message):
    """Рассылка сообщения всем пользователям"""
    try:
        user_id = message.from_user.id
        
        if not is_admin(user_id):
            await message.answer(ADMIN_ONLY)
            return
        
        # Получаем текст сообщения
        text = message.text.replace("/broadcast", "").strip()
        
        if not text:
            await message.answer("❌ Укажите текст для рассылки.\nПример: /broadcast Привет всем!")
            return
        
        # Получаем список всех пользователей
        import aiosqlite
        from config.settings import DATABASE_PATH
        
        async with aiosqlite.connect(DATABASE_PATH) as db:
            async with db.execute("SELECT user_id FROM users") as cursor:
                user_ids = await cursor.fetchall()
        
        # Отправляем сообщение всем пользователям
        sent = 0
        failed = 0
        
        for user_id_tuple in user_ids:
            try:
                await message.bot.send_message(user_id_tuple[0], text)
                sent += 1
            except Exception as e:
                logger.error(f"Ошибка отправки рассылки пользователю {user_id_tuple[0]}: {e}")
                failed += 1
        
        await message.answer(f"✅ Рассылка завершена!\nОтправлено: {sent}\nОшибок: {failed}")
        
        logger.info(f"Админ {user_id} отправил рассылку: {sent} успешно, {failed} ошибок")
        
    except Exception as e:
        logger.error(f"Ошибка в cmd_broadcast: {e}")
        await message.answer("❌ Произошла ошибка при рассылке.")


@router.message(F.text.startswith("/set_start_photo"))
async def cmd_set_start_photo(message: Message):
    """Установить стартовое фото для ответа да/нет"""
    try:
        user_id = message.from_user.id
        
        if not is_admin(user_id):
            await message.answer(ADMIN_ONLY)
            return
        
        # Проверяем, что это ответ на фото
        if not message.reply_to_message or not message.reply_to_message.photo:
            await message.answer("❌ Ответьте на фото командой /set_start_photo yes или /set_start_photo no")
            return
        
        # Получаем тип ответа (yes/no)
        command_parts = message.text.split()
        if len(command_parts) != 2 or command_parts[1] not in ['yes', 'no']:
            await message.answer("❌ Используйте: /set_start_photo yes или /set_start_photo no")
            return
        
        response_type = command_parts[1]
        photo = message.reply_to_message.photo[-1]  # Берем самое большое фото
        file_id = photo.file_id
        caption = message.reply_to_message.caption or ""
        
        # Сохраняем фото
        from handlers.utils import set_start_photo
        await set_start_photo(response_type, file_id, caption)
        
        await message.answer(f"✅ Стартовое фото для ответа '{response_type}' установлено!")
        
        logger.info(f"Админ {user_id} установил стартовое фото для {response_type}")
        
    except Exception as e:
        logger.error(f"Ошибка в cmd_set_start_photo: {e}")
        await message.answer("❌ Произошла ошибка при установке фото.")


@router.message(F.text == "/get_start_photos")
async def cmd_get_start_photos(message: Message):
    """Показать текущие стартовые фото"""
    try:
        user_id = message.from_user.id
        
        if not is_admin(user_id):
            await message.answer(ADMIN_ONLY)
            return
        
        from handlers.utils import get_start_photo
        
        # Получаем фото для "да"
        yes_file_id, yes_caption = await get_start_photo("yes")
        # Получаем фото для "нет"
        no_file_id, no_caption = await get_start_photo("no")
        
        response = "📸 <b>Текущие стартовые фото:</b>\n\n"
        
        if yes_file_id:
            response += "✅ <b>Для ответа 'Да':</b>\n"
            response += f"ID: <code>{yes_file_id}</code>\n"
            if yes_caption:
                response += f"Подпись: {yes_caption}\n"
            response += "\n"
        else:
            response += "❌ <b>Для ответа 'Да':</b> фото не установлено\n\n"
        
        if no_file_id:
            response += "❌ <b>Для ответа 'Нет':</b>\n"
            response += f"ID: <code>{no_file_id}</code>\n"
            if no_caption:
                response += f"Подпись: {no_caption}\n"
        else:
            response += "❌ <b>Для ответа 'Нет':</b> фото не установлено"
        
        await message.answer(response)
        
    except Exception as e:
        logger.error(f"Ошибка в cmd_get_start_photos: {e}")
        await message.answer("❌ Произошла ошибка при получении фото.")


@router.message(F.text == "/get_song_requests")
async def cmd_get_song_requests(message: Message):
    """Показать все предложения треков"""
    try:
        user_id = message.from_user.id
        
        if not is_admin(user_id):
            await message.answer(ADMIN_ONLY)
            return
        
        from handlers.utils import get_all_song_requests
        
        requests = await get_all_song_requests()
        
        if not requests:
            await message.answer("📭 Пока нет предложений треков.")
            return
        
        response = "🎵 <b>Предложения треков:</b>\n\n"
        
        for i, (track, first_name, username, timestamp) in enumerate(requests, 1):
            user_name = first_name or username or "Аноним"
            response += f"{i}. <b>{track}</b>\n"
            response += f"   👤 {user_name}\n"
            response += f"   📅 {timestamp}\n\n"
        
        response += f"<b>Всего предложений:</b> {len(requests)}"
        
        await message.answer(response)
        
    except Exception as e:
        logger.error(f"Ошибка в cmd_get_song_requests: {e}")
        await message.answer("❌ Произошла ошибка при получении предложений треков.")


@router.message(F.text == "/debug_wishes")
async def cmd_debug_wishes(message: Message):
    """Показать сохраненные поздравления для отладки"""
    try:
        user_id = message.from_user.id
        
        if not is_admin(user_id):
            await message.answer(ADMIN_ONLY)
            return
        
        import aiosqlite
        from config.settings import DATABASE_PATH
        
        async with aiosqlite.connect(DATABASE_PATH) as db:
            async with db.execute("""
                SELECT w.user_id, w.content_type, w.content, u.first_name, u.username, w.timestamp
                FROM wishes w
                LEFT JOIN users u ON w.user_id = u.user_id
                ORDER BY w.timestamp DESC
                LIMIT 10
            """) as cursor:
                wishes = await cursor.fetchall()
        
        if not wishes:
            await message.answer("📭 Нет сохраненных поздравлений.")
            return
        
        response = "🔍 <b>Последние поздравления:</b>\n\n"
        
        for wish in wishes:
            user_id_db, content_type, content, first_name, username, timestamp = wish
            user_name = first_name or username or "Нет имени"
            content_preview = content[:50] + "..." if len(content) > 50 else content
            
            response += f"👤 <b>User ID:</b> {user_id_db}\n"
            response += f"📝 <b>Имя:</b> {user_name}\n"
            response += f"📄 <b>Тип:</b> {content_type}\n"
            response += f"💬 <b>Содержимое:</b> {content_preview}\n"
            response += f"📅 <b>Время:</b> {timestamp}\n\n"
        
        await message.answer(response)
        
    except Exception as e:
        logger.error(f"Ошибка в cmd_debug_wishes: {e}")
        await message.answer("❌ Произошла ошибка при получении поздравлений.")

