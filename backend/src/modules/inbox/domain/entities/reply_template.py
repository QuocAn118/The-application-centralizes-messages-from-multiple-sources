"""Mẫu trả lời nhanh (BE-7). ``department_id = None`` = dùng chung mọi phòng.

Không đụng luồng gửi tin: FE chỉ chèn ``body`` vào ô soạn.
"""

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from src.shared.domain.exceptions import BusinessRuleViolationError
from src.shared.domain.identifiers import new_id

DAI_TIEU_DE = 80
DAI_NOI_DUNG = 4000


class TemplateInvalidError(BusinessRuleViolationError):
    def __init__(self) -> None:
        super().__init__(
            f"Mẫu cần tiêu đề (≤ {DAI_TIEU_DE} ký tự) và nội dung (≤ {DAI_NOI_DUNG} ký tự).",
            code="TEMPLATE_INVALID",
        )


def _gon(chu: str, toi_da: int) -> str:
    gon = chu.strip()
    if not gon or len(gon) > toi_da:
        raise TemplateInvalidError()
    return gon


@dataclass(kw_only=True)
class ReplyTemplate:
    id: UUID
    department_id: UUID | None
    title: str
    body: str
    created_at: datetime
    updated_at: datetime

    @classmethod
    def tao(
        cls, department_id: UUID | None, title: str, body: str, now: datetime
    ) -> "ReplyTemplate":
        return cls(
            id=new_id(),
            department_id=department_id,
            title=_gon(title, DAI_TIEU_DE),
            body=_gon(body, DAI_NOI_DUNG),
            created_at=now,
            updated_at=now,
        )

    def sua(self, title: str | None, body: str | None, now: datetime) -> None:
        if title is not None:
            self.title = _gon(title, DAI_TIEU_DE)
        if body is not None:
            self.body = _gon(body, DAI_NOI_DUNG)
        self.updated_at = now
