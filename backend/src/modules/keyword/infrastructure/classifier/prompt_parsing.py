"""Phần dựng prompt và parse/gác JSON — dùng chung cho mọi nhà cung cấp LLM.

Tách ra khỏi adapter Claude khi thêm Gemini: chỉ **lời gọi API** và **cách lấy
text ra khỏi response** là riêng của từng nhà cung cấp; toàn bộ phần dưới đây
(system prompt, dựng prompt, cắt fence ```json, kẹp confidence về [0,1], UUID
sai thành ``None``) không dính gì tới nhà cung cấp nào.

Giữ một bản duy nhất để hai adapter không trôi khác nhau: sửa prompt ở đây là
cả Claude lẫn Gemini cùng đổi, không có chuyện một bên quên cập nhật.
"""

import json
from decimal import Decimal, InvalidOperation
from uuid import UUID

from src.modules.keyword.domain.ports import ClassifierError
from src.modules.keyword.domain.value_objects.extracted_term import (
    ClassificationResult,
    DepartmentKeywords,
    ExtractedTerm,
)
from src.modules.keyword.domain.value_objects.normalization import chuan_hoa

MAX_TOKENS = 1024

SYSTEM_PROMPT = (
    "Bạn là bộ định tuyến hội thoại của một tổng đài chăm sóc khách hàng. "
    "Dựa vào vài tin nhắn ĐẦU của khách và danh mục từ khoá đặc trưng của từng "
    "phòng ban, hãy xác định khách cần gì và chọn ĐÚNG MỘT phòng phù hợp nhất. "
    "Nếu không đủ cơ sở để chọn (khách chào hỏi chung, nội dung mơ hồ, không khớp "
    "phòng nào), hãy để department_id = null.\n\n"
    "CHỈ trả về JSON đúng cấu trúc sau, không kèm giải thích:\n"
    '{"department_id": "<uuid phòng chọn hoặc null>", '
    '"confidence": <số thực 0..1>, '
    '"terms": ["<cụm nhu cầu ngắn>", ...]}'
)


def dung_prompt(texts: tuple[str, ...], departments: tuple[DepartmentKeywords, ...]) -> str:
    """Ghép danh mục từ khoá các phòng + vài tin đầu của khách thành prompt."""
    danh_muc = "\n".join(f"- Phòng {d.department_id}: {', '.join(d.keywords)}" for d in departments)
    tin = "\n".join(f"{i}. {t}" for i, t in enumerate(texts, start=1))
    return (
        f"Danh mục từ khoá theo phòng:\n{danh_muc or '(chưa có phòng nào)'}\n\n"
        f"Tin nhắn đầu của khách:\n{tin}"
    )


def cat_json(raw: str) -> str:
    """Cắt lấy phần ``{...}`` — phòng khi LLM bọc thêm văn bản hoặc ```json."""
    dau = raw.find("{")
    cuoi = raw.rfind("}")
    if dau == -1 or cuoi == -1 or cuoi < dau:
        raise ValueError("Không thấy object JSON trong phản hồi.")
    return raw[dau : cuoi + 1]


def doc_department_id(value: object) -> UUID | None:
    if value is None or value == "":
        return None
    try:
        return UUID(str(value))
    except (ValueError, AttributeError):
        # LLM trả id không phải UUID — coi như không chọn được phòng.
        return None


def doc_confidence(value: object) -> Decimal:
    if value is None:
        return Decimal("0")
    try:
        conf = Decimal(str(value))
    except (InvalidOperation, ValueError):
        return Decimal("0")
    # Kẹp về [0, 1] phòng khi LLM trả ngoài khoảng.
    if conf < 0:
        return Decimal("0")
    if conf > 1:
        return Decimal("1")
    return conf


def doc_terms(value: object) -> tuple[ExtractedTerm, ...]:
    if not isinstance(value, list):
        return ()
    terms: list[ExtractedTerm] = []
    for item in value:
        text = str(item).strip()
        if not text:
            continue
        terms.append(ExtractedTerm(text=text, normalized=chuan_hoa(text)))
    return tuple(terms)


def parse_ket_qua(raw: str, ten_nha_cung_cap: str) -> ClassificationResult:
    """Parse JSON thô của LLM thành ``ClassificationResult``.

    ``ten_nha_cung_cap`` chỉ để thông điệp lỗi nói đúng bên nào hỏng — không ảnh
    hưởng logic.
    """
    try:
        data = json.loads(cat_json(raw))
    except (json.JSONDecodeError, ValueError) as exc:
        raise ClassifierError(f"Không parse được JSON từ {ten_nha_cung_cap}.") from exc
    if not isinstance(data, dict):
        raise ClassifierError(f"JSON từ {ten_nha_cung_cap} không phải object.")

    return ClassificationResult(
        department_id=doc_department_id(data.get("department_id")),
        confidence=doc_confidence(data.get("confidence")),
        terms=doc_terms(data.get("terms")),
    )
