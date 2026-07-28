"""Cổng (port) mà tầng application của keyword phụ thuộc.

Mọi thứ ở đây là interface: implementation nằm ở tầng infrastructure. Nhờ vậy
domain và use case không biết identity, inbox, hay Claude tồn tại — chỉ biết các
hợp đồng này. Đây là ranh giới giữ module keyword độc lập.
"""

from dataclasses import dataclass
from typing import Protocol
from uuid import UUID

from src.modules.keyword.domain.value_objects.extracted_term import ExtractionResult


@dataclass(frozen=True)
class AgentInfo:
    """Thông tin tối thiểu về một nhân viên, lấy từ module identity."""

    user_id: UUID
    department_id: UUID | None
    role: str
    is_active: bool


class IWorkforceDirectory(Protocol):
    """Hỏi identity gián tiếp — kiểm phòng tồn tại/đang hoạt động."""

    async def department_exists_active(self, department_id: UUID) -> bool: ...


@dataclass(frozen=True)
class ConversationSnapshot:
    """Ảnh chụp tối thiểu một hội thoại inbox mà keyword cần để phân tích.

    ``is_awaiting`` = hội thoại đang CHO_PHAN (chưa có phòng). ``first_texts`` là
    nội dung text của vài tin inbound đầu của khách, đã sẵn cho LLM đọc.
    """

    conversation_id: UUID
    is_awaiting: bool
    first_texts: tuple[str, ...]


class IConversationDirectory(Protocol):
    """Đọc hội thoại/tin của inbox gián tiếp, không import inbox vào keyword.

    Chỉ implementation ở infrastructure mới biết inbox tồn tại.
    """

    async def get_snapshot(
        self, conversation_id: UUID, max_messages: int
    ) -> ConversationSnapshot | None:
        """Ảnh chụp hội thoại + tối đa ``max_messages`` tin inbound đầu; ``None`` nếu không có."""
        ...


class IConversationRouter(Protocol):
    """Tự phân một hội thoại về một phòng — chỗ DUY NHẤT keyword tác động ngược
    vào inbox.

    Implementation gọi use case phân chính thống của #1 với actor hệ thống, nên
    máy trạng thái/phân quyền/realtime của inbox giữ nguyên. Trả True nếu phân
    thành công.
    """

    async def assign_to_department(self, conversation_id: UUID, department_id: UUID) -> bool: ...


class ExtractorError(Exception):
    """LLM trích keyword thất bại (mạng/quota/timeout/parse).

    Use case bắt lỗi này và bỏ qua — phân tích lỗi không được làm hỏng nhận tin.
    """


class IKeywordExtractor(Protocol):
    """Trích cụm nhu cầu của khách từ nội dung vài tin đầu, bằng LLM.

    Ném ``ExtractorError`` khi thất bại; use case nuốt lỗi. Implementation dev:
    adapter Claude API. Fake tất định cho test.
    """

    async def extract(self, texts: tuple[str, ...]) -> ExtractionResult: ...
