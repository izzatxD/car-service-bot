"""
db/orders.py — Buyurtmalar (orders) bilan bog'liq barcha DB funksiyalari (PostgreSQL).
"""
import os
from datetime import datetime, timedelta

from db.core import now_local, TZ_UZB, get_pool


async def add_order(
    master_id: int, client_name: str, client_phone: str,
    car_model: str, car_number: str, mileage: str, problem: str, car_condition: str,
    price: float, cost: float, warranty: str, warranty_until: str | None, next_service_date: str | None,
    security_code: str = ""
) -> int:
    """Yangi buyurtma qo'shish."""
    pool = get_pool()
    w_until = datetime.strptime(warranty_until, "%Y-%m-%d").date() if warranty_until else None
    n_service = datetime.strptime(next_service_date, "%Y-%m-%d").date() if next_service_date else None
    
    async with pool.acquire() as conn:
        row_id = await conn.fetchval(
            """INSERT INTO orders (
                master_id, client_name, client_phone, car_model, car_number, mileage,
                problem, car_condition, price, cost, warranty, warranty_until, next_service_date, security_code, created_at
               ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14, $15)
               RETURNING id""",
            master_id, client_name, client_phone, car_model, car_number, mileage,
            problem, car_condition, price, cost, warranty, w_until, n_service, security_code, datetime.now(TZ_UZB).replace(tzinfo=None)
        )
        return row_id


async def get_order(order_id: int, master_id: int | None = None) -> dict | None:
    """Buyurtmani id (va master_id) bo'yicha olish."""
    pool = get_pool()
    async with pool.acquire() as conn:
        query = "SELECT * FROM orders WHERE id = $1"
        params = [order_id]
        if master_id:
            query += " AND master_id = $2"
            params.append(master_id)
        row = await conn.fetchrow(query, *params)
        return dict(row) if row else None


async def update_order_status(order_id: int, status: str, master_id: int | None = None):
    """Buyurtma holatini yangilash — completed_at ni Toshkent vaqtida saqlaydi."""
    pool = get_pool()
    async with pool.acquire() as conn:
        query = "UPDATE orders SET status = $1"
        params = [status]
        if status == "topshirildi":
            query += f", completed_at = ${len(params) + 1}"
            params.append(datetime.now(TZ_UZB).replace(tzinfo=None))
        
        query += f" WHERE id = ${len(params) + 1}"
        params.append(order_id)
        
        if master_id is not None:
            query += f" AND master_id = ${len(params) + 1}"
            params.append(master_id)
            
        await conn.execute(query, *params)


async def complete_order(order_id: int, payment_method: str, paid_amount: float, master_id: int | None = None):
    """Buyurtmani topshirish va to'lov usulini saqlash."""
    pool = get_pool()
    async with pool.acquire() as conn:
        query = "UPDATE orders SET status = 'topshirildi', completed_at = $1, payment_method = $2, paid_amount = $3 WHERE id = $4"
        params = [datetime.now(TZ_UZB).replace(tzinfo=None), payment_method, paid_amount, order_id]
        if master_id is not None:
            query += " AND master_id = $5"
            params.append(master_id)
        await conn.execute(query, *params)


async def get_debtors(master_id: int | None = None, branch_name: str | None = None, is_personal: bool = False) -> list[dict]:
    """Qarzdorlarni ro'yxatini olish (paid_amount < price)."""
    pool = get_pool()
    async with pool.acquire() as conn:
        sql = "SELECT * FROM orders WHERE status = 'topshirildi' AND payment_method = 'nasiya' AND paid_amount < price"
        params = []
        if master_id:
            if is_personal:
                sql += " AND master_id = $1"
                params.append(master_id)
            elif branch_name:
                sql += " AND master_id IN (SELECT telegram_id FROM masters WHERE (telegram_id = $1 OR parent_id = $2) AND branch_name = $3)"
                params.extend([master_id, master_id, branch_name])
            else:
                sql += " AND master_id IN (SELECT telegram_id FROM masters WHERE telegram_id = $1 OR parent_id = $2)"
                params.extend([master_id, master_id])
        sql += " ORDER BY completed_at DESC"
        rows = await conn.fetch(sql, *params)
        return [dict(row) for row in rows]


async def pay_debt(order_id: int, additional_amount: float, master_id: int | None = None) -> bool:
    """Nasiyani to'lash."""
    pool = get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow("SELECT paid_amount, price FROM orders WHERE id = $1", order_id)
        if not row:
            return False
        total_paid = row['paid_amount'] + additional_amount
        query = "UPDATE orders SET paid_amount = $1 WHERE id = $2"
        params = [total_paid, order_id]
        if master_id is not None:
            query += " AND master_id = $3"
            params.append(master_id)
        await conn.execute(query, *params)
        return total_paid >= row['price']


