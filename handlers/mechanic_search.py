import logging
from aiogram import Router, F, types
from aiogram.fsm.context import FSMContext

from config import CREATOR_ID
from db import search_orders, fmt_dt
from utils.states import SearchState
from keyboards.mechanic_kb import main_menu_kb, cancel_kb

logger = logging.getLogger(__name__)
router = Router()

# ═══════════════════════════════════════════════
#  🔍 QIDIRUV VA MIJOZ TARIXI
# ═══════════════════════════════════════════════
@router.message(F.text == "🔍 Qidiruv")
async def search_start(message: types.Message, state: FSMContext):
    await state.set_state(SearchState.query)
    await message.answer(
        "🔍 <b>Qidiruv</b>\n\n"
        "Mijozni quyidagilar bo'yicha izlashingiz mumkin:\n"
        "👤 Ism yoki raqam\n"
        "🚗 Model yoki Davlat raqami\n"
        "📅 Sana: <code>15.03</code> yoki <code>15 mart</code>\n"
        "🗓 Oy: <code>mart</code> yoki <code>03</code>", 
        reply_markup=cancel_kb()
    )

@router.message(SearchState.query)
async def search_process(message: types.Message, state: FSMContext):
    query = message.text.strip()
    
    master_id = None if message.from_user.id == CREATOR_ID else message.from_user.id
    results = await search_orders(query, master_id=master_id)

    if not results:
        await message.answer(f"😕 <b>«{query}»</b> bo'yicha hech narsa topilmadi.", reply_markup=main_menu_kb(message.from_user.id))
        await state.clear()
        return

    text = f"🔍 <b>«{query}»</b> bo'yicha tarix:\n━━━━━━━━━━━━━━━━━━━━━━\n\n"
    for o in results:
        st = o['status'].upper()
        if st == "TOP_SHIRILDI": st = "TOPSHIRILDI 📦"
        completed_line = f"   ✅ Topshirildi: {fmt_dt(o['completed_at'])}\n" if o.get('completed_at') else ""
        text += (
            f"<b>#{o['id']}</b> — {o['client_name']} ({st})\n"
            f"   🚗 {o['car_model']} | 🔧 {o['problem']}\n"
            f"   📞 {o['client_phone']} | 💰 {o['price']:,.0f} so'm\n"
            f"   📅 Qabul: {fmt_dt(o['created_at'])}\n"
            f"{completed_line}\n"
        )
    await message.answer(text, reply_markup=main_menu_kb(message.from_user.id))
    await state.clear()

