"""
db/stats.py — Statistika, tarix va Excel eksport funksiyalari (PostgreSQL).
"""
import io
import openpyxl
from datetime import datetime, timedelta
from openpyxl.styles import Font, Alignment, PatternFill

from db.core import TZ_UZB, get_pool


async def get_daily_stats(master_id: int | None = None, branch_name: str | None = None) -> dict:
    pool = get_pool()
    today = datetime.now(TZ_UZB).strftime("%Y-%m-%d")
    async with pool.acquire() as conn:
        cond_master = ""
        params = [today]
        if master_id:
            if branch_name:
                cond_master = f"AND master_id IN (SELECT telegram_id FROM masters WHERE (telegram_id = ${len(params) + 1} OR parent_id = ${len(params) + 2}) AND branch_name = ${len(params) + 3})"
                params.extend([master_id, master_id, branch_name])
            else:
                cond_master = f"AND master_id IN (SELECT telegram_id FROM masters WHERE telegram_id = ${len(params) + 1} OR parent_id = ${len(params) + 2})"
                params.extend([master_id, master_id])

        row1 = await conn.fetchrow(
            f"SELECT COUNT(*) as cnt, COALESCE(SUM(price), 0) as total, COALESCE(SUM(cost), 0) as cost_total FROM orders WHERE CAST(created_at AS DATE) = CAST($1 AS DATE) {cond_master}",
            *params
        )
        received_count, received_total, received_cost = row1['cnt'], row1['total'], row1['cost_total']

        row2 = await conn.fetchrow(
            f"SELECT COUNT(*) as cnt, COALESCE(SUM(price), 0) as total, COALESCE(SUM(cost), 0) as cost_total FROM orders WHERE CAST(completed_at AS DATE) = CAST($1 AS DATE) AND status = 'topshirildi' {cond_master}",
            *params
        )
        completed_count, completed_total, completed_cost = row2['cnt'], row2['total'], row2['cost_total']

        p_rows = await conn.fetch(
            f"SELECT payment_method, COALESCE(SUM(paid_amount), 0) as amt FROM orders WHERE CAST(completed_at AS DATE) = CAST($1 AS DATE) AND status = 'topshirildi' {cond_master} GROUP BY payment_method",
            *params
        )
        p_stats = {'naqd': 0.0, 'karta': 0.0, 'nasiya': 0.0}
        for r in p_rows:
            pm = r['payment_method'] or 'naqd'
            if pm in p_stats:
                p_stats[pm] += r['amt']

        return {
            "received_count": received_count,
            "received_total": received_total,
            "received_cost": received_cost,
            "completed_count": completed_count,
            "completed_total": completed_total,
            "completed_cost": completed_cost,
            "naqd": p_stats['naqd'],
            "karta": p_stats['karta'],
            "nasiya": p_stats['nasiya'],
        }


async def get_monthly_stats(master_id: int | None = None, branch_name: str | None = None) -> dict:
    pool = get_pool()
    month = datetime.now(TZ_UZB).strftime("%Y-%m")
    async with pool.acquire() as conn:
        cond_master = ""
        params = [month]
        if master_id:
            if branch_name:
                cond_master = f"AND master_id IN (SELECT telegram_id FROM masters WHERE (telegram_id = ${len(params) + 1} OR parent_id = ${len(params) + 2}) AND branch_name = ${len(params) + 3})"
                params.extend([master_id, master_id, branch_name])
            else:
                cond_master = f"AND master_id IN (SELECT telegram_id FROM masters WHERE telegram_id = ${len(params) + 1} OR parent_id = ${len(params) + 2})"
                params.extend([master_id, master_id])

        row1 = await conn.fetchrow(
            f"SELECT COUNT(*) as cnt, COALESCE(SUM(price), 0) as total, COALESCE(SUM(cost), 0) as cost_total FROM orders WHERE to_char(created_at, 'YYYY-MM') = $1 {cond_master}",
            *params
        )
        received_count, received_total, received_cost = row1['cnt'], row1['total'], row1['cost_total']

        row2 = await conn.fetchrow(
            f"SELECT COUNT(*) as cnt, COALESCE(SUM(price), 0) as total, COALESCE(SUM(cost), 0) as cost_total FROM orders WHERE to_char(completed_at, 'YYYY-MM') = $1 AND status = 'topshirildi' {cond_master}",
            *params
        )
        completed_count, completed_total, completed_cost = row2['cnt'], row2['total'], row2['cost_total']

        master_params = list(params[1:]) if master_id else []
        
        # fix param indexing for active_count query
        active_cond_master = ""
        if master_id:
            if branch_name:
                active_cond_master = "AND master_id IN (SELECT telegram_id FROM masters WHERE (telegram_id = $1 OR parent_id = $2) AND branch_name = $3)"
            else:
                active_cond_master = "AND master_id IN (SELECT telegram_id FROM masters WHERE telegram_id = $1 OR parent_id = $2)"

        row3 = await conn.fetchrow(
            f"SELECT COUNT(*) as cnt FROM orders WHERE status NOT IN ('topshirildi', 'bekor') {active_cond_master}",
            *master_params
        )
        active_count = row3['cnt']

        p_rows = await conn.fetch(
            f"SELECT payment_method, COALESCE(SUM(paid_amount), 0) as amt FROM orders WHERE to_char(completed_at, 'YYYY-MM') = $1 AND status = 'topshirildi' {cond_master} GROUP BY payment_method",
            *params
        )
        p_stats = {'naqd': 0.0, 'karta': 0.0, 'nasiya': 0.0}
        for r in p_rows:
            pm = r['payment_method'] or 'naqd'
            if pm in p_stats:
                p_stats[pm] += r['amt']

        return {
            "received_count": received_count,
            "received_total": received_total,
            "received_cost": received_cost,
            "completed_count": completed_count,
            "completed_total": completed_total,
            "completed_cost": completed_cost,
            "active_count": active_count,
            "naqd": p_stats['naqd'],
            "karta": p_stats['karta'],
            "nasiya": p_stats['nasiya'],
        }


