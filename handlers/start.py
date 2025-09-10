"""
Стартовый сценарий бота
"""
import logging
from datetime import datetime

from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import CommandStart
from aiogram.utils.keyboard import InlineKeyboardBuilder

from config.texts import (
    START_MESSAGE, 
    REMEMBER_VIKA_MESSAGE, 
    DONT_REMEMBER_VIKA_MESSAGE,
    START_BUTTONS
)
from handlers.utils import is_archive_mode, save_user_choice, add_user

router = Router()
logger = logging.getLogger(__name__)


@router.message(CommandStart())
async def cmd_start(message: Message):
    """Обработчик команды /start"""
    try:
        user_id = message.from_user.id
        
        # Проверяем архивный режим
        if is_archive_mode():
            await message.answer("📦 Бот в архивном режиме. Доступны только базовые функции.")
            return
        
        # Создаем клавиатуру
        builder = InlineKeyboardBuilder()
        for row in START_BUTTONS:
            for button_text in row:
                if button_text == "✅ Да, конечно!":
                    builder.button(text=button_text, callback_data="remember_vika")
                elif button_text == "❌ Нет, не помню":
                    builder.button(text=button_text, callback_data="dont_remember_vika")
        
        builder.adjust(2)
        
        await message.answer(
            START_MESSAGE,
            reply_markup=builder.as_markup()
        )
        
        logger.info(f"Пользователь {user_id} запустил бота")
        
    except Exception as e:
        logger.error(f"Ошибка в cmd_start: {e}")
        await message.answer("❌ Произошла ошибка. Попробуйте позже.")


@router.callback_query(F.data == "remember_vika")
async def remember_vika(callback: CallbackQuery):
    """Пользователь помнит Вику"""
    try:
        user_id = callback.from_user.id
        user = callback.from_user
        
        # Добавляем/обновляем пользователя в БД
        await add_user(
            user_id=user_id,
            username=user.username,
            first_name=user.first_name,
            last_name=user.last_name
        )
        
        # Сохраняем выбор пользователя
        await save_user_choice(user_id, True)
        
        # Счетчик гостей теперь не увеличивается автоматически
        # Нужно нажать кнопку "Я буду!" в главном меню
        
        # Импортируем здесь, чтобы избежать циклических импортов
        from handlers.menu import show_main_menu
        from handlers.utils import get_start_photo
        
        # Получаем фото для ответа "да"
        file_id, caption = await get_start_photo("yes")
        
        if file_id:
            # Отправляем фото с подписью
            await callback.message.delete()
            sent_message = await callback.message.answer_photo(
                photo=file_id,
                caption=caption or REMEMBER_VIKA_MESSAGE
            )
            await show_main_menu(sent_message, user_id)
        else:
            # Если фото нет, редактируем текст и показываем меню
            await callback.message.edit_text(REMEMBER_VIKA_MESSAGE)
            await show_main_menu(callback.message, user_id)
        
        await callback.answer()
        logger.info(f"Пользователь {user_id} помнит Вику")
        
    except Exception as e:
        logger.error(f"Ошибка в remember_vika: {e}")
        await callback.answer("❌ Произошла ошибка", show_alert=True)


@router.callback_query(F.data == "dont_remember_vika")
async def dont_remember_vika(callback: CallbackQuery):
    """Пользователь не помнит Вику"""
    try:
        user_id = callback.from_user.id
        user = callback.from_user
        
        # Добавляем/обновляем пользователя в БД
        await add_user(
            user_id=user_id,
            username=user.username,
            first_name=user.first_name,
            last_name=user.last_name
        )
        
        # Сохраняем выбор пользователя
        await save_user_choice(user_id, False)
        
        # Импортируем здесь, чтобы избежать циклических импортов
        from handlers.menu import show_main_menu
        from handlers.utils import get_start_photo
        
        # Получаем фото для ответа "нет"
        file_id, caption = await get_start_photo("no")
        
        if file_id:
            # Отправляем фото с подписью
            await callback.message.delete()
            sent_message = await callback.message.answer_photo(
                photo=file_id,
                caption=caption or DONT_REMEMBER_VIKA_MESSAGE
            )
            await show_main_menu(sent_message, user_id)
        else:
            # Если фото нет, редактируем текст и показываем меню
            await callback.message.edit_text(DONT_REMEMBER_VIKA_MESSAGE)
            await show_main_menu(callback.message, user_id)
        
        await callback.answer()
        logger.info(f"Пользователь {user_id} не помнил Вику")
        
    except Exception as e:
        logger.error(f"Ошибка в dont_remember_vika: {e}")
        await callback.answer("❌ Произошла ошибка", show_alert=True)

