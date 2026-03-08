import logging
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from aiogram import Bot
from datetime import datetime, timezone, timedelta
from db import get_masters_with_reminders, get_overdue_orders, get_next_service_reminders
from db.core import TZ_UZB

logger = logging.getLogger(__name__)

async def check_and_send_reminders(bot: Bot):
    """Barcha eslatmalarni yoqqan ustalar uchun 3 kunlik kechikish xabarlarini soatbay yuborish."""
    # Tashkent vaqti HH:MM hh:mm formatida
    now_time = datetime.now(TZ_UZB).strftime("%H:%M")
    
    try:
        masters = await get_masters_with_reminders()
        for master in masters:
             if master.get("reminder_time") == now_time:
                 overdue_orders = await get_overdue_orders(master["id"])
                 if not overdue_orders:
                     continue
                     
                 text = "⏰ <b>DIQQAT: MUDDATI O'TGAN ISHLAR!</b>\n"
                 text += "━━━━━━━━━━━━━━━━━━\n"
                 text += "Quyidagi mashinalar ustaxonada 3 kundan ortiq vaqtdan beri qolib ketdi:\n\n"
                 
                 for o in overdue_orders:
                     text += f"🚗 <b>{o['car_model']}</b> ({o['car_number']})\n"
                     text += f"👤 Mijoz: {o['client_name']} — {o['client_phone']}\n"
                     text += f"📅 Qabul: {o['created_at'][:10]}\n"
                     text += f"🔧 Muammo: {o['problem']}\n"
                     text += f"🔖 Order ID: #{o['id']}\n\n"
                     
                 text += "<i>Iltimos, ishlarni yakunlagan bo'lsangiz botda '✅ Topshirish' qiling.</i>"
                 
                 try:
                     await bot.send_message(master["telegram_id"], text)
                 except Exception as send_err:
                     logger.error(f"Kechikish eslatmasi yuborishda xatolik Master {master['telegram_id']}: {send_err}")
    except Exception as e:
        logger.error(f"check_and_send_reminders (overdue) umumiy xatolik: {e}")

async def check_next_service_reminders(bot: Bot):
    """Mijozni qaytarish tizimi uchun eslatmalarni ertalab soat 10:00 da yuborishni tekshirish."""
    now_time = datetime.now(TZ_UZB).strftime("%H:%M")
    
    # Faqat soat 10:00 yoki unga yaqin daqiqalarda bir marta ishlasin
    if now_time != "10:00":
        return

    try:
        reminders = await get_next_service_reminders()
        if not reminders:
            return
            
        # Ustalar kesimida guruhlash
        masters_map = {}
        for r in reminders:
            m_id = r["master_id"]
            if m_id not in masters_map:
                masters_map[m_id] = []
            masters_map[m_id].append(r)
            
        # get_master_by_id_or_tel ishlatilmayapti — to'g'ridan to'g'ri SQL ishlatilgan
        
        for master_id, orders in masters_map.items():
            # Ustaning ba'zi telegram malumotlarini olish
            import aiosqlite
            from config import DATABASE_PATH
            async with aiosqlite.connect(DATABASE_PATH) as db:
                db.row_factory = aiosqlite.Row
                c = await db.execute("SELECT telegram_id FROM masters WHERE id = ? AND is_active = 1", (master_id,))
                row = await c.fetchone()
                if not row: continue
                telegram_id = row["telegram_id"]
                
            text = "🔔 <b>MIJOZNI QAYTARISH VAQTI KELDI!</b>\n"
            text += "━━━━━━━━━━━━━━━━━━━━━━\n"
            text += "Quyidagi mijozlaringiz avtomobilini tekshirtirganiga ancha vaqt bo'ldi. Ularga qo'ng'iroq qilib holatidan xabar oling:\n\n"
            
            for o in orders:
                prob_text = f"{o['mileage']} km da qilingan" if o.get('mileage') else "Probeg kiritilmagan"
                text += f"👤 <b>{o['client_name']}</b> — 📞 {o['client_phone']}\n"
                text += f"🚗 {o['car_model']} ({o['car_number']}) | 🔧 <b>{o['problem']}</b>\n"
                text += f"🗓 Oldingi tashrif: {o['created_at'][:10]} ({prob_text})\n\n"
                
            text += "<i>Mijozingizga uning mashinasi haqida qayg'urayotganingizni sezdirish — eng yaxshi xizmatdir!</i>"
            
            try:
                await bot.send_message(telegram_id, text)
            except Exception as e:
                logger.error(f"Next service eslatma yuborishda xato Master {telegram_id}: {e}")
                
    except Exception as e:
        logger.error(f"check_next_service_reminders umumiy xatolik: {e}")

def setup_scheduler(bot: Bot):
    scheduler = AsyncIOScheduler(timezone=TZ_UZB)
    # Har soat boshida tekshiramiz (minute=0)
    scheduler.add_job(check_and_send_reminders, 'cron', minute=0, kwargs={'bot': bot})
    scheduler.add_job(check_next_service_reminders, 'cron', minute=0, kwargs={'bot': bot})
    scheduler.start()
    logger.info("APScheduler eslatmalar uchun ishga tushirildi.")
