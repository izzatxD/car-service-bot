import logging
from aiogram import Router, F, types
from aiogram.fsm.context import FSMContext
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

from config import CREATOR_ID
from db import get_master, get_order, get_debtors, pay_debt, complete_order, get_branches, fmt_dt
from utils.states import PartialPayment, PayDebtState
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

@router.callback_query(F.data.startswith("pay_"))
async def process_payment_callback(callback: types.CallbackQuery, state: FSMContext):
    _, order_id_str, method = callback.data.split("_", 2)
    order_id = int(order_id_str)
    master_id = callback.from_user.id # FAQAT o'ziniki bo'yicha to'lov qiladi
    
    order = await get_order(order_id, master_id=master_id)
    if not order:
        return await callback.answer("Xatolik: Buyurtma topilmadi!", show_alert=True)
        
    if method == "nasiya":
        await state.update_data(nasiya_order_id=order_id)
        await state.set_state(PartialPayment.amount)
        return await callback.message.edit_text(
            f"💰 Buyurtma #{order_id} umumiy summasi: <b>{order['price']:,.0f} so'm.</b>\n\n"
            f"Mijoz hozir (oldindan) necha pul to'ladi?\n(Agar hozir hech qancha bermagan bo'lsa 0 kiriting):",
        )
        
    paid_amount = float(order['price'])
    await complete_order(order_id, method, paid_amount, master_id=master_id)
    
    pm_emoji = {"naqd": "💵 Naqd", "karta": "💳 Karta"}
    await callback.message.edit_text(
        f"📦 Buyurtma #{order_id} topshirildi!\n"
        f"To'lov: <b>{pm_emoji.get(method, method)}</b>\n"
        f"Summa: {order['price']:,.0f} so'm"
    )
    await callback.answer("✅ Topshirildi!")

@router.message(PartialPayment.amount)
async def process_partial_payment(message: types.Message, state: FSMContext):
    amount_text = message.text.strip().replace(" ", "").replace(",", "")
    try:
        paid_amount = float(amount_text)
    except ValueError:
        return await message.answer("⚠️ Iltimos, faqat raqam kiriting! (Masalan: 50000 yoki 0)")
        
    data = await state.get_data()
    order_id = data.get("nasiya_order_id")
    master_id = None if message.from_user.id == CREATOR_ID else message.from_user.id
    
    order = await get_order(order_id, master_id=master_id)
    if not order:
        await state.clear()
        return await message.answer("⚠️ Xatolik: Buyurtma topilmadi!", reply_markup=main_menu_kb(message.from_user.id))
        
    if paid_amount > order['price']:
        return await message.answer(f"⚠️ Kiritilgan summa umumiy narxdan ({order['price']:,.0f} so'm) ko'p bo'lishi mumkin emas!\nQaytadan kiriting:")
        
    await complete_order(order_id, "nasiya", paid_amount, master_id=master_id)
    
    await message.answer(
        f"📦 Buyurtma #{order_id} topshirildi!\n"
        f"To'lov: <b>📝 Nasiya (Qarz)</b>\n"
        f"Umumiy summa: {order['price']:,.0f} so'm\n"
        f"To'langan: {paid_amount:,.0f} so'm\n"
        f"❗ Qarz bo'lib qoldi: {(order['price'] - paid_amount):,.0f} so'm",
        reply_markup=main_menu_kb(message.from_user.id)
    )
    await state.clear()

# ═══════════════════════════════════════════════
#  📝 QARZDORLAR
# ═══════════════════════════════════════════════
@router.message(F.text == "📝 Qarzdorlar")
async def debtors_handler(message: types.Message):
    master_id = message.from_user.id # Har doim o'ziniki
    master = await get_master(master_id)
    if master and master.get('role') == 'boss':
        branches = await get_branches(master_id)
        if branches:
            await message.answer(
                "📝 <b>Qarzdorlar</b> ro'yxatini qaysi filial bo'yicha ko'rasiz?",
                reply_markup=build_branch_keyboard(branches, "debt_branch")
            )
            return

    await show_debtors_page(message, page=1, branch_name=None)

@router.callback_query(F.data.startswith("debt_branch:"))
async def debt_branch_callback(callback: types.CallbackQuery):
    bn = callback.data.split(":", 1)[1]
    branch = None if bn == "all" else bn
    master_id = callback.from_user.id # Har doim o'ziniki
    await callback.message.delete()
    await show_debtors_page(callback.message, page=1, is_callback=False, user_id=callback.from_user.id, branch_name=branch)
    await callback.answer()

@router.callback_query(F.data.startswith("debtpage_"))
async def debtors_page_callback(callback: types.CallbackQuery):
    parts = callback.data.split("_", 2)
    page = int(parts[1])
    bn = parts[2] if len(parts) > 2 else "all"
    branch = None if bn == "all" else bn
    await show_debtors_page(callback.message, page=page, is_callback=True, user_id=callback.from_user.id, branch_name=branch)
    await callback.answer()

@router.callback_query(F.data == "ignore")
async def ignore_callback(callback: types.CallbackQuery):
    await callback.answer()

