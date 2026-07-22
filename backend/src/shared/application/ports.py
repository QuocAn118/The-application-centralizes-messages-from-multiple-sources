"""Port cho các phụ thuộc bên ngoài mà tầng application cần."""

from datetime import datetime
from typing import Protocol


class IClock(Protocol):
    """Nguồn thời gian.

    Tách thành port để test kiểm soát được thời gian mà không cần chờ đợi
    hay giả lập đồng hồ hệ thống.
    """

    def now(self) -> datetime:
        """Trả về thời điểm hiện tại theo UTC, luôn kèm thông tin timezone."""
        ...
