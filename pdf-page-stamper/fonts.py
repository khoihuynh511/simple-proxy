"""Font resolution cho PDF Page Stamper.

Chi dung font co san tren Windows de dam bao hien thi dung dau tieng Viet
(cac font Base14 mac dinh cua PDF khong ho tro day du dau tieng Viet).
"""

import os

# Ten hien thi tren giao dien -> ten file font trong C:\Windows\Fonts
FONT_FILES = {
    "Arial": "arial.ttf",
    "Times New Roman": "times.ttf",
    "Tahoma": "tahoma.ttf",
    "Calibri": "calibri.ttf",
}

FONT_NAMES = list(FONT_FILES.keys())


def resolve_font_path(font_name: str) -> str:
    if font_name not in FONT_FILES:
        raise ValueError(f"Font khong duoc ho tro: {font_name}")

    fonts_dir = os.path.join(os.environ.get("WINDIR", "C:\\Windows"), "Fonts")
    path = os.path.join(fonts_dir, FONT_FILES[font_name])
    if not os.path.isfile(path):
        raise FileNotFoundError(
            f"Khong tim thay file font '{FONT_FILES[font_name]}' trong {fonts_dir}.\n"
            f"Vui long chon font khac hoac kiem tra lai may co cai font nay khong."
        )
    return path
