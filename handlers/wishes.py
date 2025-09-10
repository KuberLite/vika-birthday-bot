"""
Обработка тайных поздравлений
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
    WISH_INSTRUCTIONS,
    WISH_SAVED,
    WISH_CANCELLED,
    CANCEL_BUTTON,
    MAIN_MENU_BUTTON
)
from handlers.utils import add_user, is_archive_mode

router = Router()
logger = logging.getLogger(__name__)


class WishStates(StatesGroup):
    """Состояния для отправки поздравлений"""
    waiting_for_wish = State()


# Словарь для отслеживания пользователей, которые отправляют поздравления
wish_collectors = {}


async def start_wish_collection(message: Message, user_id: int, from_user=None, state: FSMContext = None):
    """Начать сбор поздравления"""
    try:
        # Очищаем состояние альбома если пользователь был в процессе загрузки
        from handlers.album import album_uploaders
        if user_id in album_uploaders:
            album_uploaders.pop(user_id, None)
            logger.info(f"💌 Очищено состояние альбома для пользователя {user_id}")
        
        # Проверяем архивный режим
        if is_archive_mode():
            await message.answer("📦 Функция поздравлений недоступна в архивном режиме.")
            return
        
        # Используем from_user если передан, иначе message.from_user
        user_info = from_user or message.from_user
        
        # Добавляем пользователя в БД
        await add_user(
            user_id=user_id,
            username=user_info.username,
            first_name=user_info.first_name,
            last_name=user_info.last_name
        )
        
        # Создаем клавиатуру
        builder = InlineKeyboardBuilder()
        builder.button(text=CANCEL_BUTTON, callback_data="cancel_wish")
        
        await message.answer(
            WISH_INSTRUCTIONS,
            reply_markup=builder.as_markup()
        )
        
        # Отмечаем, что пользователь собирает поздравление
        wish_collectors[user_id] = True
        
        # Устанавливаем состояние FSM
        if state:
            await state.set_state(WishStates.waiting_for_wish)
            logger.info(f"💌 Состояние FSM установлено для пользователя {user_id}")
        
        logger.info(f"Пользователь {user_id} начал отправку поздравления")
        
    except Exception as e:
        logger.error(f"Ошибка в start_wish_collection: {e}")
        await message.answer("❌ Произошла ошибка. Попробуйте позже.")


@router.callback_query(F.data == "cancel_wish")
async def cancel_wish(callback: CallbackQuery):
    """Отменить отправку поздравления"""
    try:
        user_id = callback.from_user.id
        
        # Убираем пользователя из списка собирающих поздравления
        wish_collectors.pop(user_id, None)
        
        # Создаем клавиатуру с кнопкой возврата в меню
        from handlers.menu import get_back_to_menu_keyboard
        
        await callback.message.edit_text(
            WISH_CANCELLED,
            reply_markup=get_back_to_menu_keyboard()
        )
        await callback.answer()
        
        logger.info(f"Пользователь {user_id} отменил отправку поздравления")
        
    except Exception as e:
        logger.error(f"Ошибка в cancel_wish: {e}")
        await callback.answer("❌ Ошибка", show_alert=True)


@router.message(F.text, WishStates.waiting_for_wish)
async def handle_text_wish(message: Message, state: FSMContext):
    """Обработать текстовое поздравление"""
    try:
        user_id = message.from_user.id
        
        # Проверяем, собирает ли пользователь поздравление
        if user_id not in wish_collectors:
            return
        
        # Сохраняем поздравление в БД
        logger.info(f"🔍 DEBUG: Сохраняем поздравление от user_id={user_id}, from_user_id={message.from_user.id}")
        await save_wish(user_id, 'text', message.text)
        
        # Убираем пользователя из списка собирающих
        wish_collectors.pop(user_id, None)
        
        # Очищаем состояние FSM
        await state.clear()
        
        # Создаем клавиатуру с кнопкой возврата в меню
        from handlers.menu import get_back_to_menu_keyboard
        
        await message.answer(
            WISH_SAVED,
            reply_markup=get_back_to_menu_keyboard()
        )
        
        logger.info(f"Пользователь {user_id} отправил текстовое поздравление")
        
    except Exception as e:
        logger.error(f"Ошибка в handle_text_wish: {e}")
        await message.answer("❌ Произошла ошибка при сохранении поздравления.")


@router.message(F.photo, WishStates.waiting_for_wish)
async def handle_photo_wish(message: Message, state: FSMContext):
    """Обработать поздравление с фото"""
    try:
        user_id = message.from_user.id
        
        # Проверяем, собирает ли пользователь поздравление
        if user_id not in wish_collectors:
            return
        
        # Получаем file_id самого большого фото
        photo = message.photo[-1]
        file_id = photo.file_id
        
        # Сохраняем поздравление в БД
        await save_wish(user_id, 'photo', file_id)
        
        # Убираем пользователя из списка собирающих
        wish_collectors.pop(user_id, None)
        
        # Создаем клавиатуру с кнопкой возврата в меню
        from handlers.menu import get_back_to_menu_keyboard
        
        await message.answer(
            WISH_SAVED,
            reply_markup=get_back_to_menu_keyboard()
        )
        
        logger.info(f"Пользователь {user_id} отправил поздравление с фото")
        
    except Exception as e:
        logger.error(f"Ошибка в handle_photo_wish: {e}")
        await message.answer("❌ Произошла ошибка при сохранении поздравления.")


@router.message(F.video, WishStates.waiting_for_wish)
async def handle_video_wish(message: Message, state: FSMContext):
    """Обработать поздравление с видео"""
    try:
        user_id = message.from_user.id
        
        # Проверяем, собирает ли пользователь поздравление
        if user_id not in wish_collectors:
            return
        
        file_id = message.video.file_id
        
        # Сохраняем поздравление в БД
        await save_wish(user_id, 'video', file_id)
        
        # Убираем пользователя из списка собирающих
        wish_collectors.pop(user_id, None)
        
        # Создаем клавиатуру с кнопкой возврата в меню
        from handlers.menu import get_back_to_menu_keyboard
        
        await message.answer(
            WISH_SAVED,
            reply_markup=get_back_to_menu_keyboard()
        )
        
        logger.info(f"Пользователь {user_id} отправил поздравление с видео")
        
    except Exception as e:
        logger.error(f"Ошибка в handle_video_wish: {e}")
        await message.answer("❌ Произошла ошибка при сохранении поздравления.")


@router.message(F.voice, WishStates.waiting_for_wish)
async def handle_voice_wish(message: Message, state: FSMContext):
    """Обработать голосовое поздравление"""
    try:
        user_id = message.from_user.id
        
        # Проверяем, собирает ли пользователь поздравление
        if user_id not in wish_collectors:
            return
        
        file_id = message.voice.file_id
        
        # Сохраняем поздравление в БД
        await save_wish(user_id, 'voice', file_id)
        
        # Убираем пользователя из списка собирающих
        wish_collectors.pop(user_id, None)
        
        # Создаем клавиатуру с кнопкой возврата в меню
        from handlers.menu import get_back_to_menu_keyboard
        
        await message.answer(
            WISH_SAVED,
            reply_markup=get_back_to_menu_keyboard()
        )
        
        logger.info(f"Пользователь {user_id} отправил голосовое поздравление")
        
    except Exception as e:
        logger.error(f"Ошибка в handle_voice_wish: {e}")
        await message.answer("❌ Произошла ошибка при сохранении поздравления.")


@router.message(F.sticker, WishStates.waiting_for_wish)
async def handle_sticker_wish(message: Message, state: FSMContext):
    """Обработать поздравление со стикером"""
    try:
        user_id = message.from_user.id
        
        # Проверяем, собирает ли пользователь поздравление
        if user_id not in wish_collectors:
            return
        
        file_id = message.sticker.file_id
        
        # Сохраняем поздравление в БД
        await save_wish(user_id, 'sticker', file_id)
        
        # Убираем пользователя из списка собирающих
        wish_collectors.pop(user_id, None)
        
        # Создаем клавиатуру с кнопкой возврата в меню
        from handlers.menu import get_back_to_menu_keyboard
        
        await message.answer(
            WISH_SAVED,
            reply_markup=get_back_to_menu_keyboard()
        )
        
        logger.info(f"Пользователь {user_id} отправил поздравление со стикером")
        
    except Exception as e:
        logger.error(f"Ошибка в handle_sticker_wish: {e}")
        await message.answer("❌ Произошла ошибка при сохранении поздравления.")


async def save_wish(user_id: int, content_type: str, content: str):
    """Сохранить поздравление в БД"""
    try:
        import aiosqlite
        from config.settings import DATABASE_PATH
        
        async with aiosqlite.connect(DATABASE_PATH) as db:
            await db.execute("""
                INSERT INTO wishes (user_id, content_type, content, is_anonymous, delivered)
                VALUES (?, ?, ?, 0, 0)
            """, (user_id, content_type, content))
            await db.commit()
            
    except Exception as e:
        logger.error(f"Ошибка сохранения поздравления: {e}")
        raise


@router.message(Command("cancel"))
async def cmd_cancel(message: Message):
    """Команда отмены"""
    try:
        user_id = message.from_user.id
        
        # Убираем пользователя из списка собирающих поздравления
        if user_id in wish_collectors:
            wish_collectors.pop(user_id, None)
            
            # Создаем клавиатуру с кнопкой возврата в меню
            from handlers.menu import get_back_to_menu_keyboard
            
            await message.answer(
                WISH_CANCELLED,
                reply_markup=get_back_to_menu_keyboard()
            )
        else:
            await message.answer("❌ Нет активных операций для отмены.")
        
    except Exception as e:
        logger.error(f"Ошибка в cmd_cancel: {e}")
        await message.answer("❌ Произошла ошибка.")