async def get_all_time_stats(master_id: int | None = None, branch_name: str | None = None) -> dict:
    pool = get_pool()
    async with pool.acquire() as conn:
        cond_master = ""
        params = []
        if master_id:
            if branch_name:
                cond_master = "AND master_id IN (SELECT telegram_id FROM masters WHERE (telegram_id = $1 OR parent_id = $2) AND branch_name = $3)"
                params.extend([master_id, master_id, branch_name])
            else:
                cond_master = "AND master_id IN (SELECT telegram_id FROM masters WHERE telegram_id = $1 OR parent_id = $2)"
                params.extend([master_id, master_id])

        where_clause = f"WHERE 1=1 {cond_master}"

        row1 = await conn.fetchrow(
            f"SELECT COUNT(*) as cnt, COALESCE(SUM(price), 0) as total, COALESCE(SUM(cost), 0) as cost_total FROM orders {where_clause}",
            *params
        )
        received_count, received_total, received_cost = row1['cnt'], row1['total'], row1['cost_total']

        row2 = await conn.fetchrow(
            f"SELECT COUNT(*) as cnt, COALESCE(SUM(price), 0) as total, COALESCE(SUM(cost), 0) as cost_total FROM orders {where_clause} AND status = 'topshirildi'",
            *params
        )
        completed_count, completed_total, completed_cost = row2['cnt'], row2['total'], row2['cost_total']

        row3 = await conn.fetchrow(
            f"SELECT COUNT(*) as cnt FROM orders WHERE status NOT IN ('topshirildi', 'bekor') {cond_master}",
            *params
        )
        active_count = row3['cnt']

        p_rows = await conn.fetch(
            f"SELECT payment_method, COALESCE(SUM(paid_amount), 0) as amt FROM orders {where_clause} AND status = 'topshirildi' GROUP BY payment_method",
            *params
        )
        p_stats = {'naqd': 0.0, 'karta': 0.0, 'nasiya': 0.0}
        for r in p_rows:
            pm = r['payment_method'] or 'naqd'
            if pm in p_stats:
                p_stats[pm] += r['amt']

        return {
            "received_count": received_count,
            "received_total": received_total,
            "received_cost": received_cost,
            "completed_count": completed_count,
            "completed_total": completed_total,
            "completed_cost": completed_cost,
            "active_count": active_count,
            "naqd": p_stats['naqd'],
            "karta": p_stats['karta'],
            "nasiya": p_stats['nasiya'],
        }


async def get_history_by_period(master_id: int, period: str) -> list[dict]:
    """Admin panel uchun ustaning tarixini vaqt bo'yicha olish."""
    pool = get_pool()
    async with pool.acquire() as conn:
        cond_master = "AND master_id IN (SELECT telegram_id FROM masters WHERE telegram_id = $1 OR parent_id = $2)"
        params = [master_id, master_id]
        now = datetime.now(TZ_UZB)

        if period == "today":
            date_filter = f"AND CAST(completed_at AS DATE) = CAST(${len(params) + 1} AS DATE)"
            params.append(now.strftime("%Y-%m-%d"))
        elif period == "weekly":
            seven_days_ago = (now - timedelta(days=7)).replace(tzinfo=None)
            date_filter = f"AND completed_at >= ${len(params) + 1}"
            params.append(seven_days_ago)
        elif period == "monthly":
            date_filter = f"AND to_char(completed_at, 'YYYY-MM') = ${len(params) + 1}"
            params.append(now.strftime("%Y-%m"))
        elif period == "all":
            date_filter = ""
        else:
            return []

        sql = f"SELECT * FROM orders WHERE status = 'topshirildi' {date_filter} {cond_master} ORDER BY completed_at DESC"
        rows = await conn.fetch(sql, *params)
        return [dict(row) for row in rows]


