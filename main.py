import asyncio
import logging
import sys
import os

# Add bot directory to sys.path so imports work when launching as: python bot/main.py
sys.path.insert(0, os.path.dirname(__file__))

from aiogram import Bot, Dispatcher, types
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties
from aiogram.fsm.storage.memory import MemoryStorage
try:
    from aiogram_sqlite_storage.sqlitestore import SQLiteStorage
    _USE_SQLITE_STORAGE = True # Production
except ImportError:
    _USE_SQLITE_STORAGE = False


from config import BOT_TOKEN, LOG_LEVEL, CREATOR_ID, FSM_STORAGE_PATH
import db
from db import get_master, get_active_orders
from handlers import (
    start,
    creator_main, creator_masters, creator_stats, 
    creator_search, creator_add, creator_broadcast,
    mechanic_common, mechanic_orders, mechanic_active, 
    mechanic_finance, mechanic_search, mechanic_settings, mechanic_stats
)
from middlewares.logging_mw import LoggingMiddleware
from utils.reminders import setup_scheduler

# ─── Logging setup ────────────────────────────────────────────────────────────
logging.basicConfig(
    level=getattr(logging, LOG_LEVEL, logging.INFO),
    format="%(asctime)s | %(levelname)-8s | %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger(__name__)

# ═══════════════════════════════════════════════
#  ACCESS MIDDLEWARE — faqat creator va aktiv ustalar
# ═══════════════════════════════════════════════
import time
from aiogram import BaseMiddleware

# Simple expiring cache for master access (5 minutes)
_access_cache = {}
CACHE_TTL = 300

class AccessMiddleware(BaseMiddleware):
    async def __call__(self, handler, event, data):
        user = event.from_user
        if not user:
            return await handler(event, data)
        if user.id == CREATOR_ID:
            return await handler(event, data)
            
        # Check cache first
        now = time.time()
        if user.id in _access_cache:
            cache_entry = _access_cache[user.id]
            if now - cache_entry['time'] < CACHE_TTL:
                if cache_entry['is_active']:
                    return await handler(event, data)
                else:
                    return await self._reject(event)
                    
        # If not in cache or expired, check DB
        master = await get_master(user.id)
        is_active = bool(master and master["is_active"] == 1)
        
        # Save to cache
        _access_cache[user.id] = {'is_active': is_active, 'time': now}
        
        if is_active:
            return await handler(event, data)
            
        return await self._reject(event)
        
    async def _reject(self, event):
        if isinstance(event, types.Message):
            await event.answer("❌ Sizga botdan foydalanish ruxsati berilmagan.\n\nAdmin bilan bog'laning.")
        elif isinstance(event, types.CallbackQuery):
            await event.answer("❌ Ruxsat yo'q!", show_alert=True)
        return


async def main():
    if not BOT_TOKEN:
        logger.critical("BOT_TOKEN is not set! Check your .env file.")
        sys.exit(1)

    # Initialize database
    await db.init_db()
    logger.info("Database ready.")

    # FSM Storage — SQLite (diskda saqlaydi, bot restart da yo'qolmaydi)
    if _USE_SQLITE_STORAGE:
        storage = SQLiteStorage(db_path=FSM_STORAGE_PATH)
        logger.info(f"FSM storage: SQLiteStorage ({FSM_STORAGE_PATH})")
    else:
        storage = MemoryStorage()
        logger.warning("aiogram-sqlite-storage topilmadi! MemoryStorage ishlatilmoqda (restart da holatlar o'chadi).")

    bot = Bot(
        token=BOT_TOKEN,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML)
    )
    dp = Dispatcher(storage=storage)

    # ── Middlewares ────────────────────────────────────────────────────────────
    dp.message.middleware(LoggingMiddleware())
    dp.message.middleware(AccessMiddleware())
    dp.callback_query.middleware(AccessMiddleware())

    # ── Routers (order matters: most specific first) ───────────────────────────
    dp.include_router(start.router)
    
    # Creator Handlers
    dp.include_router(creator_main.router)
    dp.include_router(creator_masters.router)
    dp.include_router(creator_stats.router)
    dp.include_router(creator_search.router)
    dp.include_router(creator_add.router)
    dp.include_router(creator_broadcast.router)
    
    # Mechanic Handlers
    dp.include_router(mechanic_common.router)
    dp.include_router(mechanic_settings.router)
    dp.include_router(mechanic_orders.router)
    dp.include_router(mechanic_active.router)
    dp.include_router(mechanic_finance.router)
    dp.include_router(mechanic_search.router)
    dp.include_router(mechanic_stats.router)

    logger.info("Bot starting in polling mode…")
    setup_scheduler(bot)
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())


if __name__ == "__main__":
    asyncio.run(main())
