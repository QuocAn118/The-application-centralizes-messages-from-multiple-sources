"""Khớp cụm nhu cầu (LLM trích) với danh mục từ khoá các phòng để chọn phòng.

Thuần, tất định, không I/O — dễ test và tách khỏi LLM. Đầu vào là các cụm nhu
cầu đã chuẩn hoá và danh mục keyword đã chuẩn hoá; đầu ra là phòng thắng (nếu
có) cùng các cụm đã khớp.
"""

from collections import defaultdict
from dataclasses import dataclass
from uuid import UUID

from src.modules.keyword.domain.entities.keyword import Keyword
from src.modules.keyword.domain.value_objects.extracted_term import ExtractedTerm


@dataclass(frozen=True)
class MatchResult:
    """Kết quả khớp: phòng thắng (nếu rõ ràng) + các cụm nhu cầu đã khớp phòng đó.

    ``department_id`` là ``None`` khi mơ hồ: không phòng nào khớp, hoặc hai phòng
    khớp ngang nhau (không phân bừa).
    """

    department_id: UUID | None
    matched_terms: tuple[str, ...]


def _khop(term_normalized: str, keyword_normalized: str) -> bool:
    """Một cụm nhu cầu khớp một từ khoá khi cụm này chứa từ khoá kia (hai chiều).

    Ví dụ cụm "bao hanh san pham" khớp keyword "bao hanh"; cụm "doi" cũng khớp
    keyword "doi tra" ở chiều ngược. So trên dạng đã chuẩn hoá nên không phụ
    thuộc dấu/hoa thường.
    """
    return keyword_normalized in term_normalized or term_normalized in keyword_normalized


def match_department(terms: tuple[ExtractedTerm, ...], keywords: list[Keyword]) -> MatchResult:
    """Chọn phòng phù hợp nhất cho các cụm nhu cầu.

    Đếm số cụm nhu cầu *khác nhau* khớp keyword của mỗi phòng. Phòng thắng phải
    có số khớp cao nhất **và cao hơn hẳn** mọi phòng khác — hoà nhau là mơ hồ,
    giữ CHO_PHAN (không phân bừa).
    """
    if not terms or not keywords:
        return MatchResult(department_id=None, matched_terms=())

    # Mỗi phòng: tập các cụm nhu cầu (theo normalized) đã khớp keyword của phòng.
    khop_theo_phong: dict[UUID, set[str]] = defaultdict(set)
    for kw in keywords:
        for term in terms:
            if _khop(term.normalized, kw.normalized):
                khop_theo_phong[kw.department_id].add(term.normalized)

    if not khop_theo_phong:
        return MatchResult(department_id=None, matched_terms=())

    # Sắp theo số cụm khớp giảm dần.
    xep_hang = sorted(khop_theo_phong.items(), key=lambda kv: len(kv[1]), reverse=True)
    phong_nhat, cum_nhat = xep_hang[0]

    # Hoà với phòng nhì -> mơ hồ.
    if len(xep_hang) > 1 and len(xep_hang[1][1]) == len(cum_nhat):
        return MatchResult(department_id=None, matched_terms=())

    return MatchResult(department_id=phong_nhat, matched_terms=tuple(sorted(cum_nhat)))
