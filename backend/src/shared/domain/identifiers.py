"""Sinh định danh cho entity."""

from uuid import UUID

import uuid_utils


def new_id() -> UUID:
    """Sinh UUID phiên bản 7 — ngẫu nhiên nhưng sắp xếp được theo thời gian.

    Thư viện chuẩn của Python 3.13 chỉ có tới ``uuid5``; ``uuid.uuid7()`` xuất
    hiện từ Python 3.14. Gói ``uuid_utils`` trả về kiểu UUID riêng của nó nên
    phải chuyển về ``uuid.UUID`` của thư viện chuẩn để SQLAlchemy và Pydantic
    làm việc được.

    Khi dự án nâng lên Python 3.14, chỉ cần đổi thân hàm này thành
    ``return uuid.uuid7()`` và gỡ dependency ``uuid-utils``.
    """
    return UUID(bytes=uuid_utils.uuid7().bytes)
