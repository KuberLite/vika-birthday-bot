"""
Обработка загрузки фото в альбом
"""
import logging
from datetime import datetime

from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

from config.texts import (
    ALBUM_INSTRUCTIONS,
    ALBUM_FILE_SAVED,
    ALBUM_LIMIT_REACHED,
    CANCEL_BUTTON,
    MAIN_MENU_BUTTON
)
from config.settings import MAX_FILES_PER_USER, ALBUM_DELAY_DAYS
from handlers.utils import add_user, is_after_birthday, get_days_until_birthday

router = Router()
logger = logging.getLogger(__name__)


class AlbumStates(StatesGroup):
    """Состояния для загрузки файлов в альбом"""
    uploading_files = State()


# Словарь для отслеживания пользователей, которые загружают файлы
album_uploaders = {}

# Словарь для отслеживания последних уведомлений (избегаем спам)
last_notifications = {}


async def start_album_upload(message: Message, user_id: int, from_user=None, state: FSMContext = None):
    """Начать загрузку файлов в альбом"""
    try:
        # Очищаем состояние поздравлений если пользователь был в процессе отправки
        from handlers.wishes import wish_collectors
        if user_id in wish_collectors:
            wish_collectors.pop(user_id, None)
            logger.info(f"📸 Очищено состояние поздравлений для пользователя {user_id}")
        
        # Временно отключаем проверку даты для тестирования
        # if not is_after_birthday():
        #     await message.answer("📸 Загрузка фото пока недоступна! Альбом откроется 25 мая 2025 года.")
        #     return
        
        # Используем from_user если передан, иначе message.from_user
        user_info = from_user or message.from_user
        
        # Добавляем пользователя в БД
        await add_user(
            user_id=user_id,
            username=user_info.username,
            first_name=user_info.first_name,
            last_name=user_info.last_name
        )
        
        # Убираем проверку лимита файлов
        # user_files_count = await get_user_files_count(user_id)
        # if user_files_count >= MAX_FILES_PER_USER:
        #     days_left = ALBUM_DELAY_DAYS - get_days_until_birthday()
        #     await message.answer(ALBUM_LIMIT_REACHED.format(days=days_left))
        #     return
        
        # Создаем клавиатуру
        builder = InlineKeyboardBuilder()
        builder.button(text=CANCEL_BUTTON, callback_data="cancel_album")
        
        # Убираем счетчик оставшихся файлов
        instructions = ALBUM_INSTRUCTIONS
        
        await message.answer(
            instructions,
            reply_markup=builder.as_markup()
        )
        
        # Отмечаем, что пользователь загружает файлы
        album_uploaders[user_id] = True
        
        # Устанавливаем состояние FSM
        if state:
            await state.set_state(AlbumStates.uploading_files)
            logger.info(f"📸 Состояние FSM установлено для пользователя {user_id}")
        
        logger.info(f"📸 Пользователь {user_id} начал загрузку в альбом, album_uploaders={album_uploaders}")
        
    except Exception as e:
        logger.error(f"Ошибка в start_album_upload: {e}")
        await message.answer("❌ Произошла ошибка. Попробуйте позже.")


@router.callback_query(F.data == "cancel_album")
async def cancel_album_upload(callback: CallbackQuery):
    """Отменить загрузку в альбом"""
    try:
        user_id = callback.from_user.id
        
        # Убираем пользователя из списка загружающих
        album_uploaders.pop(user_id, None)
        
        await callback.message.edit_text("❌ Загрузка в альбом отменена.")
        await callback.answer()
        
        logger.info(f"Пользователь {user_id} отменил загрузку в альбом")
        
    except Exception as e:
        logger.error(f"Ошибка в cancel_album_upload: {e}")
        await callback.answer("❌ Ошибка", show_alert=True)


@router.message(F.photo, AlbumStates.uploading_files)
async def handle_album_photo(message: Message, state: FSMContext):
    """Обработать фото для альбома"""
    try:
        user_id = message.from_user.id
        
        logger.info(f"📸 DEBUG: Получено фото от пользователя {user_id}, album_uploaders={album_uploaders}")
        
        # Проверяем, загружает ли пользователь файлы
        if user_id not in album_uploaders:
            logger.info(f"📸 DEBUG: Пользователь {user_id} не в списке загружающих")
            return
        
        # Получаем file_id самого большого фото
        photo = message.photo[-1]
        file_id = photo.file_id
        
        # Сохраняем файл в БД
        await save_album_file(user_id, 'photo', file_id)
        
        # Отправляем уведомление только если прошло больше 3 секунд с последнего
        import time
        current_time = time.time()
        should_notify = True
        
        if user_id in last_notifications:
            if current_time - last_notifications[user_id] < 3:  # 3 секунды
                should_notify = False
        
        if should_notify:
            # Создаем клавиатуру с кнопкой возврата в меню
            from handlers.menu import get_back_to_menu_keyboard
            
            # Просто подтверждаем сохранение
            await message.answer(
                "✅ Файл сохранен в альбом!",
                reply_markup=get_back_to_menu_keyboard()
            )
            last_notifications[user_id] = current_time
        
        logger.info(f"Пользователь {user_id} загрузил фото в альбом")
        
    except Exception as e:
        logger.error(f"Ошибка в handle_album_photo: {e}")
        await message.answer("❌ Произошла ошибка при сохранении фото.")


