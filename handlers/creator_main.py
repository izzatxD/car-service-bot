from aiogram import Router, F, types
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder

from config import CREATOR_ID
from db import get_daily_stats, get_monthly_stats, get_all_masters
from handlers.creator_utils import _safe_edit

router = Router()

async def render_dashboard() -> tuple[str, InlineKeyboardMarkup]:
    global_daily  = await get_daily_stats()
    global_monthly = await get_monthly_stats()
    masters = await get_all_masters()

    active_masters = sum(1 for m in masters if m['is_active'])
    blocked_masters = len(masters) - active_masters

    text = (
        "⚙️ <b>ADMIN PANEL</b>\n"
        "━━━━━━━━━━━━━━━━━━\n"
        "📅 <b>Bugun:</b>\n"
        f"  📥 Qabul: <b>{global_daily['received_count']}</b>  "
        f"  ✅ Topshirildi: <b>{global_daily['completed_count']}</b>\n"
        f"  💰 Tushum: <b>{global_daily['completed_total']:,.0f} so'm</b>\n\n"
        "📆 <b>Shu oy:</b>\n"
        f"  📦 Faol buyurtmalar: <b>{global_monthly.get('active_count', 0)}</b>\n"
        f"  💰 Tushum: <b>{global_monthly['completed_total']:,.0f} so'm</b>\n\n"
        f"👨‍🔧 <b>Ustalar:</b>  🟢 Faol: <b>{active_masters}</b>  🔴 Bloklangan: <b>{blocked_masters}</b>  │ Jami: <b>{len(masters)}</b>\n"
    )

    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="👨‍🔧 Ustalar ro'yxati", callback_data="admin_masters_page_0"),
        InlineKeyboardButton(text="🔍 Usta qidirish",      callback_data="admin_search_master"),
    )
    builder.row(
        InlineKeyboardButton(text="📊 Analitika",    callback_data="admin_analytics"),
        InlineKeyboardButton(text="📦 Faol Ishlar",  callback_data="admin_orders_all"),
    )
    builder.row(
        InlineKeyboardButton(text="📤 Excel Eksport", callback_data="admin_export_xlsx"),
        InlineKeyboardButton(text="➕ Usta qo'shish",  callback_data="admin_add_master"),
    )
    builder.row(
        InlineKeyboardButton(text="📢 Barchaga xabar yuborish", callback_data="admin_broadcast"),
    )

    return text, builder.as_markup()

@router.message(F.text == "⚙ Admin Panel")
async def open_admin_dashboard(message: types.Message):
    if message.from_user.id != CREATOR_ID:
        return
    text, markup = await render_dashboard()
    await message.answer(text, reply_markup=markup)

@router.callback_query(F.data == "admin_dashboard")
async def cb_admin_dashboard(cb: types.CallbackQuery):
    if cb.from_user.id != CREATOR_ID:
        return
    text, markup = await render_dashboard()
    await _safe_edit(cb, text, markup)

@router.callback_query(F.data == "admin_noop")
async def cb_noop(cb: types.CallbackQuery):
    await cb.answer()

