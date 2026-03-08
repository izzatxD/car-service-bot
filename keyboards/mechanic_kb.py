from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
from config import CREATOR_ID

def main_menu_kb(user_id: int):
    kb = [
        [KeyboardButton(text="➕ Yangi Qabul"), KeyboardButton(text="🔍 Qidiruv")],
        [KeyboardButton(text="⏳ Faol ishlar"), KeyboardButton(text="📊 Statistika")],
        [KeyboardButton(text="📝 Qarzdorlar")]
    ]
    if user_id == CREATOR_ID:
        kb.append([KeyboardButton(text="⚙ Admin Panel")])
    else:
        kb.append([KeyboardButton(text="⚙️ Sozlamalar")])
    return ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True)

def cancel_kb():
    return ReplyKeyboardMarkup(keyboard=[[KeyboardButton(text="❌ Bekor qilish")]], resize_keyboard=True)

def skip_kb():
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="⏭ O'tkazib yuborish")], [KeyboardButton(text="❌ Bekor qilish")]],
        resize_keyboard=True,
    )

def admin_panel_kb():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="⚙ Admin Panel"), KeyboardButton(text="🏠 Asosiy menyu")]
        ],
        resize_keyboard=True
    )

def problem_templates_kb():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="Moy almashtirish"), KeyboardButton(text="Xodovoy qismi"), KeyboardButton(text="Dvigatel ishi")],
            [KeyboardButton(text="Elektrika"), KeyboardButton(text="Tormoz sistemasi"), KeyboardButton(text="Kuzov va bo'yoq")],
            [KeyboardButton(text="❌ Bekor qilish")]
        ],
        resize_keyboard=True
    )

def warranty_templates_kb():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="Kafolatsiz (0 kun)"), KeyboardButton(text="7 kun")],
            [KeyboardButton(text="14 kun"), KeyboardButton(text="1 oy"), KeyboardButton(text="3 oy")],
            [KeyboardButton(text="❌ Bekor qilish")]
        ],
        resize_keyboard=True
    )

def car_models_kb():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="Cobalt"), KeyboardButton(text="Gentra / Lacetti")],
            [KeyboardButton(text="Spark"), KeyboardButton(text="Nexia (1,2,3)")],
            [KeyboardButton(text="Matiz"), KeyboardButton(text="Tracker / Onix")],
            [KeyboardButton(text="❌ Bekor qilish")]
        ],
        resize_keyboard=True
    )

def next_service_kb():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="⏱ 1 oydan keyin (Taksi)"), KeyboardButton(text="⏱ 2 oydan keyin (Aktiv)")],
            [KeyboardButton(text="⏱ 4 oydan keyin (O'rta)"), KeyboardButton(text="⏱ 6 oydan keyin (Kam yurar)")],
            [KeyboardButton(text="⏭ Eslatma kerak emas")]
        ],
        resize_keyboard=True
    )
