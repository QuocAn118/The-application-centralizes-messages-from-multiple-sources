"""Lỗi dùng chung cho các adapter kênh."""


class WebhookSignatureError(ValueError):
    """Chữ ký webhook không hợp lệ — payload không đáng tin, phải từ chối.

    Cố ý là ``ValueError`` rỗng thông tin: router bắt để trả 403 mà không lộ lý
    do cụ thể (RB-3). Đặt ở chỗ dùng chung để mọi adapter (Zalo, Meta, và nền
    tảng thêm sau) ném cùng một loại, router chỉ cần bắt một exception.
    """
