"""Sự kiện timeline của hội thoại — nguồn của "dòng hệ thống" trong khung chat (BE-2).

Bảng riêng của module Hộp thư (``conversation_events``), KHÔNG dùng
``assignment_log`` của #3: bảng đó chỉ #3 ghi khi tự giao, không có loại sự kiện
hay người trước, và là nguồn "Được gán" của #5 — ghi thêm vào đó sẽ đổi nghĩa báo
cáo (quyết định của user, 2026-09-27).
"""

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from uuid import UUID

from src.shared.domain.identifiers import new_id


class ConversationEventKind(StrEnum):
    TAKEN = "TAKEN"  # nhân viên tự bấm Nhận việc
    AUTO_ASSIGNED = "AUTO_ASSIGNED"  # #3 tự giao
    ASSIGNED = "ASSIGNED"  # Manager/Admin giao khi chưa có ai
    REASSIGNED = "REASSIGNED"  # đổi từ người này sang người khác
    UNASSIGNED = "UNASSIGNED"  # gỡ người phụ trách


@dataclass(frozen=True, kw_only=True)
class ConversationEvent:
    id: UUID
    conversation_id: UUID
    kind: ConversationEventKind
    actor_user_id: UUID | None  # None = hệ thống
    from_user_id: UUID | None
    to_user_id: UUID | None
    created_at: datetime

    @classmethod
    def ghi(
        cls,
        conversation_id: UUID,
        kind: ConversationEventKind,
        now: datetime,
        actor_user_id: UUID | None = None,
        from_user_id: UUID | None = None,
        to_user_id: UUID | None = None,
    ) -> "ConversationEvent":
        return cls(
            id=new_id(),
            conversation_id=conversation_id,
            kind=kind,
            actor_user_id=actor_user_id,
            from_user_id=from_user_id,
            to_user_id=to_user_id,
            created_at=now,
        )
