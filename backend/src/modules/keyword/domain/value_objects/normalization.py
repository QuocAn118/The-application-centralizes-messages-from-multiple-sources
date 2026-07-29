"""Chuẩn hoá text để khớp từ khoá không phụ thuộc dấu và hoa thường.

Dùng chung cho ``Keyword`` (danh mục Manager nhập) và ``ExtractedTerm`` (cụm LLM
trích): cả hai phải chuẩn hoá theo cùng một cách thì khớp mới đúng. Chỉ dùng thư
viện chuẩn (``unicodedata``) — domain không phụ thuộc gói ngoài.
"""

import unicodedata


def chuan_hoa(text: str) -> str:
    """Đưa text về dạng khớp: bỏ dấu tiếng Việt, thường hoá, gộp khoảng trắng.

    Ví dụ: ``"Bảo Hành"`` và ``"bao hanh"`` đều thành ``"bao hanh"``. ``đ``/``Đ``
    được xử lý riêng vì ``unicodedata`` không tách dấu của chúng.
    """
    # Tách ký tự tổ hợp rồi bỏ các dấu (combining marks).
    tach = unicodedata.normalize("NFD", text)
    khong_dau = "".join(c for c in tach if unicodedata.category(c) != "Mn")
    # đ/Đ không phải tổ hợp NFD nên xử lý tay.
    khong_dau = khong_dau.replace("đ", "d").replace("Đ", "D")
    # Thường hoá và gộp mọi cụm khoảng trắng thành một dấu cách.
    return " ".join(khong_dau.lower().split())
