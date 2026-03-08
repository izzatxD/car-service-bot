from aiogram.types import InlineKeyboardMarkup, CallbackQuery
from aiogram.exceptions import TelegramBadRequest

async def _safe_edit(cb: CallbackQuery, text: str, markup: InlineKeyboardMarkup):
    try:
        await cb.message.edit_text(text, reply_markup=markup)
    except TelegramBadRequest:
        pass
    finally:
        await cb.answer()

def _bar(value: int, max_value: int, length: int = 8) -> str:
    if max_value == 0:
        return "░" * length
    filled = round(value / max_value * length)
    return "█" * filled + "░" * (length - filled)