async def show_debtors_page(message: types.Message, page: int = 1, is_callback: bool = False, user_id: int | None = None, branch_name: str | None = None):
    uid = user_id if user_id else message.from_user.id
    master_id = uid # Har doim o'ziniki
    debtors = await get_debtors(master_id, branch_name=branch_name, is_personal=True)
    
    if not debtors:
        bn_text = f" ({branch_name})" if branch_name else ""
        text = f"🎉 Hozircha qarzdorlar yo'q!{bn_text}"
        if is_callback:
            await message.edit_text(text)
        else:
            await message.answer(text, reply_markup=main_menu_kb(uid))
        return

    PER_PAGE = 5
    total_pages = (len(debtors) + PER_PAGE - 1) // PER_PAGE
    if page < 1: page = 1
    if page > total_pages: page = total_pages
    
    start_idx = (page - 1) * PER_PAGE
    end_idx = start_idx + PER_PAGE
    current_debtors = debtors[start_idx:end_idx]
    
    text = f"📝 <b>Qarzdorlar ro'yxati</b> (Sahifa: {page} / {total_pages})\n"
    text += f"Jami qarzdorlar: {len(debtors)} ta\n\n"
    
    buttons = []
    
    for o in current_debtors:
        qarz_summasi = o['price'] - o['paid_amount']
        text += (
            f"👤 <b>{o['client_name']}</b> (📞 {o['client_phone']})\n"
            f"🆔 <b>#{o['id']}</b> | 🚗 {o['car_model']}\n"
            f"💰 Umumiy: {o['price']:,.0f} so'm\n"
            f"❗ <b>Qolgan qarz: {qarz_summasi:,.0f} so'm</b>\n"
            f"📅 Sana: {fmt_dt(o['completed_at'])}\n"
            f"━━━━━━━━━━━━━━━━━━\n"
        )
        buttons.append([InlineKeyboardButton(text=f"✅ #{o['id']} ni to'lash", callback_data=f"paydebt_{o['id']}")])
        
    bn_data = branch_name if branch_name else "all"
    nav_buttons = []
    if page > 1:
        nav_buttons.append(InlineKeyboardButton(text="⬅️ Oldingi", callback_data=f"debtpage_{page-1}_{bn_data}"))
    
    nav_buttons.append(InlineKeyboardButton(text=f"{page}/{total_pages}", callback_data="ignore"))
    
    if page < total_pages:
        nav_buttons.append(InlineKeyboardButton(text="Keyingi ➡️", callback_data=f"debtpage_{page+1}_{bn_data}"))
        
    buttons.append(nav_buttons)
    ikb = InlineKeyboardMarkup(inline_keyboard=buttons)
    
    if is_callback:
        await message.edit_text(text, reply_markup=ikb)
    else:
        await message.answer(text, reply_markup=ikb)

@router.callback_query(F.data.startswith("paydebt_"))
async def process_paydebt_callback(callback: types.CallbackQuery, state: FSMContext):
    _, order_id_str = callback.data.split("_", 1)
    order_id = int(order_id_str)
    
    master_id = callback.from_user.id # Har doim o'ziniki
    order = await get_order(order_id, master_id=master_id)
    
    if not order:
        return await callback.answer("Xato: Buyurtma topilmadi!", show_alert=True)
        
    qarz_summasi = order['price'] - order['paid_amount']
    
    await state.update_data(paydebt_order_id=order_id, qarz_summasi=qarz_summasi)
    await state.set_state(PayDebtState.amount)
    
    await callback.message.edit_text(
        f"📝 <b>Qarz to'lash (Buyurtma #{order_id})</b>\n\n"
        f"👤 Mijoz: {order['client_name']}\n"
        f"💵 Qolgan qarz summasi: <b>{qarz_summasi:,.0f} so'm</b>\n\n"
        f"Mijoz qancha to'lamoqda? (raqamda kiriting):"
    )
    await callback.answer()

@router.message(PayDebtState.amount)
async def process_paydebt_amount(message: types.Message, state: FSMContext):
    amount_text = message.text.strip().replace(" ", "").replace(",", "")
    try:
        additional_amount = float(amount_text)
    except ValueError:
        return await message.answer("⚠️ Iltimos, faqat raqam kiriting!")
        
    data = await state.get_data()
    order_id = data.get("paydebt_order_id")
    qarz_summasi = data.get("qarz_summasi")
    
    if additional_amount > qarz_summasi:
        return await message.answer(f"⚠️ Kiritilgan summa qarz summasidan ({qarz_summasi:,.0f} so'm) ko'p!\nQaytadan kiriting:")
        
    master_id = None if message.from_user.id == CREATOR_ID else message.from_user.id
    is_fully_paid = await pay_debt(order_id, additional_amount, master_id=master_id)
    
    text = f"✅ <b>To'lov qabul qilindi! (Buyurtma #{order_id})</b>\n"
    text += f"To'landi: {additional_amount:,.0f} so'm\n"
    if is_fully_paid:
        text += "🎉 <b>Qarz to'liq uzildi!</b>"
    else:
        text += f"❗ Qolgan qarz: {(qarz_summasi - additional_amount):,.0f} so'm"
        
    await message.answer(text, reply_markup=main_menu_kb(message.from_user.id))
    await state.clear()

