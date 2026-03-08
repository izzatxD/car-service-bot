import logging
from aiogram import Router, F, types
from aiogram.fsm.context import FSMContext
from keyboards.mechanic_kb import main_menu_kb

logger = logging.getLogger(__name__)
router = Router()

# ═══════════════════════════════════════════════
#  ❌ Bekor qilish / Qaytish
# ═══════════════════════════════════════════════
@router.message(F.text == "❌ Bekor qilish")
@router.message(F.text == "🏠 Asosiy menyu")
async def cancel_handler(message: types.Message, state: FSMContext):
    await state.clear()
    await message.answer(
        "🏠 Asosiy menyu:",
        reply_markup=main_menu_kb(message.from_user.id),
    )

