"""
db/masters.py — Ustalar (masters) bilan bog'liq barcha DB funksiyalari (PostgreSQL).
"""
import logging
from db.core import get_pool

logger = logging.getLogger(__name__)

async def add_master(telegram_id: int, full_name: str | None = None, username: str | None = None) -> bool:
    """Yangi ustani qo'shish yoki ma'lumotlarini yangilash."""
    pool = get_pool()
    try:
        async with pool.acquire() as conn:
            await conn.execute(
                """INSERT INTO masters (telegram_id, full_name, username, is_active) 
                   VALUES ($1, $2, $3, 1) 
                   ON CONFLICT (telegram_id) DO UPDATE SET 
                   full_name = COALESCE(EXCLUDED.full_name, masters.full_name),
                   username = COALESCE(EXCLUDED.username, masters.username),
                   is_active = 1""", 
                telegram_id, full_name, username
            )
        return True
    except Exception as e:
        logger.error(f"Error in add_master: {e}")
        return False


async def get_master(telegram_id: int) -> dict | None:
    """Ustani ID bo'yicha olish."""
    pool = get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow("SELECT * FROM masters WHERE telegram_id = $1", telegram_id)
        return dict(row) if row else None


async def block_master(telegram_id: int):
    """Ustani bloklash."""
    pool = get_pool()
    async with pool.acquire() as conn:
        await conn.execute("UPDATE masters SET is_active = 0 WHERE telegram_id = $1", telegram_id)


async def get_all_masters() -> list[dict]:
    """Barcha ustalarni ro'yxatini olish."""
    pool = get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch("SELECT * FROM masters ORDER BY created_at DESC")
        return [dict(row) for row in rows]


async def update_master_info(telegram_id: int, phone: str = "", workshop_name: str = "") -> bool:
    """Ustaning ixtiyoriy kontakt ma'lumotlarini yangilash (PDF uchun)."""
    pool = get_pool()
    try:
        async with pool.acquire() as conn:
            await conn.execute(
                "UPDATE masters SET phone = $1, workshop_name = $2 WHERE telegram_id = $3",
                phone.strip(), workshop_name.strip(), telegram_id
            )
        return True
    except Exception as e:
        logger.error(f"Error in update_master_info: {e}")
        return False


async def get_workers(parent_id: int) -> list[dict]:
    """Boshliqning barcha shogirdlarini (ishchilarni) olish."""
    pool = get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch("SELECT * FROM masters WHERE parent_id = $1 ORDER BY created_at DESC", parent_id)
        return [dict(row) for row in rows]


async def get_branches(master_id: int) -> list[str]:
    """Boshliq va uning shogirdlariga tegishli (mavjud) barcha filiallarni olish."""
    pool = get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            "SELECT DISTINCT branch_name FROM masters WHERE (telegram_id = $1 OR parent_id = $2) AND branch_name != '' AND branch_name IS NOT NULL", 
            master_id, master_id
        )
        return [r['branch_name'] for r in rows if r['branch_name']]


async def add_worker(parent_id: int, telegram_id: int, full_name: str, phone: str, branch_name: str) -> bool:
    """Boshliq o'ziga yangi shogird qo'shishi."""
    pool = get_pool()
    try:
        async with pool.acquire() as conn:
            await conn.execute(
                """INSERT INTO masters (telegram_id, full_name, phone, role, parent_id, branch_name, is_active) 
                   VALUES ($1, $2, $3, 'worker', $4, $5, 1)""", 
                telegram_id, full_name, phone, parent_id, branch_name
            )
        return True
    except Exception as e:
        logger.error(f"Error in add_worker: {e}")
        return False


async def update_master_settings(telegram_id: int, **kwargs) -> bool:
    """Ustaning o'zgartirilgan sozlamalarini (settings) bazaga yozish."""
    valid_keys = ['workshop_name', 'address', 'phone', 'reminder_time', 'default_warranty_days', 'reminders_enabled']
    updates = []
    params = []
    
    for key, value in kwargs.items():
        if key in valid_keys:
            params.append(value)
            updates.append(f"{key} = ${len(params)}")
            
    if not updates:
        return False
        
    pool = get_pool()
    try:
        async with pool.acquire() as conn:
            params.append(telegram_id)
            sql = f"UPDATE masters SET {', '.join(updates)} WHERE telegram_id = ${len(params)}"
            await conn.execute(sql, *params)
        return True
    except Exception as e:
        logger.error(f"Error in update_master_settings: {e}")
        return False


async def get_masters_with_reminders() -> list[dict]:
    """Eslatmalarni yoqib qo'ygan ustalarni olish."""
    pool = get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch("SELECT * FROM masters WHERE reminders_enabled = 1 AND is_active = 1")
        return [dict(row) for row in rows]
