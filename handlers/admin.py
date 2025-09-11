"""
Админские команды
"""
import logging
from datetime import datetime

from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram import Bot
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

from config.settings import ADMIN_IDS
from config.texts import (
    ADMIN_ONLY,
    PRESENTS_SENT,
    ALBUM_SENT,
    STATS_MESSAGE
)
from handlers.utils import (
    send_birthday_wishes, create_album, get_confirmed_guests_list, get_all_users_stats,
    add_wishlist_item, get_wishlist_items, delete_wishlist_item, format_wishlist
)

router = Router()
logger = logging.getLogger(__name__)


class WishlistStates(StatesGroup):
    """Состояния для управления вишлистом"""
    waiting_for_item = State()
    waiting_for_delete_id = State()


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

📊 <b>Статистика:</b>
/stats - Общая статистика бота
/users - Подробная статистика пользователей  
/guests - Список подтвердивших участие

🔍 <b>Отладка:</b>
/debug_wishes - Последние поздравления

🎁 <b>Действия:</b>
/open_presents - Отправить все поздравления
/get_album - Получить собранный альбом
/get_song_requests - Предложения треков

🎁 <b>Управление вишлистом:</b>
/add_wishlist_item - Добавить элемент в вишлист
/delete_wishlist_item - Удалить элемент из вишлиста
/show_wishlist_admin - Показать вишлист с ID

⚙️ <b>Настройки:</b>
/broadcast &lt;текст&gt; - Рассылка всем пользователям
/set_start_photo yes|no - Установить стартовое фото
/get_start_photos - Показать стартовые фото
/cancel - Отменить текущую операцию
/admin - Показать это сообщение

⚠️ <b>Внимание:</b> Команды работают только для администраторов.
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


@router.message(F.text == "/guests")
async def cmd_guests_list(message: Message):
    """Показать список пользователей, подтвердивших участие"""
    if not is_admin(message.from_user.id):
        await message.answer(ADMIN_ONLY)
        return
    
    try:
        guests = await get_confirmed_guests_list()
        
        if not guests:
            await message.answer("👥 Пока никто не подтвердил участие в вечеринке")
            return
        
        text = f"👥 Подтвердили участие ({len(guests)} чел.):\n\n"
        
        for i, guest in enumerate(guests, 1):
            text += f"{i}. {guest['display_name']}\n"
            text += f"   📅 {guest['confirmed_at'][:16]}\n\n"
        
        # Разбиваем на части если слишком длинно
        if len(text) > 4000:
            parts = []
            lines = text.split('\n\n')
            current_part = f"👥 Подтвердили участие ({len(guests)} чел.):\n\n"
            
            for line in lines[1:]:  # Пропускаем заголовок
                if len(current_part + line + '\n\n') > 3800:
                    parts.append(current_part)
                    current_part = line + '\n\n'
                else:
                    current_part += line + '\n\n'
            
            if current_part.strip():
                parts.append(current_part)
            
            for part in parts:
                await message.answer(part)
        else:
            await message.answer(text)
        
        logger.info(f"Админ {message.from_user.id} запросил список гостей")
        
    except Exception as e:
        logger.error(f"Ошибка в cmd_guests_list: {e}")
        await message.answer("❌ Ошибка при получении списка гостей")


@router.message(F.text == "/users")
async def cmd_users_stats(message: Message):
    """Показать статистику всех пользователей бота"""
    if not is_admin(message.from_user.id):
        await message.answer(ADMIN_ONLY)
        return
    
    try:
        stats = await get_all_users_stats()
        
        if not stats:
            await message.answer("❌ Ошибка при получении статистики")
            return
        
        text = f"""📊 Статистика пользователей бота:

👥 Всего пользователей: {stats['total_users']}

💭 Ответы на вопрос "Помнишь Вику?":
✅ Да, помню: {stats['remembers_vika']}
❌ Нет, не помню: {stats['not_remembers_vika']}
❓ Не ответили: {stats['no_answer']}

🎉 Активность:
💌 Поздравлений отправлено: {stats['wishes_count']}
📸 Файлов в альбоме: {stats['album_files_count']}
🎵 Предложений треков: {stats['songs_count']}
👥 Подтвердили участие: {stats['confirmed_guests_count']}

📈 Процент вовлеченности:
Поздравления: {round(stats['wishes_count'] / max(stats['total_users'], 1) * 100, 1)}%
Участие: {round(stats['confirmed_guests_count'] / max(stats['total_users'], 1) * 100, 1)}%"""
        
        await message.answer(text)
        logger.info(f"Админ {message.from_user.id} запросил статистику пользователей")
        
    except Exception as e:
        logger.error(f"Ошибка в cmd_users_stats: {e}")
        await message.answer("❌ Ошибка при получении статистики")


# === УПРАВЛЕНИЕ ВИШЛИСТОМ ===

@router.message(F.text == "/add_wishlist_item")
async def cmd_add_wishlist_item(message: Message, state: FSMContext):
    """Начать добавление элемента в вишлист"""
    try:
        user_id = message.from_user.id
        
        if not is_admin(user_id):
            await message.answer(ADMIN_ONLY)
            return
        
        await message.answer(
            "🎁 Добавление элемента в вишлист\n\n"
            "Отправьте текст элемента, который нужно добавить в вишлист Вики.\n\n"
            "Используйте /cancel для отмены."
        )
        
        await state.set_state(WishlistStates.waiting_for_item)
        logger.info(f"Админ {user_id} начал добавление элемента в вишлист")
        
    except Exception as e:
        logger.error(f"Ошибка в cmd_add_wishlist_item: {e}")
        await message.answer("❌ Произошла ошибка.")


