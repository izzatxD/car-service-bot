from aiogram import Router, F, types
from aiogram.fsm.context import FSMContext
from aiogram.types import InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder

from config import CREATOR_ID
from db import get_all_masters
from utils.states import SearchMaster
from handlers.creator_masters import render_master_profile

router = Router()

@router.callback_query(F.data == "admin_search_master")
async def cb_search_master_start(cb: types.CallbackQuery, state: FSMContext):
    if cb.from_user.id != CREATOR_ID:
        return
    await state.set_state(SearchMaster.waiting_for_query)
    await cb.message.answer(
        "🔍 <b>Usta Qidirish</b>\n\n"
        "Ustaning <b>Telegram ID</b> raqamini yoki <b>ismini</b> kiriting:\n"
        "<i>Bekor qilish: «❌ Bekor qilish»</i>"
    )
    await cb.answer()


@router.message(SearchMaster.waiting_for_query)
async def process_search_master(message: types.Message, state: FSMContext):
    if message.from_user.id != CREATOR_ID:
        return

    query = message.text.strip()
    if query in ["❌ Bekor qilish", "🏠 Asosiy menyu", "⚙ Admin Panel"]:
        await state.clear()
        return

    await state.clear()
    masters = await get_all_masters()

    if query.isdigit():
        results = [m for m in masters if str(m['telegram_id']) == query]
    else:
        q_lower = query.lower()
        results = [
            m for m in masters
            if q_lower in (m.get('full_name') or '').lower()
            or q_lower in (m.get('username') or '').lower()
        ]

    if not results:
        builder = InlineKeyboardBuilder()
        builder.row(
            InlineKeyboardButton(text="🔍 Qayta qidirish", callback_data="admin_search_master"),
            InlineKeyboardButton(text="🔙 Dashboard",       callback_data="admin_dashboard"),
        )
        await message.answer(
            f"😕 <b>«{query}»</b> bo'yicha usta topilmadi.",
            reply_markup=builder.as_markup()
        )
        return

    if len(results) == 1:
        text, markup = await render_master_profile(results[0]['telegram_id'])
        await message.answer(text, reply_markup=markup)
        return

    text = f"🔍 <b>«{query}»</b> — {len(results)} ta natija:\n━━━━━━━━━━━━━━━━━━\n"
    builder = InlineKeyboardBuilder()
    for m in results[:20]:
        status_icon = "🟢" if m['is_active'] else "🔴"
        name = m.get('full_name') or m.get('username') or f"ID:{m['telegram_id']}"
        builder.row(
            InlineKeyboardButton(
                text=f"{status_icon} {name[:25]}",
                callback_data=f"admin_master_{m['telegram_id']}"
            )
        )
    builder.row(
        InlineKeyboardButton(text="🔍 Qayta qidirish", callback_data="admin_search_master"),
        InlineKeyboardButton(text="🔙 Dashboard",       callback_data="admin_dashboard"),
    )
    await message.answer(text, reply_markup=builder.as_markup())

