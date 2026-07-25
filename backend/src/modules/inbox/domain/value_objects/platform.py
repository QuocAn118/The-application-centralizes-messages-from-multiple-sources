"""Nền tảng nhắn tin mà một kênh thuộc về."""

from enum import StrEnum


class Platform(StrEnum):
    """Các nền tảng OmniChat kết nối.

    Kế thừa ``StrEnum`` để đọc thẳng từ cơ sở dữ liệu và ghi ra JSON mà không
    phải chuyển đổi. Danh sách này mở rộng được: thêm một nền tảng mới chỉ là
    thêm một giá trị ở đây kèm một adapter tương ứng ở tầng infrastructure —
    domain và use case không đổi.
    """

    ZALO = "ZALO"
    FACEBOOK = "FACEBOOK"
    INSTAGRAM = "INSTAGRAM"
