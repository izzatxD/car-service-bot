from aiogram import Router, F, types, Bot
from aiogram.fsm.context import FSMContext
from aiogram.types import InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder

from config import CREATOR_ID
from db import get_master, add_master
from utils.states import AddMaster

router = Router()

@router.callback_query(F.data == "admin_add_master")
async def cb_admin_add_master(cb: types.CallbackQuery, state: FSMContext):
    if cb.from_user.id != CREATOR_ID:
        return

    await state.set_state(AddMaster.waiting_for_id)
    await cb.message.answer(
        "➕ <b>Yangi Usta Qo'shish</b>\n\n"
        "Qo'shmoqchi bo'lgan ustaning <b>Telegram ID</b> raqamini kiriting.\n\n"
        "💡 <i>Foydalanuvchi o'z ID sini bilmasa, @userinfobot ga /start yubortiring.</i>\n\n"
        "Bekor qilish: «❌ Bekor qilish»"
    )
    await cb.answer()

@router.message(AddMaster.waiting_for_id)
async def process_add_master_id(message: types.Message, state: FSMContext):
    if message.from_user.id != CREATOR_ID:
        return

    text = message.text.strip()
    if text in ["❌ Bekor qilish", "🏠 Asosiy menyu", "⚙ Admin Panel"]:
        await state.clear()
        return

    if not text.isdigit():
        await message.answer("❌ Faqat raqam kiriting! Masalan: <code>123456789</code>")
        return

    uid = int(text)
    existing = await get_master(uid)
    if existing:
        status = "🟢 Faol" if existing['is_active'] else "🔴 Bloklangan"
        name   = existing.get('full_name') or existing.get('username') or '—'
        await message.answer(
            f"⚠️ Bu usta allaqachon bazada mavjud!\n"
            f"👤 <b>{name}</b> — {status}"
        )
        await state.clear()
        return

    bot: Bot = message.bot
    chat_found = False
    full_name  = ""
    username   = ""

    try:
        chat = await bot.get_chat(uid)
        if chat.id == uid and str(chat.type) in ("private", "ChatType.PRIVATE"):
            full_name  = chat.full_name or ""
            username   = chat.username or ""
            chat_found = True
    except Exception:
        chat_found = False

    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="✅ Ha, qo'shish", callback_data=f"admin_confirm_add_{uid}"),
        InlineKeyboardButton(text="❌ Bekor",         callback_data="admin_cancel_add"),
    )

    await state.update_data(uid=uid, full_name=full_name, username=username)
    await state.set_state(AddMaster.confirming)

    if chat_found:
        await message.answer(
            f"👤 <b>Topildi!</b>\n\n"
            f"Ism: <b>{full_name or '—'}</b>\n"
            f"Username: {'@' + username if username else '—'}\n"
            f"ID: <code>{uid}</code>\n\n"
            f"Ushbu foydalanuvchini usta sifatida qo'shishni tasdiqlaysizmi?",
            reply_markup=builder.as_markup()
        )
    else:
        await message.answer(
            f"⚠️ <b>Foydalanuvchi aniqlanmadi</b>\n\n"
            f"ID <code>{uid}</code> li foydalanuvchi bot bilan hali muloqot qilmagan yoki mavjud emas.\n"
            f"Baribir qo'shishni xohlaysizmi?\n",
            reply_markup=builder.as_markup()
        )

@router.callback_query(F.data.startswith("admin_confirm_add_"))
async def cb_confirm_add_master(cb: types.CallbackQuery, state: FSMContext):
    if cb.from_user.id != CREATOR_ID:
        return

    uid = int(cb.data.split("_")[-1])
    data = await state.get_data()

    full_name = data.get("full_name", "")
    username  = data.get("username", "")

    success = await add_master(uid, full_name=full_name or None, username=username or None)

    if success:
        name = full_name or (f"@{username}" if username else f"ID:{uid}")
        await cb.message.edit_text(
            f"✅ <b>{name}</b> muvaffaqiyatli qo'shildi!\n"
            f"🆔 <code>{uid}</code>\n"
        )
    else:
        await cb.message.edit_text("❌ Xatolik yuz berdi yoki usta allaqachon mavjud.")

    await state.clear()
    await cb.answer()

@router.callback_query(F.data == "admin_cancel_add")
async def cb_cancel_add_master(cb: types.CallbackQuery, state: FSMContext):
    await state.clear()
    await cb.message.edit_text("❌ Usta qo'shish bekor qilindi.")
    await cb.answer()

