from aiogram import Router, types
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext

from config import CREATOR_ID
from keyboards.mechanic_kb import main_menu_kb
from db import get_master, add_master

router = Router()

@router.message(Command("start"))
async def cmd_start(message: types.Message, state: FSMContext):
    await state.clear()
    
    # Update master's profile upon starting if they are already an active master
    if message.from_user.id != CREATOR_ID:
        master = await get_master(message.from_user.id)
        if master and master["is_active"] == 1:
            await add_master(
                message.from_user.id,
                full_name=message.from_user.full_name,
                username=message.from_user.username
            )

    await message.answer(
        "🚗 <b>Avtoulov Usta CRM</b> tizimiga xush kelibsiz!\n\n"
        "🛠 Bu bot orqali mijozlar bazangizni boshqaring.\n",
        reply_markup=main_menu_kb(message.from_user.id),
    )
