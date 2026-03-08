import logging
from aiogram import Router, F, types
from aiogram.fsm.context import FSMContext
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

from config import CREATOR_ID
from db import get_master, update_master_settings, get_workers, add_worker
from utils.states import SettingsState, AddWorker
from keyboards.mechanic_kb import main_menu_kb

logger = logging.getLogger(__name__)
router = Router()

# ═══════════════════════════════════════════════
#  ⚙️ SOZLAMALAR (Master profili)
# ═══════════════════════════════════════════════
@router.message(F.text == "⚙️ Sozlamalar")
async def settings_handler(message: types.Message):
    await show_settings(message, message.from_user.id)

async def show_settings(message: types.Message, user_id: int):
    master_id = None if user_id == CREATOR_ID else user_id
    master = await get_master(master_id)
    if not master:
        return await message.answer("Siz usta emassiz.")

    reminders_on = master.get('reminders_enabled', 0)
    toggle_emoji = "🔔 Yoqilgan ✅" if reminders_on else "🔕 O'chirilgan ❌"
    toggle_action = "reminders_off" if reminders_on else "reminders_on"

    text = (
        "⚙️ <b>Sozlamalar</b>\n"
        "━━━━━━━━━━━━━━━━━━\n"
        f"🏢 <b>Ustaxona nomi:</b> {master.get('workshop_name') or 'Kiritilmagan'}\n"
        f"📍 <b>Manzil:</b> {master.get('address') or 'Kiritilmagan'}\n"
        f"📞 <b>Telefon:</b> {master.get('phone') or 'Kiritilmagan'}\n"
        f"🛡 <b>Standart Kafolat:</b> {master.get('default_warranty_days') or 0} kun\n"
        f"🔔 <b>Eslatmalar:</b> {toggle_emoji}\n"
        f"⏰ <b>Eslatma vaqti:</b> {master.get('reminder_time') or '09:00'}\n\n"
        "O'zgartirmoqchi bo'lgan ma'lumotni tanlang:"
    )

    markup = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🏢 Ustaxona nomi", callback_data="set_workshop_name"),
         InlineKeyboardButton(text="📍 Manzil", callback_data="set_address")],
        [InlineKeyboardButton(text="📞 Telefon", callback_data="set_phone"),
         InlineKeyboardButton(text="🛡 Kafolat muddati", callback_data="set_warranty")],
        [InlineKeyboardButton(text=f"{'🔕 O\'chirish' if reminders_on else '🔔 Yoqish'}", callback_data=toggle_action),
         InlineKeyboardButton(text="⏰ Eslatma vaqti", callback_data="set_reminder")],
    ])
    if master.get('role') == 'boss':
        markup.inline_keyboard.append([InlineKeyboardButton(text="👥 Mening Jamoam", callback_data="my_team")])

    await message.answer(text, reply_markup=markup)

@router.callback_query(F.data.in_({"reminders_on", "reminders_off"}))
async def toggle_reminders(callback: types.CallbackQuery):
    master_id = None if callback.from_user.id == CREATOR_ID else callback.from_user.id
    enabled = 1 if callback.data == "reminders_on" else 0
    await update_master_settings(master_id, reminders_enabled=enabled)
    status = "✅ Eslatmalar yoqildi! Har kuni belgilangan vaqtda 3+ kunlik ishlar haqida xabar olasiz." if enabled else "❌ Eslatmalar o'chirildi."
    await callback.answer(status, show_alert=True)
    # Sozlamalar sahifasini yangilash
    master = await get_master(master_id)
    reminders_on = master.get('reminders_enabled', 0)
    toggle_emoji = "🔔 Yoqilgan ✅" if reminders_on else "🔕 O'chirilgan ❌"
    text = (
        "⚙️ <b>Sozlamalar</b>\n"
        "━━━━━━━━━━━━━━━━━━\n"
        f"🏢 <b>Ustaxona nomi:</b> {master.get('workshop_name') or 'Kiritilmagan'}\n"
        f"📍 <b>Manzil:</b> {master.get('address') or 'Kiritilmagan'}\n"
        f"📞 <b>Telefon:</b> {master.get('phone') or 'Kiritilmagan'}\n"
        f"🛡 <b>Standart Kafolat:</b> {master.get('default_warranty_days') or 0} kun\n"
        f"🔔 <b>Eslatmalar:</b> {toggle_emoji}\n"
        f"⏰ <b>Eslatma vaqti:</b> {master.get('reminder_time') or '09:00'}\n\n"
        "O'zgartirmoqchi bo'lgan ma'lumotni tanlang:"
    )
    markup = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🏢 Ustaxona nomi", callback_data="set_workshop_name"),
         InlineKeyboardButton(text="📍 Manzil", callback_data="set_address")],
        [InlineKeyboardButton(text="📞 Telefon", callback_data="set_phone"),
         InlineKeyboardButton(text="🛡 Kafolat muddati", callback_data="set_warranty")],
        [InlineKeyboardButton(text=f"{'🔕 O\'chirish' if reminders_on else '🔔 Yoqish'}", callback_data='reminders_off' if reminders_on else 'reminders_on'),
         InlineKeyboardButton(text="⏰ Eslatma vaqti", callback_data="set_reminder")],
    ])
    if master.get('role') == 'boss':
        markup.inline_keyboard.append([InlineKeyboardButton(text="👥 Mening Jamoam", callback_data="my_team")])
        
    await callback.message.edit_text(text, reply_markup=markup)

