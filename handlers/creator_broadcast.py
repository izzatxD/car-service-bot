from aiogram import Router, F, types
from aiogram.fsm.context import FSMContext

from config import CREATOR_ID
from db import get_all_masters
from utils.states import BroadcastState

router = Router()

@router.callback_query(F.data == "admin_broadcast")
async def cb_admin_broadcast_start(cb: types.CallbackQuery, state: FSMContext):
    if cb.from_user.id != CREATOR_ID:
        return
        
    await state.set_state(BroadcastState.waiting_for_message)
    await cb.message.answer(
        "📢 <b>Barcha ustalarga xabar yuborish</b>\n\n"
        "Yubormoqchi bo'lgan xabaringizni yozing yoki rasm/video jo'nating.\n"
        "<i>Bekor qilish: «❌ Bekor qilish»</i>"
    )
    await cb.answer()

@router.message(BroadcastState.waiting_for_message)
async def process_broadcast_message(message: types.Message, state: FSMContext):
    if message.from_user.id != CREATOR_ID:
        return
        
    if message.text in ["❌ Bekor qilish", "🏠 Asosiy menyu", "⚙ Admin Panel"]:
        await state.clear()
        return await message.answer("❌ Xabar yuborish bekor qilindi.")
        
    masters = await get_all_masters()
    active_masters = [m for m in masters if m['is_active']]
    
    if not active_masters:
        await state.clear()
        return await message.answer("⚠️ Baza bo'sh yoki faol ustalar topilmadi.")
        
    sent_count = 0
    await message.answer("⏳ Xabarlar yuborilmoqda, kuting...")
    
    for m in active_masters:
        try:
            await message.copy_to(chat_id=m['telegram_id'])
            sent_count += 1
        except Exception:
            pass
            
    await state.clear()
    await message.answer(
        f"✅ <b>Xabar yuborish yakunlandi!</b>\n"
        f"Jami yuborildi: {sent_count} ta ustaga (Mavjud: {len(active_masters)} ta)"
    )