@router.message(F.text, WishlistStates.waiting_for_item)
async def handle_add_wishlist_item(message: Message, state: FSMContext):
    """Обработать добавление элемента в вишлист"""
    try:
        user_id = message.from_user.id
        
        if not is_admin(user_id):
            await message.answer(ADMIN_ONLY)
            await state.clear()
            return
        
        item_text = message.text.strip()
        
        if not item_text:
            await message.answer("❌ Текст элемента не может быть пустым. Попробуйте еще раз.")
            return
        
        success = await add_wishlist_item(item_text, user_id)
        
        if success:
            await message.answer(f"✅ Элемент добавлен в вишлист:\n\n📝 {item_text}")
            logger.info(f"Админ {user_id} добавил элемент в вишлист: {item_text}")
        else:
            await message.answer("❌ Ошибка при добавлении элемента в вишлист.")
        
        await state.clear()
        
    except Exception as e:
        logger.error(f"Ошибка в handle_add_wishlist_item: {e}")
        await message.answer("❌ Произошла ошибка при добавлении элемента.")
        await state.clear()


@router.message(F.text == "/show_wishlist_admin")
async def cmd_show_wishlist_admin(message: Message):
    """Показать вишлист с ID элементов для админа"""
    try:
        user_id = message.from_user.id
        
        if not is_admin(user_id):
            await message.answer(ADMIN_ONLY)
            return
        
        items = await get_wishlist_items()
        
        if not items:
            await message.answer("📭 Вишлист пуст.")
            return
        
        response = "🎁 <b>Вишлист Вики (админ-режим):</b>\n\n"
        
        for item_id, text, timestamp in items:
            response += f"<b>ID {item_id}:</b> {text}\n"
            response += f"📅 {timestamp[:16]}\n\n"
        
        response += f"<b>Всего элементов:</b> {len(items)}\n\n"
        response += "💡 <b>Команды:</b>\n"
        response += "/add_wishlist_item - добавить элемент\n"
        response += "/delete_wishlist_item - удалить элемент"
        
        await message.answer(response)
        
    except Exception as e:
        logger.error(f"Ошибка в cmd_show_wishlist_admin: {e}")
        await message.answer("❌ Произошла ошибка при получении вишлиста.")


@router.message(F.text == "/delete_wishlist_item")
async def cmd_delete_wishlist_item(message: Message, state: FSMContext):
    """Начать удаление элемента из вишлиста"""
    try:
        user_id = message.from_user.id
        
        if not is_admin(user_id):
            await message.answer(ADMIN_ONLY)
            return
        
        items = await get_wishlist_items()
        
        if not items:
            await message.answer("📭 Вишлист пуст - нечего удалять.")
            return
        
        response = "🗑 <b>Удаление элемента из вишлиста</b>\n\n"
        response += "Выберите ID элемента для удаления:\n\n"
        
        for item_id, text, timestamp in items:
            response += f"<b>ID {item_id}:</b> {text}\n\n"
        
        response += "Отправьте ID элемента, который нужно удалить.\n"
        response += "Используйте /cancel для отмены."
        
        await message.answer(response)
        await state.set_state(WishlistStates.waiting_for_delete_id)
        logger.info(f"Админ {user_id} начал удаление элемента из вишлиста")
        
    except Exception as e:
        logger.error(f"Ошибка в cmd_delete_wishlist_item: {e}")
        await message.answer("❌ Произошла ошибка.")


@router.message(F.text, WishlistStates.waiting_for_delete_id)
async def handle_delete_wishlist_item(message: Message, state: FSMContext):
    """Обработать удаление элемента из вишлиста"""
    try:
        user_id = message.from_user.id
        
        if not is_admin(user_id):
            await message.answer(ADMIN_ONLY)
            await state.clear()
            return
        
        try:
            item_id = int(message.text.strip())
        except ValueError:
            await message.answer("❌ Неверный формат ID. Введите числовой ID элемента.")
            return
        
        success = await delete_wishlist_item(item_id)
        
        if success:
            await message.answer(f"✅ Элемент с ID {item_id} удален из вишлиста.")
            logger.info(f"Админ {user_id} удалил элемент ID {item_id} из вишлиста")
        else:
            await message.answer(f"❌ Элемент с ID {item_id} не найден.")
        
        await state.clear()
        
    except Exception as e:
        logger.error(f"Ошибка в handle_delete_wishlist_item: {e}")
        await message.answer("❌ Произошла ошибка при удалении элемента.")
        await state.clear()


@router.message(F.text == "/cancel")
async def cmd_cancel_admin(message: Message, state: FSMContext):
    """Отменить текущую операцию админа"""
    try:
        user_id = message.from_user.id
        
        if not is_admin(user_id):
            await message.answer(ADMIN_ONLY)
            return
        
        current_state = await state.get_state()
        
        if current_state:
            await state.clear()
            await message.answer("✅ Операция отменена.")
            logger.info(f"Админ {user_id} отменил операцию в состоянии {current_state}")
        else:
            await message.answer("❌ Нет активных операций для отмены.")
        
    except Exception as e:
        logger.error(f"Ошибка в cmd_cancel_admin: {e}")
        await message.answer("❌ Произошла ошибка.")

