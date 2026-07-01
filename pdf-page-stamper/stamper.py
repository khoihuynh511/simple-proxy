"""Logic dong dau so trang len file PDF.

Tach rieng khoi giao dien (app.py) de co the kiem thu doc lap.
"""

import io
import os

from pypdf import PdfReader, PdfWriter
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas

from fonts import resolve_font_path

MM_TO_PT = 2.834645669

POSITIONS = [
    "Header - Trai",
    "Header - Giua",
    "Header - Phai",
    "Footer - Trai",
    "Footer - Giua",
    "Footer - Phai",
]

_registered_fonts = set()


def ensure_font_registered(font_name: str) -> None:
    if font_name in _registered_fonts:
        return
    path = resolve_font_path(font_name)
    pdfmetrics.registerFont(TTFont(font_name, path))
    _registered_fonts.add(font_name)


def build_stamp_text(customer_name: str, file_name: str, page_num: int, total_pages: int) -> str:
    return f"{customer_name} | {file_name} | Trang {page_num}/{total_pages}"


def compute_xy(position: str, page_width: float, page_height: float,
                text_width: float, font_size: float,
                margin_x_pt: float, margin_y_pt: float):
    if position not in POSITIONS:
        raise ValueError(f"Vi tri khong hop le: {position}")

    is_header = position.startswith("Header")
    y = (page_height - margin_y_pt - font_size) if is_header else margin_y_pt

    if position.endswith("Trai"):
        x = margin_x_pt
    elif position.endswith("Phai"):
        x = page_width - margin_x_pt - text_width
    else:
        x = (page_width - text_width) / 2
    return x, y


def get_page_count(pdf_path: str) -> int:
    reader = PdfReader(pdf_path)
    return len(reader.pages)


def stamp_pdf(input_path: str, output_path: str, customer_name: str,
              position: str, font_name: str, font_size: float,
              margin_x_mm: float, margin_y_mm: float) -> None:
    """Doc input_path, dong dau so trang len tung trang, ghi ra output_path.

    File goc (input_path) khong bi thay doi.
    """
    ensure_font_registered(font_name)
    margin_x_pt = margin_x_mm * MM_TO_PT
    margin_y_pt = margin_y_mm * MM_TO_PT

    reader = PdfReader(input_path)
    total_pages = len(reader.pages)
    file_name = os.path.basename(input_path)
    writer = PdfWriter()

    for i, page in enumerate(reader.pages, start=1):
        width = float(page.mediabox.width)
        height = float(page.mediabox.height)

        text = build_stamp_text(customer_name, file_name, i, total_pages)
        text_width = pdfmetrics.stringWidth(text, font_name, font_size)
        x, y = compute_xy(position, width, height, text_width, font_size,
                            margin_x_pt, margin_y_pt)

        buf = io.BytesIO()
        c = canvas.Canvas(buf, pagesize=(width, height))
        c.setFont(font_name, font_size)
        c.drawString(x, y, text)
        c.save()
        buf.seek(0)

        overlay_page = PdfReader(buf).pages[0]
        page.merge_page(overlay_page)
        writer.add_page(page)

    out_dir = os.path.dirname(output_path)
    if out_dir:
        os.makedirs(out_dir, exist_ok=True)
    with open(output_path, "wb") as f:
        writer.write(f)
