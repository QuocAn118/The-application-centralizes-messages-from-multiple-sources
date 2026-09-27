"""Ghi chú nội bộ về một khách (BE-5), giới hạn theo PHÒNG của người viết.

``department_id`` = phòng người viết TẠI LÚC VIẾT (quyết định GĐ1 §10.4): khách
nhắn nhiều phòng thì mỗi phòng chỉ thấy ghi chú của phòng mình. Admin không thuộc
phòng → ghi chú Admin viết có ``department_id = None``, chỉ Admin thấy.
"""

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from src.shared.domain.exceptions import BusinessRuleViolationError
from src.shared.domain.identifiers import new_id

DAI_TOI_DA = 2000


class NoteBodyInvalidError(BusinessRuleViolationError):
    def __init__(self) -> None:
        super().__init__(
            f"Ghi chú phải có nội dung và không dài quá {DAI_TOI_DA} ký tự.",
            code="NOTE_BODY_INVALID",
        )


@dataclass(frozen=True, kw_only=True)
class CustomerNote:
    id: UUID
    customer_id: UUID
    department_id: UUID | None
    author_id: UUID
    body: str
    created_at: datetime

    @classmethod
    def viet(
        cls,
        customer_id: UUID,
        department_id: UUID | None,
        author_id: UUID,
        body: str,
        now: datetime,
    ) -> "CustomerNote":
        noi_dung = body.strip()
        if not noi_dung or len(noi_dung) > DAI_TOI_DA:
            raise NoteBodyInvalidError()
        return cls(
            id=new_id(),
            customer_id=customer_id,
            department_id=department_id,
            author_id=author_id,
            body=noi_dung,
            created_at=now,
        )
