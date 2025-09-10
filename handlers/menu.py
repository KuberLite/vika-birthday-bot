"""
Главное меню бота
"""
import logging
from datetime import datetime

from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.fsm.context import FSMContext

from config.texts import (
    MAIN_MENU_MESSAGE,
    MAIN_MENU_BUTTONS,
    PARTY_LOCATION,
    PARTY_TIME,
    WHAT_TO_BRING,
    WISHLIST,
    ALBUM_NOT_READY,
    ARCHIVE_MODE,
    GUEST_CONFIRMED,
    GUEST_ALREADY_CONFIRMED
)
from handlers.utils import (
    get_days_until_birthday,
    is_archive_mode,
    is_after_birthday,
    get_guest_count,
    confirm_guest_participation,
    is_guest_confirmed
)

router = Router()
logger = logging.getLogger(__name__)


def get_back_to_menu_keyboard():
    """Создать клавиатуру с кнопкой 'Назад в меню'"""
    builder = InlineKeyboardBuilder()
    builder.button(text="🏠 Назад в меню", callback_data="back_to_menu")
    return builder.as_markup()


async def show_main_menu(message: Message, user_id: int):
    """Показать главное меню"""
    try:
        # Проверяем архивный режим
        if is_archive_mode():
            await message.answer(ARCHIVE_MODE)
            return
        
        # Получаем количество дней до дня рождения
        days_left = get_days_until_birthday()
        
        # Создаем клавиатуру с обновленным таймером
        builder = InlineKeyboardBuilder()
        
        for row in MAIN_MENU_BUTTONS:
            for button_text in row:
                # Заменяем плейсхолдер для таймера
                if "{days}" in button_text:
                    button_text = button_text.format(days=days_left)
                
                # Определяем callback_data для каждой кнопки
                if "Где будет тусовка?" in button_text:
                    builder.button(text=button_text, callback_data="party_location")
                elif "Во сколько начало?" in button_text:
                    builder.button(text=button_text, callback_data="party_time")
                elif "Что взять с собой?" in button_text:
                    builder.button(text=button_text, callback_data="what_to_bring")
                elif "Вишлист" in button_text:
                    builder.button(text=button_text, callback_data="wishlist")
                elif "Поздравить Вику" in button_text:
                    builder.button(text=button_text, callback_data="send_wish")
                elif "фотки" in button_text:
                    if is_after_birthday():
                        builder.button(text=button_text, callback_data="upload_photos")
                    else:
                        builder.button(text=button_text, callback_data="album_not_ready")
                elif "Вика-гадалка" in button_text:
                    builder.button(text=button_text, callback_data="fortune")
                elif "Я буду" in button_text:
                    builder.button(text=button_text, callback_data="confirm_attendance")
                elif "Предложить трек" in button_text or "караоке" in button_text:
                    builder.button(text=button_text, callback_data="song_request")
                elif "До ДР:" in button_text:
                    builder.button(text=button_text, callback_data="birthday_timer")
        
        builder.adjust(2)
        
        await message.answer(
            MAIN_MENU_MESSAGE,
            reply_markup=builder.as_markup()
        )
        
    except Exception as e:
        logger.error(f"Ошибка в show_main_menu: {e}")
        await message.answer("❌ Произошла ошибка при загрузке меню")


@router.callback_query(F.data == "party_location")
async def show_party_location(callback: CallbackQuery):
    """Показать информацию о месте проведения"""
    try:
        # Удаляем предыдущее сообщение
        await callback.message.delete()
        
        # Отправляем карту
        await callback.message.answer_location(
            latitude=53.832189,
            longitude=27.537568
        )
        
        # Отправляем текст с адресом и кнопкой "Назад"
        await callback.message.answer(
            PARTY_LOCATION,
            reply_markup=get_back_to_menu_keyboard()
        )
        
        await callback.answer()
    except Exception as e:
        logger.error(f"Ошибка в show_party_location: {e}")
        await callback.answer("❌ Ошибка", show_alert=True)


@router.callback_query(F.data == "party_time")
async def show_party_time(callback: CallbackQuery):
    """Показать время проведения"""
    try:
        await callback.message.edit_text(
            PARTY_TIME,
            reply_markup=get_back_to_menu_keyboard()
        )
        await callback.answer()
    except Exception as e:
        logger.error(f"Ошибка в show_party_time: {e}")
        await callback.answer("❌ Ошибка", show_alert=True)


@router.callback_query(F.data == "what_to_bring")
async def show_what_to_bring(callback: CallbackQuery):
    """Показать что взять с собой"""
    try:
        await callback.message.edit_text(
            WHAT_TO_BRING,
            reply_markup=get_back_to_menu_keyboard()
        )
        await callback.answer()
    except Exception as e:
        logger.error(f"Ошибка в show_what_to_bring: {e}")
        await callback.answer("❌ Ошибка", show_alert=True)


@router.callback_query(F.data == "wishlist")
async def show_wishlist(callback: CallbackQuery):
    """Показать вишлист"""
    try:
        await callback.message.edit_text(
            WISHLIST,
            reply_markup=get_back_to_menu_keyboard()
        )
        await callback.answer()
    except Exception as e:
        logger.error(f"Ошибка в show_wishlist: {e}")
        await callback.answer("❌ Ошибка", show_alert=True)


@router.callback_query(F.data == "send_wish")
async def start_send_wish(callback: CallbackQuery, state: FSMContext):
    """Начать отправку поздравления"""
    try:
        # Импортируем здесь, чтобы избежать циклических импортов
        from handlers.wishes import start_wish_collection
        
        await start_wish_collection(callback.message, callback.from_user.id, callback.from_user, state)
        await callback.answer()
    except Exception as e:
        logger.error(f"Ошибка в start_send_wish: {e}")
        await callback.answer("❌ Ошибка", show_alert=True)


