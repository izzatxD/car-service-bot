from aiogram import Router, F, types
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, BufferedInputFile
from aiogram.utils.keyboard import InlineKeyboardBuilder

from config import CREATOR_ID
from db import export_orders_to_excel
from db.core import get_pool
from handlers.creator_utils import _safe_edit, _bar

router = Router()

async def render_analytics() -> tuple[str, InlineKeyboardMarkup]:
    pool = get_pool()
    async with pool.acquire() as conn:
        # Top ustalar
        top_m = await conn.fetch("""
            SELECT m.full_name, m.username, m.telegram_id,
                   COUNT(o.id) as cnt, 
                   COALESCE(SUM(o.price), 0) as rev,
                   COALESCE(SUM(o.cost), 0) as cost_t
            FROM orders o JOIN masters m ON o.master_id = m.telegram_id
            WHERE o.status = 'topshirildi'
            GROUP BY m.full_name, m.username, m.telegram_id 
            ORDER BY (COALESCE(SUM(o.price), 0) - COALESCE(SUM(o.cost), 0)) DESC LIMIT 5
        """)

        # Eng ko'p muammolar
        top_p = await conn.fetch(
            "SELECT problem, COUNT(*) as c FROM orders GROUP BY problem ORDER BY c DESC LIMIT 5"
        )

        total = await conn.fetchval("SELECT COUNT(*) FROM orders")
        completed = await conn.fetchval("SELECT COUNT(*) FROM orders WHERE status = 'topshirildi'")
        active = await conn.fetchval("SELECT COUNT(*) FROM orders WHERE status NOT IN ('topshirildi','bekor')")
        cancelled = await conn.fetchval("SELECT COUNT(*) FROM orders WHERE status = 'bekor'")
        
        total_profit = await conn.fetchval("SELECT COALESCE(SUM(price - cost), 0) FROM orders WHERE status = 'topshirildi'")

        monthly_rows = await conn.fetch("""
            SELECT to_char(created_at, 'YYYY-MM') as month,
                   COUNT(*) as cnt,
                   COALESCE(SUM(CASE WHEN status='topshirildi' THEN price ELSE 0 END), 0) as rev,
                   COALESCE(SUM(CASE WHEN status='topshirildi' THEN cost ELSE 0 END), 0) as cost_t
            FROM orders
            GROUP BY 1 ORDER BY 1 DESC LIMIT 3
        """)

    ratio = (completed / total * 100) if total and total > 0 else 0
    max_rev = max(((m['rev'] - m['cost_t']) for m in top_m), default=1) or 1
    max_cnt = max((p['c'] for p in top_p), default=1) or 1

    text = "📊 <b>ANALITIKA</b>\n━━━━━━━━━━━━━━━━━━\n\n"

    text += (
        "<b>Umumiy:</b>\n"
        f"  📋 Jami: <b>{total}</b>  ✅ Bitdi: <b>{completed}</b>\n  "
        f"⏳ Faol: <b>{active}</b>  ❌ Bekor: <b>{cancelled}</b>\n"
        f"  💵 Jami Foyda: <b>{total_profit:,.0f} so'm</b>\n"
        f"  Konversiya: <b>{ratio:.1f}%</b> [{_bar(completed, total)}]\n\n"
    )

    if monthly_rows:
        text += "📅 <b>Oxirgi oylar:</b>\n"
        for row in reversed(monthly_rows):
            profit_m = row['rev'] - row['cost_t']
            text += f"  {row['month']}  —  {row['cnt']} ta  💵 {profit_m:,.0f} s\n"
        text += "\n"

    if top_m:
        text += "🏆 <b>Top ustalar (Foyda bo'yicha):</b>\n"
        for i, m in enumerate(top_m, 1):
            name = (m['full_name'] or m['username'] or f"ID:{m['telegram_id']}")[:18]
            profit = m['rev'] - m['cost_t']
            bar  = _bar(int(profit), int(max_rev))
            text += f"  {i}. <b>{name}</b>\n     [{bar}] {profit:,.0f} so'm ({m['cnt']} ta)\n"
        text += "\n"
    else:
        text += "🏆 <b>Top ustalar:</b> ma'lumot yo'q\n\n"

    if top_p:
        text += "🔧 <b>Eng ko'p muammolar:</b>\n"
        for p in top_p:
            bar = _bar(p['c'], max_cnt)
            text += f"  [{bar}] {p['problem']} — {p['c']}x\n"

    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="🔙 Dashboard", callback_data="admin_dashboard"))
    return text, builder.as_markup()

@router.callback_query(F.data == "admin_analytics")
async def cb_admin_analytics(cb: types.CallbackQuery):
    if cb.from_user.id != CREATOR_ID:
        return
    text, markup = await render_analytics()
    await _safe_edit(cb, text, markup)


@router.callback_query(F.data == "admin_export_xlsx")
async def cb_admin_export(cb: types.CallbackQuery):
    if cb.from_user.id != CREATOR_ID:
        return

    await cb.answer("📊 Excel fayl tayyorlanmoqda...", show_alert=True)

    from datetime import datetime
    file_bytes = await export_orders_to_excel()
    date_str  = datetime.now().strftime('%Y-%m-%d')
    doc       = BufferedInputFile(file_bytes, filename=f"CRM_Orders_{date_str}.xlsx")
    await cb.message.answer_document(doc, caption=f"📊 Barcha buyurtmalar bazasi\nSana: {date_str}")

