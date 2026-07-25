"""Entity tệp đính kèm — ảnh/file đã tải về và lưu lại."""

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from src.modules.inbox.domain.value_objects.message_content import AttachmentKind
from src.shared.domain.entity import AggregateRoot


@dataclass(eq=False, kw_only=True)
class Attachment(AggregateRoot):
    """Một tệp đính kèm đã được tải về và lưu lại.

    URL gốc của nền tảng (``original_url``) hết hạn nên nội dung được tải về và
    lưu ở ``stored_path``; hệ thống phục vụ lại từ đó. Giữ ``original_url`` chỉ
    để truy vết nguồn.
    """

    message_id: UUID
    kind: AttachmentKind
    stored_path: str
    created_at: datetime
    original_url: str | None = None
    content_type: str | None = None
    size: int | None = None

    @classmethod
    def stored(
        cls,
        message_id: UUID,
        kind: AttachmentKind,
        stored_path: str,
        now: datetime,
        original_url: str | None = None,
        content_type: str | None = None,
        size: int | None = None,
    ) -> "Attachment":
        return cls(
            message_id=message_id,
            kind=kind,
            stored_path=stored_path,
            original_url=original_url,
            content_type=content_type,
            size=size,
            created_at=now,
        )
