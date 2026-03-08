import logging
from aiogram import Router, F, types
from aiogram.fsm.context import FSMContext
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

from config import CREATOR_ID
from db import get_master, get_order, update_order_status, get_active_orders, get_branches, fmt_dt
from keyboards.mechanic_kb import main_menu_kb

logger = logging.getLogger(__name__)
router = Router()

def build_branch_keyboard(branches: list[str], prefix: str):
    buttons = []
    for i in range(0, len(branches), 2):
        row = [InlineKeyboardButton(text=f"🏢 {branches[i]}", callback_data=f"{prefix}:{branches[i]}")]
        if i + 1 < len(branches):
            row.append(InlineKeyboardButton(text=f"🏢 {branches[i+1]}", callback_data=f"{prefix}:{branches[i+1]}"))
        buttons.append(row)
    buttons.append([InlineKeyboardButton(text="📊 Umumiy (Barchasi)", callback_data=f"{prefix}:all")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)

# ═══════════════════════════════════════════════
#  ⏳ FAOL ISHLAR (PROFESSIONAL WORKFLOW)
# ═══════════════════════════════════════════════
def _build_active_order_card(o: dict):
    st = o.get('status', '')
    emoji = "⚪"
    if st == "qabul_qilindi": emoji = "⚪"
    elif st == "jarayonda": emoji = "🟡"
    elif st == "tayyor": emoji = "🟢"
    elif st == "topshirildi": emoji = "�"
    elif st == "bekor": emoji = "❌"
    
    mileage_line = f"📏 Probeg: {o.get('mileage')}\n" if o.get('mileage') else ""
    text = (
        f"{emoji} <b>#{o['id']}</b> — {o['client_name']}\n"
        f"🚗 Model: {o['car_model']} ({o.get('car_number') or '-'}) \n"
        f"{mileage_line}"
        f"🔧 Muammo: {o['problem']}\n"
        f"💰 Narx: {o.get('price', 0):,.0f} so'm\n"
        f"📅 Qabul: {fmt_dt(o['created_at'])}\n"
        f"📋 Status: {st.replace('_', ' ').capitalize()}"
    )
    
    buttons = []
    if st == "qabul_qilindi":
        buttons.append(InlineKeyboardButton(text="▶ Jarayonga", callback_data=f"status_{o['id']}_jarayonda"))
    elif st == "jarayonda":
        buttons.append(InlineKeyboardButton(text="✅ Tayyor", callback_data=f"status_{o['id']}_tayyor"))
    elif st == "tayyor":
        buttons.append(InlineKeyboardButton(text="📦 Topshirildi", callback_data=f"status_{o['id']}_topshirildi"))
        
    if st not in ["topshirildi", "bekor"]:
        buttons.append(InlineKeyboardButton(text="❌ Bekor", callback_data=f"status_{o['id']}_bekor"))
    
    ikb = InlineKeyboardMarkup(inline_keyboard=[buttons]) if buttons else None
    return text, ikb

@router.message(F.text == "⏳ Faol ishlar")
async def active_orders_handler(message: types.Message):
    master_id = message.from_user.id # Har doim o'zining ishlari ko'rinadi
    from db import get_master, get_branches
    master = await get_master(master_id)
    if master and master.get('role') == 'boss':
        branches = await get_branches(master_id)
        if branches:
            await message.answer(
                "📅 <b>Faol ishlar</b> ro'yxatini qaysi filial bo'yicha ko'rasiz?",
                reply_markup=build_branch_keyboard(branches, "active_branch")
            )
            return

    await _show_active_orders(message, master_id, None)

@router.callback_query(F.data.startswith("active_branch:"))
async def active_branch_callback(callback: types.CallbackQuery):
    bn = callback.data.split(":", 1)[1]
    branch = None if bn == "all" else bn
    master_id = callback.from_user.id # Har doim o'zining ishlari ko'rinadi
    await callback.message.delete()
    await _show_active_orders(callback.message, master_id, branch)
    await callback.answer()

async def _show_active_orders(message: types.Message, master_id: int | None, branch_name: str | None):
    orders = await get_active_orders(master_id=master_id, branch_name=branch_name, is_personal=True)

    if not orders:
        bn_text = f" ({branch_name})" if branch_name else ""
        return await message.answer(f"🎉 Hozirda faol ishlar yo'q!{bn_text}", reply_markup=main_menu_kb(message.from_user.id if message.from_user else CREATOR_ID))

    for o in orders:
        text, ikb = _build_active_order_card(o)
        await message.answer(text, reply_markup=ikb)


@router.callback_query(F.data.startswith("status_"))
async def update_status_callback(callback: types.CallbackQuery, state: FSMContext):
    _, order_id_str, new_status = callback.data.split("_", 2)
    order_id = int(order_id_str)
    
    master_id = None if callback.from_user.id == CREATOR_ID else callback.from_user.id
    
    if new_status == "topshirildi":
        ikb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="💵 Naqd", callback_data=f"pay_{order_id}_naqd")],
            [InlineKeyboardButton(text="💳 Karta", callback_data=f"pay_{order_id}_karta")],
            [InlineKeyboardButton(text="📝 Nasiya", callback_data=f"pay_{order_id}_nasiya")],
            [InlineKeyboardButton(text="🔙 Orqaga", callback_data=f"status_{order_id}_tayyor")]
        ])
        
        # Payment uchun vaqtinchalik o'zgartirish textini chiqarish:
        order = await get_order(order_id, master_id=master_id)
        if order:
            await callback.message.edit_text(
                f"💰 Buyurtma #{order_id} summasi: <b>{order.get('price', 0):,.0f} so'm</b>\nTo'lov turini tanlang:", 
                reply_markup=ikb
            )
        else:
            await callback.message.edit_text(f"To'lov turini tanlang (Buyurtma #{order_id}):", reply_markup=ikb)
            
        await callback.answer()
        return
        
    await update_order_status(order_id, new_status, master_id=master_id)
    
    order = await get_order(order_id, master_id=master_id)
    if order:
        text, ikb = _build_active_order_card(order)
        await callback.message.edit_text(text, reply_markup=ikb)
    else:
        st_emoji = {"jarayonda": "🟡", "tayyor": "🟢", "topshirildi": "📦", "bekor": "❌"}
        await callback.message.edit_text(
            f"{st_emoji.get(new_status, '')} Buyurtma #{order_id} statusi: <b>{new_status.replace('_', ' ').capitalize()}</b>"
        )
        
    await callback.answer("✅ Status yangilandi!")

