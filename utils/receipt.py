import os
from io import BytesIO
from datetime import datetime
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib.colors import HexColor
from reportlab.pdfgen import canvas

def generate_receipt_pdf(order: dict, master_info: dict | None = None) -> BytesIO:
    """Elektron kvitansiya PDF formatida yaratish."""
    buffer = BytesIO()
    c = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4

    # ─── Ranglar ───
    PRIMARY = HexColor("#1a1a2e")
    ACCENT = HexColor("#16213e")
    HIGHLIGHT = HexColor("#0f3460")
    TEXT_DARK = HexColor("#1a1a2e")
    TEXT_LIGHT = HexColor("#ffffff")
    BORDER = HexColor("#e2e8f0")
    BG_LIGHT = HexColor("#f8fafc")
    GREEN = HexColor("#10b981")

    # ─── Usta ma'lumotlarini tayyorlash ───
    master_lines = []
    if master_info:
        ws = (master_info.get("workshop_name") or "").strip()
        addr = (master_info.get("address") or "").strip()
        ph = (master_info.get("phone") or "").strip()
        nm = (master_info.get("full_name") or "").strip()
        
        if ws: master_lines.append(ws)
        if addr: master_lines.append(addr)
        if ph: master_lines.append(f"Tel: {ph}")
        elif nm and not ws: master_lines.append(nm)

    header_h = 115 if master_lines else 100

    c.setFillColor(PRIMARY)
    c.rect(0, height - header_h, width, header_h, fill=True, stroke=False)

    c.setFillColor(GREEN)
    c.rect(0, height - header_h - 4, width, 4, fill=True, stroke=False)

    c.setFillColor(TEXT_LIGHT)
    c.setFont("Helvetica-Bold", 22)
    c.drawCentredString(width / 2, height - 40, "AVTOUSTAXONA XIZMATI")

    c.setFont("Helvetica", 11)
    c.drawCentredString(width / 2, height - 58, "Elektron Kvitansiya")

    if master_lines:
        c.setFont("Helvetica", 9)
        c.setFillColor(HexColor("#a8d8b0"))
        info_text = "  |  ".join(master_lines)
        c.drawCentredString(width / 2, height - 74, info_text)
        id_y = height - 91
    else:
        id_y = height - 80

    c.setFillColor(TEXT_LIGHT)
    c.setFont("Helvetica-Bold", 12)
    order_id = order.get("id", "—")
    c.drawCentredString(width / 2, id_y, f"Buyurtma #{order_id}")

    y = height - (header_h + 20)
    c.setFillColor(BG_LIGHT)
    c.roundRect(30, y - 10, width - 60, 35, 5, fill=True, stroke=False)
    c.setFillColor(TEXT_DARK)
    c.setFont("Helvetica", 10)

    created = order.get("created_at", datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    c.drawString(40, y + 5, f"📅  Sana:  {created}")
    c.drawRightString(width - 40, y + 5, f"📋  Status:  {order.get('status', 'faol').upper()}")

    y = y - 50
    c.setFillColor(HIGHLIGHT)
    c.setFont("Helvetica-Bold", 13)
    c.drawString(35, y, "👤  MIJOZ MA'LUMOTLARI")

    c.setStrokeColor(BORDER)
    c.setLineWidth(0.5)
    y -= 8
    c.line(35, y, width - 35, y)

    items_client = [
        ("Ism-sharif", order.get("client_name", "—")),
        ("Telefon raqam", order.get("client_phone", "—")),
    ]

    c.setFont("Helvetica", 11)
    for label, value in items_client:
        y -= 25
        c.setFillColor(HexColor("#64748b"))
        c.drawString(50, y, f"{label}:")
        c.setFillColor(TEXT_DARK)
        c.setFont("Helvetica-Bold", 11)
        c.drawString(200, y, str(value))
        c.setFont("Helvetica", 11)

    y -= 40
    c.setFillColor(HIGHLIGHT)
    c.setFont("Helvetica-Bold", 13)
    c.drawString(35, y, "🚗  AVTOULOV MA'LUMOTLARI")

    y -= 8
    c.setStrokeColor(BORDER)
    c.line(35, y, width - 35, y)

    items_device = [
        ("Mashina rusumi", order.get("car_model", "—")),
        ("Davlat raqami", order.get("car_number", "—")),
        ("Probeg (masofa)", order.get("mileage", "—")),
        ("Muammo qismi", order.get("problem", "—")),
        ("Mashina holati", order.get("car_condition", "—")),
    ]
    # Faqat qiymat bo'lmagan ho'lda qo'shimcha izohni qo'shamiz
    sec_code = (order.get("security_code") or "").strip()
    if sec_code:
        items_device.append(("Qo'shimcha izoh", sec_code))

    c.setFont("Helvetica", 11)
    for label, value in items_device:
        y -= 25
        c.setFillColor(HexColor("#64748b"))
        c.drawString(50, y, f"{label}:")
        c.setFillColor(TEXT_DARK)
        c.setFont("Helvetica-Bold", 11)
        val_str = str(value)
        if len(val_str) > 45:
            val_str = val_str[:45] + "..."
        c.drawString(200, y, val_str)
        c.setFont("Helvetica", 11)

    y -= 45
    c.setFillColor(GREEN)
    c.roundRect(30, y - 15, width - 60, 50, 8, fill=True, stroke=False)

    c.setFillColor(TEXT_LIGHT)
    c.setFont("Helvetica-Bold", 14)
    price = order.get("price", 0)
    c.drawString(50, y + 12, f"💰  Narx:  {price:,.0f} so'm")

    warranty = order.get("warranty", "—")
    c.drawRightString(width - 50, y + 12, f"🛡  Kafolat:  {warranty}")

    y -= 60
    c.setFillColor(HexColor("#94a3b8"))
    c.setFont("Helvetica", 9)
    c.drawCentredString(width / 2, y, "Bu kvitansiya ustaxona tomonidan avtomatik yaratilgan.")
    c.drawCentredString(width / 2, y - 14, "Iltimos, ushbu kvitansiyani xizmat muddati yakunlanguncha saqlang.")

    c.setFillColor(PRIMARY)
    c.rect(0, 0, width, 30, fill=True, stroke=False)
    c.setFillColor(GREEN)
    c.rect(0, 30, width, 3, fill=True, stroke=False)
    c.setFillColor(TEXT_LIGHT)
    c.setFont("Helvetica", 8)
    c.drawCentredString(width / 2, 10, "Telegram Bot orqali yaratilgan  •  Barcha huquqlar himoyalangan")

    c.save()
    buffer.seek(0)
    return buffer