async def search_orders(query: str, master_id: int | None = None, branch_name: str | None = None) -> list[dict]:
    """Mijoz tarixini Ism, Telefon, Raqam, Model yoki Sana orqali qidirish."""
    pool = get_pool()
    months_map = {
        "yanvar": "01", "yan": "01", "fevral": "02", "fev": "02", "mart": "03", "mar": "03",
        "aprel": "04", "apr": "04", "may": "05", "iyun": "06", "iyul": "07", "avgust": "08",
        "avg": "08", "sentabr": "09", "sen": "09", "oktabr": "10", "okt": "10",
        "noyabr": "11", "noy": "11", "dekabr": "12", "dek": "12"
    }
    lower_q = query.lower().strip()
    search_date = ""
    if "." in query:
        parts = query.split(".")
        if len(parts) >= 2 and parts[0].isdigit() and parts[1].isdigit():
            day = parts[0].zfill(2)
            month = parts[1].zfill(2)
            search_date = f"-{month}-{day}"
    elif lower_q in months_map:
        search_date = f"-{months_map[lower_q]}-"
    else:
        for m_name, m_num in months_map.items():
            if m_name in lower_q:
                day_part = lower_q.replace(m_name, "").strip()
                if day_part.isdigit():
                    day = day_part.zfill(2)
                    search_date = f"-{m_num}-{day}"
                else:
                    search_date = f"-{m_num}-"
                break

    async with pool.acquire() as conn:
        sql = """
            SELECT * FROM orders 
            WHERE (
                client_name ILIKE $1 
                OR client_phone ILIKE $2 
                OR car_number ILIKE $3 
                OR car_model ILIKE $4
        """
        params = [f"%{query}%", f"%{query}%", f"%{query}%", f"%{query}%"]
        
        if search_date:
            sql += f" OR CAST(created_at AS TEXT) LIKE ${len(params) + 1} OR CAST(completed_at AS TEXT) LIKE ${len(params) + 2}"
            params.extend([f"%{search_date}%", f"%{search_date}%"])
            
        sql += ")"
        
        if master_id:
            if branch_name:
                sql += f" AND master_id IN (SELECT telegram_id FROM masters WHERE (telegram_id = ${len(params) + 1} OR parent_id = ${len(params) + 2}) AND branch_name = ${len(params) + 3})"
                params.extend([master_id, master_id, branch_name])
            else:
                sql += f" AND master_id IN (SELECT telegram_id FROM masters WHERE telegram_id = ${len(params) + 1} OR parent_id = ${len(params) + 2})"
                params.extend([master_id, master_id])
                
        sql += " ORDER BY created_at DESC LIMIT 20"
        rows = await conn.fetch(sql, *params)
        return [dict(row) for row in rows]


async def get_active_orders(master_id: int | None = None, branch_name: str | None = None, is_personal: bool = False) -> list[dict]:
    """Faol buyurtmalarni (topshirilmagan / bekor qilinmagan) olish."""
    pool = get_pool()
    async with pool.acquire() as conn:
        sql = "SELECT * FROM orders WHERE status NOT IN ('topshirildi', 'bekor')"
        params = []
        if master_id:
            if is_personal:
                sql += " AND master_id = $1"
                params.append(master_id)
            elif branch_name:
                sql += " AND master_id IN (SELECT telegram_id FROM masters WHERE (telegram_id = $1 OR parent_id = $2) AND branch_name = $3)"
                params.extend([master_id, master_id, branch_name])
            else:
                sql += " AND master_id IN (SELECT telegram_id FROM masters WHERE telegram_id = $1 OR parent_id = $2)"
                params.extend([master_id, master_id])
        sql += " ORDER BY created_at DESC"
        rows = await conn.fetch(sql, *params)
        return [dict(row) for row in rows]


async def get_all_orders(master_id: int | None = None, branch_name: str | None = None) -> list[dict]:
    """Barcha mijozlarni (buyurtmalarni) ro'yxatini olish."""
    pool = get_pool()
    async with pool.acquire() as conn:
        sql = "SELECT * FROM orders"
        params = []
        if master_id:
            if branch_name:
                sql += " WHERE master_id IN (SELECT telegram_id FROM masters WHERE (telegram_id = $1 OR parent_id = $2) AND branch_name = $3)"
                params.extend([master_id, master_id, branch_name])
            else:
                sql += " WHERE master_id IN (SELECT telegram_id FROM masters WHERE telegram_id = $1 OR parent_id = $2)"
                params.extend([master_id, master_id])
        sql += " ORDER BY created_at DESC"
        rows = await conn.fetch(sql, *params)
        return [dict(row) for row in rows]


async def get_overdue_orders(master_id: int) -> list[dict]:
    """Ustaning 3 kundan oshgan, lekin hali topshirilmagan ishlarini olish."""
    pool = get_pool()
    async with pool.acquire() as conn:
        query = """
            SELECT * FROM orders 
            WHERE master_id IN (SELECT telegram_id FROM masters WHERE telegram_id = $1 OR parent_id = $2) 
              AND status != 'topshirildi' 
              AND status != 'bekor_qilindi'
              AND created_at <= (NOW() - INTERVAL '3 days')
            ORDER BY created_at ASC
        """
        rows = await conn.fetch(query, master_id, master_id)
        return [dict(row) for row in rows]


async def get_weekly_history(master_id: int | None = None, branch_name: str | None = None) -> list[dict]:
    """Oxirgi 7 kunda topshirilgan buyurtmalarni olish."""
    pool = get_pool()
    async with pool.acquire() as conn:
        seven_days_ago = (datetime.now(TZ_UZB).replace(tzinfo=None) - timedelta(days=7))
        sql = "SELECT * FROM orders WHERE status = 'topshirildi' AND completed_at >= $1"
        params = [seven_days_ago]
        if master_id:
            if branch_name:
                sql += " AND master_id IN (SELECT telegram_id FROM masters WHERE (telegram_id = $2 OR parent_id = $3) AND branch_name = $4)"
                params.extend([master_id, master_id, branch_name])
            else:
                sql += " AND master_id IN (SELECT telegram_id FROM masters WHERE telegram_id = $2 OR parent_id = $3)"
                params.extend([master_id, master_id])
        sql += " ORDER BY completed_at DESC"
        rows = await conn.fetch(sql, *params)
        return [dict(row) for row in rows]


async def get_next_service_reminders() -> list[dict]:
    """Bugun keyingi tashrif muddati kelgan ishlarni qaytaradi."""
    pool = get_pool()
    today = datetime.now(TZ_UZB).date()
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            "SELECT * FROM orders WHERE CAST(next_service_date AS DATE) = $1",
            today
        )
        return [dict(row) for row in rows]