async def export_orders_to_excel() -> bytes:
    """Barcha buyurtmalarni Excel faylga eksport qilish."""
    pool = get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch("SELECT * FROM orders ORDER BY created_at DESC")

        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = "Buyurtmalar"

        if not rows:
            buffer = io.BytesIO()
            wb.save(buffer)
            return buffer.getvalue()

        col_names = {
            "id": "Tartib #", "master_id": "Usta ID", "client_name": "Mijoz Ismi",
            "client_phone": "Telefon Raqam", "car_model": "Mashina Rusumi",
            "car_number": "Davlat Raqami", "problem": "Muammo/Xizmat turi",
            "car_condition": "Mashina Holati", "price": "Kelishilgan Summa",
            "cost": "Xarajat", "profit": "Sof Foyda", "warranty": "Kafolat",
            "warranty_until": "Kafolat Tugashi", "security_code": "Qo'shimcha izoh",
            "status": "Holati (Status)", "created_at": "Qabul qilingan sana",
            "completed_at": "Topshirilgan sana", "payment_method": "To'lov usuli",
            "paid_amount": "To'langan summa", "mileage": "Probeg", "next_service_date": "Keyingi xizmat"
        }

        original_keys = list(dict(rows[0]).keys())
        original_keys.append("profit")
        translated_headers = [col_names.get(k, k) for k in original_keys]
        ws.append(translated_headers)

        col_widths = {
            "A": 10, "B": 10, "C": 25, "D": 20, "E": 25,
            "F": 20, "G": 30, "H": 25, "I": 15, "J": 15,
            "K": 20, "L": 15, "M": 20, "N": 20, "O": 20,
            "P": 20, "Q": 20, "R": 20, "S": 20, "T": 20, "U": 20
        }
        for col_letter, width in col_widths.items():
            if col_letter in ws.column_dimensions:
                ws.column_dimensions[col_letter].width = width

        for cell in ws[1]:
            cell.font = Font(bold=True, color="FFFFFF")
            cell.fill = PatternFill(start_color="4F81BD", end_color="4F81BD", fill_type="solid")
            cell.alignment = Alignment(horizontal="center", vertical="center")

        total_price = 0
        total_cost = 0
        total_profit = 0

        for row in rows:
            row_dict = dict(row)
            if "price" in row_dict and row_dict["price"] is not None:
                row_dict["price"] = int(row_dict["price"])
            if "cost" in row_dict and row_dict["cost"] is not None:
                row_dict["cost"] = int(row_dict["cost"])
                
            # Convert datetime to string to avoid openpyxl timezone issues
            if "created_at" in row_dict and isinstance(row_dict.get("created_at"), datetime):
                row_dict["created_at"] = row_dict["created_at"].replace(tzinfo=None)
            if "completed_at" in row_dict and isinstance(row_dict.get("completed_at"), datetime):
                row_dict["completed_at"] = row_dict["completed_at"].replace(tzinfo=None)
            if "next_service_date" in row_dict and row_dict.get("next_service_date") is not None:
                row_dict["next_service_date"] = str(row_dict["next_service_date"])
            if "warranty_until" in row_dict and row_dict.get("warranty_until") is not None:
                row_dict["warranty_until"] = str(row_dict["warranty_until"])
                
            profit = row_dict.get("price", 0) - row_dict.get("cost", 0)
            row_dict["profit"] = profit
            total_price += row_dict.get("price", 0)
            total_cost += row_dict.get("cost", 0)
            total_profit += profit
            if "status" in row_dict and row_dict["status"]:
                row_dict["status"] = str(row_dict["status"]).replace("_", " ").capitalize()
            ws.append([row_dict.get(k, "") for k in original_keys])

        ws.append([""] * len(original_keys))
        jami_row = [""] * len(original_keys)
        price_idx = original_keys.index("price") if "price" in original_keys else -1
        cost_idx = original_keys.index("cost") if "cost" in original_keys else -1
        profit_idx = original_keys.index("profit") if "profit" in original_keys else -1

        if price_idx > 0:
            jami_row[price_idx - 1] = "JAMI YIG'INDI:"
        if price_idx != -1: jami_row[price_idx] = total_price
        if cost_idx != -1: jami_row[cost_idx] = total_cost
        if profit_idx != -1: jami_row[profit_idx] = total_profit
        ws.append(jami_row)

        total_r = ws.max_row
        for col_i in range(1, len(original_keys) + 1):
            c = ws.cell(row=total_r, column=col_i)
            c.font = Font(bold=True)
            if jami_row[col_i - 1] != "":
                c.fill = PatternFill(start_color="e6f2ff", end_color="e6f2ff", fill_type="solid")

        for row in ws.iter_rows(min_row=2, max_col=len(original_keys), max_row=len(rows) + 1):
            for cell in row:
                cell.alignment = Alignment(vertical="center", wrap_text=True)

        buffer = io.BytesIO()
        wb.save(buffer)

    return buffer.getvalue()
