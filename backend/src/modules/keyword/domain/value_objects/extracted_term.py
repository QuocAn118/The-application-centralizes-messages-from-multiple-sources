"""Value object cho kết quả phân loại hội thoại bằng LLM.

Cách tiếp cận: LLM tự đọc hiểu vài tin đầu của khách và, dựa trên danh mục từ
khoá của từng phòng (bơm vào prompt), tự chọn phòng phù hợp — thay cho khớp
chuỗi thủ công. Code chỉ *gác* kết quả LLM (phòng phải tồn tại + đủ tin cậy).
"""

from dataclasses import dataclass, field
from decimal import Decimal
from enum import StrEnum
from uuid import UUID


class AnalysisOutcome(StrEnum):
    """Kết cục của một lần phân tích hội thoại.

    ``AUTO_ASSIGNED``: LLM chọn được một phòng hợp lệ, đủ tin cậy → đã tự phân.
    ``AMBIGUOUS``: LLM đọc được nhu cầu nhưng không chọn được phòng rõ ràng
    (LLM trả "không rõ", chọn phòng không tồn tại, hoặc tin cậy thấp) → giữ CHO_PHAN.
    ``NOT_ANALYZED``: không phân tích được (LLM lỗi, hoặc chưa đủ tin) → giữ nguyên.
    """

    AUTO_ASSIGNED = "AUTO_ASSIGNED"
    AMBIGUOUS = "AMBIGUOUS"
    NOT_ANALYZED = "NOT_ANALYZED"


@dataclass(frozen=True)
class ExtractedTerm:
    """Một cụm nhu cầu LLM nhận ra từ nội dung tin.

    Giữ để #5 báo cáo nhu cầu khách (kể cả khi không phân được phòng). ``text``
    là cụm LLM diễn đạt; ``normalized`` là dạng bỏ dấu/thường hoá để #5 gom nhóm.
    """

    text: str
    normalized: str


@dataclass(frozen=True)
class DepartmentKeywords:
    """Danh mục từ khoá của một phòng, ở dạng bơm vào prompt cho LLM tham chiếu.

    ``keywords`` là các từ khoá gốc (Manager nhập) của phòng ``department_id``.
    """

    department_id: UUID
    keywords: tuple[str, ...]


@dataclass(frozen=True)
class ClassificationResult:
    """Kết quả một lần gọi ``IConversationClassifier``.

    ``department_id`` là phòng LLM chọn, hoặc ``None`` nếu LLM không xác định
    được. ``confidence`` (0..1) là độ tin cậy LLM tự đánh giá. ``terms`` là các
    cụm nhu cầu LLM nhận ra (cho #5). Phòng LLM chọn vẫn được use case *gác* lại
    (phải tồn tại + đủ tin cậy) trước khi tự phân.
    """

    department_id: UUID | None = None
    confidence: Decimal = Decimal("0")
    terms: tuple[ExtractedTerm, ...] = field(default_factory=tuple)
