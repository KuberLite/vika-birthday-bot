"""
Обработка предложений треков для плейлиста
"""
import logging
from aiogram import Router, F
from aiogram.types import Message
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

from config.texts import SONG_REQUEST_SAVED
from handlers.utils import save_song_request

router = Router()
logger = logging.getLogger(__name__)


class SongStates(StatesGroup):
    """Состояния для предложения треков"""
    waiting_for_song = State()


@router.message(F.text, SongStates.waiting_for_song)
async def handle_song_request(message: Message, state: FSMContext):
    """Обработать предложение трека"""
    try:
        user_id = message.from_user.id
        track_text = message.text.strip()
        
        logger.info(f"🎵 Получен трек от пользователя {user_id}: {track_text}")
        
        # Проверяем длину
        if len(track_text) < 3:
            await message.answer("❌ Слишком короткое название. Попробуй ещё раз!")
            return
            
        if len(track_text) > 200:
            await message.answer("❌ Слишком длинное название. Попробуй покороче!")
            return
        
        # Сохраняем предложение трека
        await save_song_request(user_id, track_text)
        
        # Отправляем подтверждение
        await message.answer(
            SONG_REQUEST_SAVED.format(track=track_text)
        )
        
        # Возвращаемся в главное меню
        from handlers.menu import show_main_menu
        await show_main_menu(message, user_id)
        
        # Очищаем состояние
        await state.clear()
        
        logger.info(f"Пользователь {user_id} предложил трек: {track_text}")
        
    except Exception as e:
        logger.error(f"Ошибка в handle_song_request: {e}")
        await message.answer("❌ Произошла ошибка при сохранении предложения.")
        await state.clear()


@router.message(SongStates.waiting_for_song)
async def handle_any_song_message(message: Message, state: FSMContext):
    """Обработать любое сообщение в состоянии ожидания трека"""
    logger.info(f"🎵 DEBUG: Получено сообщение в состоянии waiting_for_song от {message.from_user.id}: {message.text}")
    await message.answer("🎵 Отправьте текстовое сообщение с названием трека.")
