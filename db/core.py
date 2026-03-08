"""
db/core.py — Umumiy utility funksiyalar, konstantalar va DB init for PostgreSQL.
"""
import asyncpg
from datetime import datetime, timezone, timedelta
import logging

from config import DATABASE_URL

logger = logging.getLogger(__name__)

# ─── Toshkent vaqti (UTC+5) ───────────────────
TZ_UZB = timezone(timedelta(hours=5))

# Global DB pool
pool: asyncpg.Pool = None

def get_pool() -> asyncpg.Pool:
    """Qolgan modullarda ishlatish uchun pool ni qaytaradi."""
    global pool
    if not pool:
        raise RuntimeError("Database pool is not initialized! Call init_db() first.")
    return pool

def now_local() -> str:
    """Hozirgi vaqtni Toshkent zonasida qaytaradi: '2026-03-01 00:26:00'"""
    return datetime.now(TZ_UZB).strftime("%Y-%m-%d %H:%M:%S")

def fmt_dt(raw: str | datetime | None) -> str:
    """Bazadagi sana/vaqt qatorini chiroyli ko'rinishga keltiradi."""
    if not raw:
        return "—"
    if isinstance(raw, datetime):
        return raw.strftime("%d.%m.%Y %H:%M")
    try:
        dt = datetime.fromisoformat(str(raw))
        return dt.strftime("%d.%m.%Y %H:%M")
    except Exception:
        return str(raw)


async def init_db():
    global pool
    try:
        pool = await asyncpg.create_pool(dsn=DATABASE_URL)
        logger.info(f"Connected to database: {DATABASE_URL}")
    except Exception as e:
        logger.error(f"Failed to connect to database at {DATABASE_URL}: {e}")
        raise

    async with pool.acquire() as conn:
        # Ustalar jadvali
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS masters (
                id SERIAL PRIMARY KEY,
                telegram_id BIGINT UNIQUE,
                full_name TEXT,
                username TEXT,
                phone TEXT DEFAULT '',
                workshop_name TEXT DEFAULT '',
                address TEXT DEFAULT NULL,
                reminder_time TEXT DEFAULT '09:00',
                reminders_enabled INTEGER DEFAULT 0,
                default_warranty_days INTEGER DEFAULT 0,
                is_active INTEGER DEFAULT 1,
                role TEXT DEFAULT 'boss',
                branch_name TEXT DEFAULT '',
                parent_id BIGINT DEFAULT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Orders jadvali
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS orders (
                id SERIAL PRIMARY KEY,
                master_id BIGINT,
                client_name TEXT NOT NULL,
                client_phone TEXT NOT NULL,
                car_model TEXT NOT NULL,
                car_number TEXT DEFAULT '',
                mileage TEXT DEFAULT '',
                problem TEXT NOT NULL,
                car_condition TEXT NOT NULL,
                price REAL NOT NULL,
                cost REAL DEFAULT 0,
                warranty TEXT NOT NULL,
                warranty_until DATE,
                next_service_date DATE,
                security_code TEXT DEFAULT '',
                status TEXT DEFAULT 'qabul_qilindi',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                completed_at TIMESTAMP,
                payment_method TEXT DEFAULT 'naqd',
                paid_amount REAL DEFAULT 0
            )
        """)
        logger.info("Database tables initialized successfully.")
