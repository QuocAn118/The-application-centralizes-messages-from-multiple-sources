"""Nội dung một tin nhắn, đã chuẩn hoá khỏi định dạng riêng của từng nền tảng."""

from dataclasses import dataclass, field
from enum import StrEnum

from src.shared.domain.exceptions import DomainError


class AttachmentKind(StrEnum):
    """Loại tệp đính kèm mà #1 hỗ trợ."""

    IMAGE = "IMAGE"
    FILE = "FILE"


class EmptyMessageContentError(DomainError):
    """Tin nhắn phải có ít nhất text hoặc một tệp đính kèm."""

    def __init__(self) -> None:
        super().__init__(
            "Tin nhắn không có nội dung: cần ít nhất text hoặc một tệp đính kèm.",
            code="EMPTY_MESSAGE_CONTENT",
        )


@dataclass(frozen=True)
class AttachmentRef:
    """Tham chiếu tới một tệp đính kèm ở dạng chuẩn hoá.

    Hai chiều dùng khác nhau:
    - **Tin đến:** ``url`` là địa chỉ tạm do nền tảng cấp; use case tải về và
      lưu lại vì URL này hết hạn.
    - **Tin gửi đi:** nhân viên tải tệp thẳng lên nên chưa có URL — ``url`` để
      rỗng, use case lưu tệp trước rồi mới sinh URL công khai cho nền tảng tải.

    Value object này chỉ mô tả, không tự tải.
    """

    kind: AttachmentKind
    url: str = ""
    content_type: str | None = None


@dataclass(frozen=True)
class MessageContent:
    """Nội dung một tin: text và/hoặc danh sách tệp đính kèm.

    Chuẩn hoá tại đây để phần còn lại của hệ thống không phải biết Zalo hay
    Meta gói nội dung thế nào. Một tin rỗng hoàn toàn (không text, không đính
    kèm) bị chặn ngay — nó vô nghĩa và thường là dấu hiệu parse webhook sai.
    """

    text: str | None = None
    attachments: tuple[AttachmentRef, ...] = field(default_factory=tuple)

    def __post_init__(self) -> None:
        co_text = self.text is not None and self.text.strip() != ""
        if not co_text and not self.attachments:
            raise EmptyMessageContentError
