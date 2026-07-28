"""Notifier đơn từ cho hrm — bản tối thiểu ghi log.

Spec §9: đề yêu cầu Staff biết khi đơn được duyệt/từ chối. #4 làm tối thiểu —
ghi một tín hiệu vào log; client lấy trạng thái qua REST (polling). Đẩy realtime
thật (tái dùng WebSocket của #1 qua một cầu nối ở composition root) là nợ đã ghi,
làm khi cần. Giữ ``INotifier`` làm ranh giới nên nâng cấp sau không đụng use case.
"""

import logging
from uuid import UUID

logger = logging.getLogger(__name__)


class LogNotifier:
    """Implementation ``INotifier`` ghi tín hiệu thay đổi đơn vào log."""

    async def notify_request_changed(
        self, request_id: UUID, recipient_user_id: UUID, change: str
    ) -> None:
        logger.info(
            "Đơn có thay đổi",
            extra={
                "request_id": str(request_id),
                "recipient_user_id": str(recipient_user_id),
                "change": change,
            },
        )