@router.callback_query(F.data == "album_not_ready")
async def show_album_not_ready(callback: CallbackQuery):
    """Показать что альбом еще не готов"""
    try:
        await callback.message.edit_text(
            ALBUM_NOT_READY,
            reply_markup=get_back_to_menu_keyboard()
        )
        await callback.answer()
    except Exception as e:
        logger.error(f"Ошибка в show_album_not_ready: {e}")
        await callback.answer("❌ Ошибка", show_alert=True)


@router.callback_query(F.data == "upload_photos")
async def start_upload_photos(callback: CallbackQuery, state: FSMContext):
    """Начать загрузку фото"""
    try:
        logger.info(f"📸 DEBUG: Нажата кнопка upload_photos от пользователя {callback.from_user.id}")
        
        # Импортируем здесь, чтобы избежать циклических импортов
        from handlers.album import start_album_upload
        
        await start_album_upload(callback.message, callback.from_user.id, callback.from_user, state)
        await callback.answer()
        
        logger.info(f"📸 DEBUG: start_album_upload завершен для пользователя {callback.from_user.id}")
    except Exception as e:
        logger.error(f"Ошибка в start_upload_photos: {e}")
        await callback.answer("❌ Ошибка", show_alert=True)


@router.callback_query(F.data == "fortune")
async def show_fortune(callback: CallbackQuery):
    """Показать гадание"""
    try:
        # Импортируем здесь, чтобы избежать циклических импортов
        from handlers.utils import get_random_fortune
        
        fortune = get_random_fortune()
        await callback.message.edit_text(
            fortune,
            reply_markup=get_back_to_menu_keyboard()
        )
        await callback.answer()
    except Exception as e:
        logger.error(f"Ошибка в show_fortune: {e}")
        await callback.answer("❌ Ошибка", show_alert=True)


@router.callback_query(F.data == "confirm_attendance")
async def confirm_attendance(callback: CallbackQuery):
    """Подтвердить участие в вечеринке"""
    try:
        user_id = callback.from_user.id
        
        # Проверяем, подтвердил ли уже пользователь участие
        already_confirmed = await is_guest_confirmed(user_id)
        count = await get_guest_count()
        
        if already_confirmed:
            # Пользователь уже подтвердил участие
            message_text = GUEST_ALREADY_CONFIRMED.format(count=count)
        else:
            # Новое подтверждение
            success = await confirm_guest_participation(user_id)
            if success:
                count = await get_guest_count()  # Обновляем счетчик
                message_text = GUEST_CONFIRMED.format(count=count)
                logger.info(f"Пользователь {user_id} подтвердил участие в вечеринке")
            else:
                message_text = "❌ Произошла ошибка при подтверждении участия"
        
        await callback.message.edit_text(
            message_text,
            reply_markup=get_back_to_menu_keyboard()
        )
        await callback.answer()
        
    except Exception as e:
        logger.error(f"Ошибка в confirm_attendance: {e}")
        await callback.answer("❌ Ошибка", show_alert=True)


@router.callback_query(F.data == "song_request")
async def show_song_request(callback: CallbackQuery, state: FSMContext):
    """Показать форму для предложения трека"""
    try:
        logger.info(f"🎵 Обработка song_request от пользователя {callback.from_user.id}")
        
        from config.texts import SONG_REQUEST
        from handlers.songs import SongStates
        
        await callback.message.edit_text(
            SONG_REQUEST,
            reply_markup=get_back_to_menu_keyboard()
        )
        
        # Устанавливаем состояние ожидания трека
        await state.set_state(SongStates.waiting_for_song)
        logger.info(f"🎵 Состояние установлено для пользователя {callback.from_user.id}")
        
        await callback.answer()
    except Exception as e:
        logger.error(f"Ошибка в show_song_request: {e}")
        await callback.answer("❌ Ошибка", show_alert=True)


@router.callback_query(F.data == "back_to_menu")
async def handle_back_to_menu(callback: CallbackQuery, state: FSMContext):
    """Обработать возврат в главное меню"""
    try:
        # Очищаем состояние при возврате в меню
        await state.clear()
        await show_main_menu(callback.message, callback.from_user.id)
        await callback.answer()
    except Exception as e:
        logger.error(f"Ошибка в handle_back_to_menu: {e}")
        await callback.answer("❌ Ошибка", show_alert=True)


@router.callback_query(F.data == "birthday_timer")
async def show_birthday_timer(callback: CallbackQuery):
    """Показать таймер до дня рождения"""
    try:
        days_left = get_days_until_birthday()
        
        if days_left > 0:
            message_text = f"⏳ До дня рождения Вики осталось: {days_left} дней! 🎂"
        elif days_left == 0:
            message_text = "🎉 Сегодня день рождения Вики! 🎂🎉"
        else:
            message_text = f"🎂 День рождения Вики был {abs(days_left)} дней назад! 🎉"
        
        await callback.message.edit_text(
            message_text,
            reply_markup=get_back_to_menu_keyboard()
        )
        await callback.answer()
    except Exception as e:
        logger.error(f"Ошибка в show_birthday_timer: {e}")
        await callback.answer("❌ Ошибка", show_alert=True)


@router.callback_query(F.data == "main_menu")
async def back_to_main_menu(callback: CallbackQuery):
    """Вернуться в главное меню"""
    try:
        await show_main_menu(callback.message, callback.from_user.id)
        await callback.answer()
    except Exception as e:
        logger.error(f"Ошибка в back_to_main_menu: {e}")
        await callback.answer("❌ Ошибка", show_alert=True)