@router.callback_query(F.data.startswith("set_"))
async def process_settings_callbacks(callback: types.CallbackQuery, state: FSMContext):
    action = callback.data.replace("set_", "")
    
    if action == "workshop_name":
        await state.set_state(SettingsState.workshop_name)
        await callback.message.edit_text("🏢 Kvitansiya uchun <b>Ustaxona nomini</b> kiriting (qisqa va aniq):", reply_markup=None)
    elif action == "address":
        await state.set_state(SettingsState.address)
        await callback.message.edit_text("📍 Kvitansiya uchun <b>Ustaxona manzilini</b> kiriting (qisqa, tushunarli):", reply_markup=None)
    elif action == "phone":
         await state.set_state(SettingsState.phone)
         await callback.message.edit_text("📞 Mijozlar sizga bog'lanishi uchun <b>Telefon raqamingizni</b> kiriting:", reply_markup=None)
    elif action == "warranty":
         await state.set_state(SettingsState.warranty_days)
         await callback.message.edit_text("🛡 Standart kafolat beriladigan kunlar sonini kiriting (raqam bilan, masalan: 7):", reply_markup=None)
    elif action == "reminder":
         await state.set_state(SettingsState.reminder_time)
         await callback.message.edit_text(
            "⏰ <b>Eslatma vaqti</b>\n\n"
            "3 kundan ko'proq vaqt olib yotgan, topshirilmagan ishlar bo'yicha\n"
            "har kuni avtomatik eslatma keladi.\n\n"
            "Vaqtni <b>HH:MM</b> formatida yozing:\n"
            "(Masalan: <code>09:00</code> yoki <code>20:30</code>)",
            reply_markup=None
         )
         
    await callback.answer()

@router.message(SettingsState.workshop_name)
async def save_workshop_name(message: types.Message, state: FSMContext):
    master_id = None if message.from_user.id == CREATOR_ID else message.from_user.id
    await update_master_settings(master_id, workshop_name=message.text.strip())
    await message.answer("✅ Ustaxona nomi saqlandi!", reply_markup=main_menu_kb(message.from_user.id))
    await state.clear()

@router.message(SettingsState.address)
async def save_address(message: types.Message, state: FSMContext):
    master_id = None if message.from_user.id == CREATOR_ID else message.from_user.id
    await update_master_settings(master_id, address=message.text.strip())
    await message.answer("✅ Manzil saqlandi!", reply_markup=main_menu_kb(message.from_user.id))
    await state.clear()
    
@router.message(SettingsState.phone)
async def save_phone(message: types.Message, state: FSMContext):
    master_id = None if message.from_user.id == CREATOR_ID else message.from_user.id
    await update_master_settings(master_id, phone=message.text.strip())
    await message.answer("✅ Telefon raqam saqlandi!", reply_markup=main_menu_kb(message.from_user.id))
    await state.clear()

@router.message(SettingsState.warranty_days)
async def save_warranty_days(message: types.Message, state: FSMContext):
    days_txt = message.text.strip()
    if not days_txt.isdigit():
        return await message.answer("⚠️ Faqat kunlar sonini (raqam) kiriting. Masalan: 10")
    
    master_id = None if message.from_user.id == CREATOR_ID else message.from_user.id
    await update_master_settings(master_id, default_warranty_days=int(days_txt))
    await message.answer("✅ Standart kafolat kunlari saqlandi!", reply_markup=main_menu_kb(message.from_user.id))
    await state.clear()

@router.message(SettingsState.reminder_time)
async def save_reminder_time(message: types.Message, state: FSMContext):
    time_str = message.text.strip()
    if len(time_str) != 5 or ':' not in time_str:
        return await message.answer("⚠️ Vaqtni HH:MM formatida kiriting. Masalan: 09:00")
        
    master_id = None if message.from_user.id == CREATOR_ID else message.from_user.id
    await update_master_settings(master_id, reminder_time=time_str)
    await message.answer(f"✅ Eslatmalar vaqti {time_str} ga o'rnatildi!", reply_markup=main_menu_kb(message.from_user.id))
    await state.clear()

