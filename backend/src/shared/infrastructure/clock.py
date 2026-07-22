"""Implementation của port thời gian."""

from datetime import UTC, datetime


class SystemClock:
    """Lấy thời gian từ đồng hồ hệ thống."""

    def now(self) -> datetime:
        return datetime.now(UTC)
