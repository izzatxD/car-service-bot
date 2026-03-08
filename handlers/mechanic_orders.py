import logging
from datetime import datetime, timedelta
from aiogram import Router, F, types
from aiogram.fsm.context import FSMContext
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, BufferedInputFile

from config import CREATOR_ID
from db import add_order, get_order, get_master, search_orders
from utils.states import NewOrder
from keyboards.mechanic_kb import main_menu_kb, cancel_kb, skip_kb, problem_templates_kb, warranty_templates_kb, car_models_kb, next_service_kb
from utils.receipt import generate_receipt_pdf

logger = logging.getLogger(__name__)
router = Router()

# ═══════════════════════════════════════════════
#  ➕ YANGI QABUL — Step-by-step FSM
# ═══════════════════════════════════════════════
@router.message(F.text == "➕ Yangi Qabul")
async def new_order_start(message: types.Message, state: FSMContext):
    master = await get_master(message.from_user.id)
    if not master and message.from_user.id != CREATOR_ID:
        return await message.answer("Siz usta emassiz.")
        
    await state.clear()
    await state.set_state(NewOrder.client_name)
    await message.answer(
        "📝 <b>Yangi qabul</b>\n\n👤 Mijozning ism-sharifini kiriting:",
        reply_markup=cancel_kb(),
    )

@router.message(NewOrder.client_name)
async def process_client_name(message: types.Message, state: FSMContext):
    await state.update_data(client_name=message.text.strip())
    await state.set_state(NewOrder.client_phone)
    await message.answer("📞 Mijozning telefon raqamini kiriting:")

@router.message(NewOrder.client_phone)
async def process_client_phone(message: types.Message, state: FSMContext):
    phone = message.text.strip()
    await state.update_data(client_phone=phone)
    
    # ─── Qaytgan mijozni tekshirish ───
    master_id = None if message.from_user.id == CREATOR_ID else message.from_user.id
    prev_orders = await search_orders(phone, master_id=master_id)
    
    if prev_orders:
        last = prev_orders[0]  # eng so'nggi buyurtma
        client_name = last.get('client_name', '')
        car_model = last.get('car_model', '')
        car_number = last.get('car_number', '')
        
        car_info = car_model
        if car_number:
            car_info += f" ({car_number})"
        
        ikb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(
                text=f"✅ Ha, {client_name} — {car_info}",
                callback_data="refill_yes"
            )],
            [InlineKeyboardButton(
                text="✏️ Yo'q, yangidan kiriting",
                callback_data="refill_no"
            )]
        ])
        
        # Avvalgi ma'lumotlarni vaqtincha saqlab qo'yamiz
        await state.update_data(
            _refill_name=client_name,
            _refill_car_model=car_model,
            _refill_car_number=car_number
        )
        
        await message.answer(
            f"🔄 <b>Bu raqam bazada bor!</b>\n\n"
            f"👤 Ism: <b>{client_name}</b>\n"
            f"🚗 Mashina: <b>{car_info}</b>\n\n"
            f"Avvalgi ma'lumotlarni qayta ishlatsinmi?",
            reply_markup=ikb
        )
        return
    
    # Yangi mijoz — to'g'ridan-to'g'ri davom etadi
    await state.set_state(NewOrder.car_model)
    await message.answer("\ud83d\ude97 Mashina rusumini tanlang yoki nomini yozing (masalan: Chevrolet Cobalt):", reply_markup=car_models_kb())

@router.callback_query(F.data == "refill_yes")
async def refill_yes_callback(callback: types.CallbackQuery, state: FSMContext):
    """Avvalgi mijoz ma'lumotlarini avtomatik to'ldirish."""
    data = await state.get_data()
    await state.update_data(
        client_name=data.get('_refill_name', ''),
        car_model=data.get('_refill_car_model', ''),
        car_number=data.get('_refill_car_number', '')
    )
    await state.set_state(NewOrder.mileage)
    await callback.message.edit_text(
        f"✅ <b>Ma'lumotlar to'ldirildi!</b>\n"
        f"👤 {data.get('_refill_name')} | 🚗 {data.get('_refill_car_model')}\n\n"
        f"📈 Mashinaning hozirgi probegini kiriting:\n(Yoki o'tkazib yuboring)"
    )
    await callback.message.answer("📈 Probegni kiriting:", reply_markup=skip_kb())
    await callback.answer()