# ═══════════════════════════════════════════════
#  JAMOAVIY BOSHQARUV (XODIMLAR / SHOGIRDLAR)
# ═══════════════════════════════════════════════

@router.callback_query(F.data == "my_team")
async def my_team_handler(callback: types.CallbackQuery):
    master_id = None if callback.from_user.id == CREATOR_ID else callback.from_user.id
    workers = await get_workers(master_id)
    
    text = f"👥 <b>Mening Jamoam ({len(workers)} kishi)</b>\n━━━━━━━━━━━━━━━━━━\n\n"
    if not workers:
        text += "Sizda hali ishchilar tayinlanmagan.\n(Ishchi - o'z mijozlarini kiritib, ishini o'zi bitkazadi va foyda unga yoziladi, biroq statistikasini siz to'liq kuzata olasiz)."
    else:
        for i, w in enumerate(workers, 1):
            phone = w.get('phone') or "Yo'q"
            name = w.get('full_name') or w.get('username') or "Noma'lum"
            text += f"{i}. <b>{name}</b> (<code>ID: {w['telegram_id']}</code>)\n📞 {phone}\n\n"
            
    text += "\nYangi ishchi / shogird qo'shish uchun pastdagi tugmani bosing."
    
    markup = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="➕ Xodim qo'shish", callback_data="add_team_worker")],
        [InlineKeyboardButton(text="🔙 Orqaga", callback_data="back_to_settings_main")]
    ])
    
    await callback.message.edit_text(text, reply_markup=markup)

@router.callback_query(F.data == "back_to_settings_main")
async def back_to_settings_main_handler(callback: types.CallbackQuery):
    await toggle_reminders(callback)

@router.callback_query(F.data == "add_team_worker")
async def add_worker_start(callback: types.CallbackQuery, state: FSMContext):
    await state.set_state(AddWorker.waiting_for_id)
    await callback.message.edit_text(
        "📝 O'z ustaxonangizga xodim qo'shish:\n\n"
        "Shogird/xodimning <b>Telegram ID</b> raqamini yozib yuboring.\n"
        "(Ushbu raqamni kishi o'zining telegramidan @getmyid_bot kabi botlarga kirib bilib olishi mumkin).", 
        reply_markup=None
    )
    await callback.answer()

@router.message(AddWorker.waiting_for_id)
async def add_worker_id(message: types.Message, state: FSMContext):
    if not message.text.isdigit():
        return await message.answer("⚠️ Telegram ID faqat raqamlardan iborat bo'ladi! Raqamni qaytadan kiriting:")
    
    await state.update_data(worker_id=int(message.text.strip()))
    await state.set_state(AddWorker.waiting_for_name)
    await message.answer("Endi Xodimning ism-sharifini yozing:")

@router.message(AddWorker.waiting_for_name)
async def add_worker_name(message: types.Message, state: FSMContext):
    await state.update_data(worker_name=message.text.strip())
    await state.set_state(AddWorker.waiting_for_phone)
    await message.answer("Xodimning telefon raqamini kiriting:")

@router.message(AddWorker.waiting_for_phone)
async def add_worker_phone(message: types.Message, state: FSMContext):
    await state.update_data(worker_phone=message.text.strip())
    await state.set_state(AddWorker.waiting_for_branch_name)
    await message.answer("Ushbu xodim ustaxonangizning qaysi filialiga biriktiriladi?\n(Masalan: Chilonzor filial, Yunusobod. Yoki shunchaki bitta nom yozing):", reply_markup=types.ReplyKeyboardRemove())

@router.message(AddWorker.waiting_for_branch_name)
async def add_worker_branch_name(message: types.Message, state: FSMContext):
    data = await state.get_data()
    worker_id = data['worker_id']
    worker_name = data['worker_name']
    phone = data['worker_phone']
    branch_name = message.text.strip()
    
    parent_id = None if message.from_user.id == CREATOR_ID else message.from_user.id
    
    ok = await add_worker(parent_id, worker_id, worker_name, phone, branch_name)
    if ok:
        await message.answer(f"✅ Xodim <b>{worker_name}</b> muvaffaqiyatli <b>{branch_name}</b> filialiga qo'shildi!\n\nEndi u ham botdan foydalansa, ishlari sizning statistikangizga aynan shu filial bilan uzatiladi.", reply_markup=main_menu_kb(message.from_user.id))
    else:
        await message.answer("❌ Xodimni qo'shib bo'lmadi. Ehtimol uning ID si allaqachon botda qandaydir maxsus ustuna bilan r'oyxatdan o'tgan bo'lishi mumkin.", reply_markup=main_menu_kb(message.from_user.id))
        
    await state.clear()
