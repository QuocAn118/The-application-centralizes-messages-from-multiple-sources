"""Entity từ khoá — một cụm đặc trưng của một phòng ban, do Manager định nghĩa."""

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from src.modules.keyword.domain.value_objects.normalization import chuan_hoa
from src.shared.domain.entity import AggregateRoot
from src.shared.domain.exceptions import BusinessRuleViolationError


class EmptyKeywordError(BusinessRuleViolationError):
    """Từ khoá không được rỗng."""

    def __init__(self) -> None:
        super().__init__(
            "Từ khoá không được để trống.",
            code="EMPTY_KEYWORD",
        )


@dataclass(eq=False, kw_only=True)
class Keyword(AggregateRoot):
    """Một từ khoá gắn với đúng một phòng ban.

    ``text`` là dạng gốc Manager nhập (hiển thị lại); ``normalized`` là dạng đã
    bỏ dấu/thường hoá để khớp với cụm nhu cầu LLM trích. ``department_id`` là
    tham chiếu UUID sang identity — cố ý không khoá ngoại, giữ module độc lập.
    Ràng buộc "một từ khoá (normalized) chỉ có một lần trong một phòng" đảm bảo
    ở tầng use case + unique index DB.
    """

    department_id: UUID
    text: str
    normalized: str
    created_at: datetime
    updated_at: datetime

    @staticmethod
    def _chuan_hoa_text(text: str) -> tuple[str, str]:
        goc = text.strip()
        if not goc:
            raise EmptyKeywordError
        chuan = chuan_hoa(goc)
        if not chuan:
            # Text chỉ gồm ký tự bị chuẩn hoá bỏ hết (ví dụ toàn khoảng trắng lạ).
            raise EmptyKeywordError
        return goc, chuan

    @classmethod
    def create(cls, department_id: UUID, text: str, now: datetime) -> "Keyword":
        """Tạo một từ khoá mới cho một phòng."""
        goc, chuan = cls._chuan_hoa_text(text)
        return cls(
            department_id=department_id,
            text=goc,
            normalized=chuan,
            created_at=now,
            updated_at=now,
        )

    def rename(self, text: str, now: datetime) -> None:
        """Đổi nội dung từ khoá; chuẩn hoá lại để khớp vẫn đúng."""
        self.text, self.normalized = self._chuan_hoa_text(text)
        self.updated_at = now