@router.callback_query(F.data == "refill_no")
async def refill_no_callback(callback: types.CallbackQuery, state: FSMContext):
    """Yangi mijoz sifatida davom etish."""
    await state.set_state(NewOrder.car_model)
    await callback.message.edit_text("✏️ Yangi ma'lumot kiriting:")
    await callback.message.answer("🚗 Mashina rusumini tanlang yoki nomini yozing:", reply_markup=car_models_kb())
    await callback.answer()

@router.message(NewOrder.car_model)
async def process_car_model(message: types.Message, state: FSMContext):
    await state.update_data(car_model=message.text.strip())
    await state.set_state(NewOrder.car_number)
    await message.answer("🔢 Mashina davlat raqamini kiriting (Masalan: 01 A 001 AA):\n(Agar no'malum bo'lsa O'tkazib yuborish)", reply_markup=skip_kb())

@router.message(NewOrder.car_number)
async def process_car_number(message: types.Message, state: FSMContext):
    car_number = "" if message.text == "⏭ O'tkazib yuborish" else message.text.strip()
    await state.update_data(car_number=car_number)
    await state.set_state(NewOrder.mileage)
    await message.answer("📏 Mashinaning hozirgi yurgan masofasini (probeg) kiriting (Masalan: 85,000 km):\n(Agar no'malum bo'lsa O'tkazib yuborish)", reply_markup=skip_kb())

@router.message(NewOrder.mileage)
async def process_car_mileage(message: types.Message, state: FSMContext):
    mileage = "" if message.text == "⏭ O'tkazib yuborish" else message.text.strip()
    await state.update_data(mileage=mileage)
    await state.set_state(NewOrder.problem)
    await message.answer("🔍 Muammo yoki qilinadigan ishlarni tanlang yoki yozing:", reply_markup=problem_templates_kb())

@router.message(NewOrder.problem)
async def process_problem(message: types.Message, state: FSMContext):
    await state.update_data(problem=message.text.strip())
    await state.set_state(NewOrder.car_condition)
    await message.answer("📋 Mashina holatini kiriting (masalan: qirilgan joylari bor):\n(Yoki o'tkazib yuboring)", reply_markup=skip_kb())

@router.message(NewOrder.car_condition)
async def process_car_condition(message: types.Message, state: FSMContext):
    condition = "" if message.text == "⏭ O'tkazib yuborish" else message.text.strip()
    await state.update_data(car_condition=condition)
    await state.set_state(NewOrder.price)
    await message.answer("💰 Taxminiy narxni kiriting (faqat son, ish haqi + ehtiyot qismlar):", reply_markup=cancel_kb())

@router.message(NewOrder.price)
async def process_price(message: types.Message, state: FSMContext):
    price_text = message.text.strip().replace(" ", "").replace(",", "")
    try:
        price = float(price_text)
    except ValueError:
        return await message.answer("⚠️ Iltimos, faqat raqam kiriting! Masalan: 150000")

    await state.update_data(price=price)
    await state.set_state(NewOrder.cost)
    await message.answer("🛠 <b>Harajat summasini kiriting:</b>\n(Masalan, ehtiyot qismlar yoki boshqa xarajatlar)\n\n<i>Agar harajat bo'lmasa, o'tkazib yuborishingiz mumkin:</i>", reply_markup=skip_kb())

