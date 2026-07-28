"""Value object cho kết quả phân tích nhu cầu khách bằng LLM."""

from dataclasses import dataclass, field
from decimal import Decimal
from enum import StrEnum
from uuid import UUID


class AnalysisOutcome(StrEnum):
    """Kết cục của một lần phân tích hội thoại.

    ``AUTO_ASSIGNED``: khớp đúng một phòng đủ tin cậy → đã tự phân.
    ``AMBIGUOUS``: LLM trích được nhu cầu nhưng không khớp một phòng rõ ràng
    (không khớp phòng nào, hoặc khớp nhiều phòng ngang nhau) → giữ CHO_PHAN.
    ``NOT_ANALYZED``: không phân tích được (LLM lỗi, hoặc chưa đủ tin) → giữ nguyên.
    """

    AUTO_ASSIGNED = "AUTO_ASSIGNED"
    AMBIGUOUS = "AMBIGUOUS"
    NOT_ANALYZED = "NOT_ANALYZED"


@dataclass(frozen=True)
class ExtractedTerm:
    """Một cụm nhu cầu LLM trích được từ nội dung tin, ở dạng chuẩn hoá để khớp.

    ``text`` là cụm gốc LLM trả (giữ để #5 báo cáo nhu cầu mới); ``normalized``
    là dạng đã bỏ dấu/thường hoá để so khớp với keyword của phòng.
    """

    text: str
    normalized: str


@dataclass(frozen=True)
class ExtractionResult:
    """Kết quả một lần gọi ``IKeywordExtractor``.

    ``terms`` là các cụm nhu cầu trích được; ``confidence`` là độ tin cậy tổng
    thể LLM tự đánh giá (0..1). Rỗng ``terms`` nghĩa là không trích được gì.
    """

    terms: tuple[ExtractedTerm, ...] = field(default_factory=tuple)
    confidence: Decimal = Decimal("0")


@dataclass(frozen=True)
class DepartmentMatch:
    """Một phòng ứng viên sau khi khớp cụm nhu cầu với danh mục keyword.

    ``matched_terms`` là các cụm nhu cầu đã khớp keyword của phòng này; số lượng
    khớp là cơ sở chọn phòng thắng.
    """

    department_id: UUID
    matched_terms: tuple[str, ...]
