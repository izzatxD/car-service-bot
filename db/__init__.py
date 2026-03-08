"""
db/__init__.py — Barcha DB funksiyalarini markazlashtirib re-export qiladi.
Eski 'import database as db' yoki 'from database import ...' importlar shu yerga ko'chirilgan.
"""

# db/core.py dan
from db.core import (
    TZ_UZB,
    now_local,
    fmt_dt,
    init_db,
    get_pool,
)

# db/masters.py dan
from db.masters import (
    add_master,
    get_master,
    block_master,
    get_all_masters,
    update_master_info,
    get_workers,
    get_branches,
    add_worker,
    update_master_settings,
    get_masters_with_reminders,
)

# db/orders.py dan
from db.orders import (
    add_order,
    get_order,
    update_order_status,
    complete_order,
    get_debtors,
    pay_debt,
    search_orders,
    get_active_orders,
    get_all_orders,
    get_overdue_orders,
    get_weekly_history,
    get_next_service_reminders,
)

# db/stats.py dan
from db.stats import (
    get_daily_stats,
    get_monthly_stats,
    get_all_time_stats,
    get_history_by_period,
    export_orders_to_excel,
)

__all__ = [
    # core
    "DB_PATH", "TZ_UZB", "now_local", "fmt_dt", "init_db",
    # masters
    "add_master", "get_master", "block_master", "get_all_masters",
    "update_master_info", "get_workers", "get_branches", "add_worker",
    "update_master_settings", "get_masters_with_reminders",
    # orders
    "add_order", "get_order", "update_order_status", "complete_order",
    "get_debtors", "pay_debt", "search_orders", "get_active_orders",
    "get_all_orders", "get_overdue_orders", "get_weekly_history",
    "get_next_service_reminders",
    # stats
    "get_daily_stats", "get_monthly_stats", "get_all_time_stats",
    "get_history_by_period", "export_orders_to_excel",
]