@router.message(NewOrder.cost)
async def process_cost(message: types.Message, state: FSMContext):
    if message.text == "⏭ O'tkazib yuborish":
        cost = 0.0
    else:
        cost_text = message.text.strip().replace(" ", "").replace(",", "")
        try:
            cost = float(cost_text)
        except ValueError:
            return await message.answer("⚠️ Iltimos, faqat raqam kiriting yoki o'tkazib yuboring!")

    await state.update_data(cost=cost)
    
    # ─── AVTOMAT KAFOLAT MUDDATI ───
    master_id = None if message.from_user.id == CREATOR_ID else message.from_user.id
    master = await get_master(master_id)
    default_w = (master.get("default_warranty_days") or 0) if master else 0
    
    if default_w > 0:
        await state.update_data(warranty=f"{default_w} kun")
        data = await state.get_data()
        text = _build_confirm_text(data, default_w)
        
        builder = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="✅ Tasdiqlash", callback_data="confirm_order"),
             InlineKeyboardButton(text="❌ Bekor qilish", callback_data="cancel_order")]
        ])
        
        await state.set_state(None)
        await message.answer(text, reply_markup=builder)
    else:
        await state.set_state(NewOrder.warranty)
        await message.answer(
            "🛡 Kafolat muddatini kiriting (masalan: 1 oy, 15 kun):\n(Yoki o'tkazib yuboring)",
            reply_markup=warranty_templates_kb()
        )

def _build_confirm_text(data: dict, auto_warranty: int = 0) -> str:
    warranty_line = (
        f"🛡 Kafolat (avtomat): <b>{auto_warranty} kun</b>"
        if auto_warranty else f"🛡 Kafolat: {data.get('warranty') or '—'}"
    )
    mileage_line = f"📏 Probeg: {data.get('mileage')}\n" if data.get('mileage') else ""
    return (
        f"📋 <b>Ma'lumotlarni tasdiqlang:</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━━━\n"
        f"👤 Mijoz: {data.get('client_name')}\n"
        f"📞 Tel: {data.get('client_phone')}\n"
        f"🚗 Model: {data.get('car_model')}\n"
        f"🔢 Raqam: {data.get('car_number') or '—'}\n"
        f"{mileage_line}"
        f"🔧 Muammo: {data.get('problem')}\n"
        f"🏷 Holati: {data.get('car_condition') or '—'}\n"
        f"💰 Umumiy Narx: {data.get('price', 0):,.0f} so'm\n"
        f"📉 Harajat: {data.get('cost', 0):,.0f} so'm\n"
        f"{warranty_line}\n"
        f"⏱ Keyingi tashrif: {data.get('next_service_text') or '—'}\n"
    )

@router.message(NewOrder.warranty)
async def process_warranty(message: types.Message, state: FSMContext):
    warranty = "" if message.text == "⏭ O'tkazib yuborish" else message.text.strip()
    await state.update_data(warranty=warranty)
    
    await state.set_state(NewOrder.next_service_time)
    await message.answer(
        "⏱ <b>Keyingi tashrif (Eslatma) vaqtini belgilang:</b>\n"
        "Mijoz mashinani kamroq haydasada, 6 oyda kelib tekshirtirib, matorni himoya qilishga eslatib turish uchun muddatni tanlang:",
        reply_markup=next_service_kb()
    )

@router.message(NewOrder.next_service_time)
async def process_next_service(message: types.Message, state: FSMContext):
    btn_text = message.text.strip()
    
    # ⏱ 1 oydan keyin (Taksi)
    # ⏱ 2 oydan keyin (Aktiv)
    # ⏱ 4 oydan keyin (O'rta)
    # ⏱ 6 oydan keyin (Kam yurar)
    months = 0
    if "1 oy" in btn_text: months = 1
    elif "2 oy" in btn_text: months = 2
    elif "4 oy" in btn_text: months = 4
    elif "6 oy" in btn_text: months = 6

    next_date = None
    if months > 0:
        d = datetime.now() + timedelta(days=30 * months)
        next_date = d.strftime("%Y-%m-%d %H:%M:%S")

    await state.update_data(next_service_time=next_date, next_service_text=btn_text)
    
    data = await state.get_data()
    text = _build_confirm_text(data)
    
    builder = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Tasdiqlash", callback_data="confirm_order"),
         InlineKeyboardButton(text="❌ Bekor qilish", callback_data="cancel_order")]
    ])
    await message.answer(text, reply_markup=builder)