@router.message(F.video)
async def handle_album_video(message: Message):
    """Обработать видео для альбома"""
    try:
        user_id = message.from_user.id
        
        # Проверяем, загружает ли пользователь файлы
        if user_id not in album_uploaders:
            return
        
        # Получаем file_id видео
        file_id = message.video.file_id
        
        # Сохраняем файл в БД
        await save_album_file(user_id, 'video', file_id)
        
        # Отправляем уведомление только если прошло больше 3 секунд с последнего
        import time
        current_time = time.time()
        should_notify = True
        
        if user_id in last_notifications:
            if current_time - last_notifications[user_id] < 3:  # 3 секунды
                should_notify = False
        
        if should_notify:
            # Создаем клавиатуру с кнопкой возврата в меню
            from handlers.menu import get_back_to_menu_keyboard
            
            # Просто подтверждаем сохранение
            await message.answer(
                "✅ Файл сохранен в альбом!",
                reply_markup=get_back_to_menu_keyboard()
            )
            last_notifications[user_id] = current_time
        
        logger.info(f"Пользователь {user_id} загрузил видео в альбом")
        
    except Exception as e:
        logger.error(f"Ошибка в handle_album_video: {e}")
        await message.answer("❌ Произошла ошибка при сохранении видео.")


@router.message(F.voice)
async def handle_album_voice(message: Message):
    """Обработать голосовое сообщение для альбома"""
    try:
        user_id = message.from_user.id
        
        # Проверяем, загружает ли пользователь файлы
        if user_id not in album_uploaders:
            return
        
        # Получаем file_id голосового сообщения
        file_id = message.voice.file_id
        
        # Сохраняем файл в БД
        await save_album_file(user_id, 'voice', file_id)
        
        # Отправляем уведомление только если прошло больше 3 секунд с последнего
        import time
        current_time = time.time()
        should_notify = True
        
        if user_id in last_notifications:
            if current_time - last_notifications[user_id] < 3:  # 3 секунды
                should_notify = False
        
        if should_notify:
            # Создаем клавиатуру с кнопкой возврата в меню
            from handlers.menu import get_back_to_menu_keyboard
            
            # Просто подтверждаем сохранение
            await message.answer(
                "✅ Файл сохранен в альбом!",
                reply_markup=get_back_to_menu_keyboard()
            )
            last_notifications[user_id] = current_time
        
        logger.info(f"Пользователь {user_id} загрузил голосовое в альбом")
        
    except Exception as e:
        logger.error(f"Ошибка в handle_album_voice: {e}")
        await message.answer("❌ Произошла ошибка при сохранении голосового сообщения.")


async def get_user_files_count(user_id: int) -> int:
    """Получить количество файлов пользователя в альбоме"""
    try:
        import aiosqlite
        from config.settings import DATABASE_PATH
        
        async with aiosqlite.connect(DATABASE_PATH) as db:
            async with db.execute("""
                SELECT COUNT(*) FROM album_files WHERE user_id = ?
            """, (user_id,)) as cursor:
                row = await cursor.fetchone()
                return row[0] if row else 0
                
    except Exception as e:
        logger.error(f"Ошибка получения количества файлов: {e}")
        return 0


async def save_album_file(user_id: int, file_type: str, file_id: str):
    """Сохранить файл альбома в БД"""
    try:
        import aiosqlite
        from config.settings import DATABASE_PATH
        
        async with aiosqlite.connect(DATABASE_PATH) as db:
            await db.execute("""
                INSERT INTO album_files (user_id, file_id, file_type)
                VALUES (?, ?, ?)
            """, (user_id, file_id, file_type))
            await db.commit()
            
    except Exception as e:
        logger.error(f"Ошибка сохранения файла альбома: {e}")
        raise


@router.message(Command("cancel"))
async def cmd_cancel_album(message: Message):
    """Команда отмены загрузки в альбом"""
    try:
        user_id = message.from_user.id
        
        # Убираем пользователя из списка загружающих
        if user_id in album_uploaders:
            album_uploaders.pop(user_id, None)
            await message.answer("❌ Загрузка в альбом отменена.")
        else:
            await message.answer("❌ Нет активных операций для отмены.")
        
    except Exception as e:
        logger.error(f"Ошибка в cmd_cancel_album: {e}")
        await message.answer("❌ Произошла ошибка.")

