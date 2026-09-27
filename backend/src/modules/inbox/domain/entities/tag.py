"""Nhãn khách dùng chung toàn công ty (BE-6, GĐ1 §10.1 #3).

Màu chỉ được lấy từ bảng màu đã kiểm tương phản của design system (``swatch-1..8``)
— không nhận mã màu tự do. Không xoá cứng: ngừng dùng thì nhãn biến khỏi ô chọn,
khách đang gắn vẫn giữ (dữ liệu cũ không tự mất).
"""

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from src.shared.domain.exceptions import BusinessRuleViolationError
from src.shared.domain.identifiers import new_id

MAU_HOP_LE = frozenset(f"swatch-{i}" for i in range(1, 9))
DAI_TEN_TOI_DA = 40


class TagInvalidError(BusinessRuleViolationError):
    def __init__(self, message: str, code: str) -> None:
        super().__init__(message, code=code)


def _ten_hop_le(ten: str) -> str:
    # Gộp khoảng trắng thừa: "  VIP   mới " và "VIP mới" là một nhãn.
    gon = " ".join(ten.split())
    if not gon or len(gon) > DAI_TEN_TOI_DA:
        raise TagInvalidError(
            f"Tên nhãn phải có và không dài quá {DAI_TEN_TOI_DA} ký tự.", "TAG_NAME_INVALID"
        )
    return gon


def _mau_hop_le(mau: str) -> str:
    if mau not in MAU_HOP_LE:
        raise TagInvalidError("Màu nhãn phải chọn từ bảng màu có sẵn.", "TAG_COLOR_INVALID")
    return mau


@dataclass(kw_only=True)
class Tag:
    id: UUID
    name: str
    color: str
    is_active: bool
    created_at: datetime

    @classmethod
    def tao(cls, name: str, color: str, now: datetime) -> "Tag":
        return cls(
            id=new_id(),
            name=_ten_hop_le(name),
            color=_mau_hop_le(color),
            is_active=True,
            created_at=now,
        )

    def sua(self, name: str | None, color: str | None, is_active: bool | None) -> None:
        if name is not None:
            self.name = _ten_hop_le(name)
        if color is not None:
            self.color = _mau_hop_le(color)
        if is_active is not None:
            self.is_active = is_active