@router.callback_query(F.data == "confirm_order")
async def process_confirm_order(callback: types.CallbackQuery, state: FSMContext):
    await callback.message.edit_reply_markup(reply_markup=None)
    await state.set_state(NewOrder.security_code)
    await callback.message.answer(
        "📝 Qo'shimcha izoh yoki parol bormi?\n(Agar yo'q bo'lsa — O'tkazib yuborish)",
        reply_markup=skip_kb()
    )
    await callback.answer()

@router.callback_query(F.data == "cancel_order")
async def process_cancel_order(callback: types.CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.message.edit_reply_markup(reply_markup=None)
    await callback.message.answer("❌ Bekor qilindi!", reply_markup=main_menu_kb(callback.from_user.id))
    await callback.answer()

@router.message(NewOrder.security_code)
async def process_security_code(message: types.Message, state: FSMContext):
    security_code = "" if message.text == "⏭ O'tkazib yuborish" else message.text.strip()
    await state.update_data(security_code=security_code)
    data = await state.get_data()
    data["master_id"] = message.from_user.id

    try:
        from db import add_order, get_order, get_master
        order_id = await add_order(
            master_id=data["master_id"],
            client_name=data.get('client_name', ''),
            client_phone=data.get('client_phone', ''),
            car_model=data.get('car_model', ''),
            car_number=data.get('car_number', ''),
            mileage=data.get('mileage', ''),
            problem=data.get('problem', ''),
            car_condition=data.get('car_condition', ''),
            price=float(data.get('price', 0)),
            cost=float(data.get('cost', 0)),
            warranty=data.get('warranty', ''),
            warranty_until=data.get('warranty_until'),
            next_service_date=data.get('next_service_time'),
            security_code=data.get('security_code', '')  # Foydalanuvchi kiritgan izoh
        )
        
        # Security codeni keyin UPDATE qilishimiz mumkin, hozircha params ichida ishlaydi (add_order da generate bo'lgan)
        
        profit = (data.get('price') or 0) - (data.get('cost') or 0)
        
        summary = (
            f"✅ <b>Buyurtma muvaffaqiyatli saqlandi!</b>\n━━━━━━━━━━━━━━━━━━━━━━\n"
            f"🆔 <b>Buyurtma:</b> #{order_id}\n"
            f"👤 <b>Mijoz:</b> {data.get('client_name')}\n"
            f"📞 <b>Tel:</b> {data.get('client_phone')}\n"
            f"🚗 <b>Model:</b> {data.get('car_model')} (Raqam: {data.get('car_number') or '—'})\n"
            f"📏 <b>Probeg:</b> {data.get('mileage') or '—'}\n"
            f"🔧 <b>Muammo:</b> {data.get('problem')}\n"
            f"💰 <b>Narx:</b> {data.get('price', 0):,.0f} so'm\n"
            f"📉 <b>Harajat:</b> {data.get('cost', 0):,.0f} so'm\n"
            f"💵 <b>Sof Foyda:</b> {profit:,.0f} so'm\n"
            f"🛡 <b>Kafolat:</b> {data.get('warranty') or '—'}\n"
            f"⏱ <b>Eslatma:</b> {data.get('next_service_text') or '—'}\n"
        )
        await message.answer(summary, reply_markup=main_menu_kb(message.from_user.id))
        
        try:
            order = await get_order(order_id)
            master = await get_master(message.from_user.id)
            pdf_buffer = generate_receipt_pdf(order, master_info=master)
            pdf_file = BufferedInputFile(pdf_buffer.read(), filename=f"kvitansiya_{order_id}.pdf")
            await message.answer_document(pdf_file, caption=f"📄 #{order_id} — Kvitansiya (Mijozga yuborishingiz mumkin)")
        except Exception as e:
            logger.error(f"PDF xato: {e}", exc_info=True)
            await message.answer("⚠️ PDF kvitansiyani yaratishda muammo yuz berdi!")
    except Exception as e:
        logger.error(f"Buyurtma saqlashda xato: {e}", exc_info=True)
        await message.answer(
            "⚠️ Buyurtmani saqlashda xatolik yuz berdi! Qaytadan urinib ko'ring yoki /start bosing.",
            reply_markup=main_menu_kb(message.from_user.id)
        )
    finally:
        await state.clear()

