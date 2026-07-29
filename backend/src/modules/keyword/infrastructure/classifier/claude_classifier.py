"""Adapter LLM: cho Claude đọc vài tin đầu của khách và tự chọn phòng phù hợp.

Implementation của port ``IConversationClassifier`` bằng Claude API (SDK
``anthropic``). Prompt gồm nội dung vài tin đầu của khách + danh mục từ khoá của
từng phòng để LLM tham chiếu; yêu cầu LLM trả JSON gồm phòng chọn (hoặc null),
độ tin cậy, và các cụm nhu cầu. Adapter chỉ parse — code use case mới *gác* kết
quả (phòng phải tồn tại + đủ tin cậy). Mọi lỗi (mạng/quota/parse) gói thành
``ClassifierError`` để use case nuốt gọn, không làm hỏng nhận tin.

Khoá API là bí mật (``ANTHROPIC_API_KEY`` trong ``.env``) — không log prompt kèm
khoá, không đưa khoá vào thông điệp lỗi.
"""

import json
import logging
from decimal import Decimal, InvalidOperation
from typing import Any, Protocol
from uuid import UUID

from src.modules.keyword.domain.ports import ClassifierError
from src.modules.keyword.domain.value_objects.extracted_term import (
    ClassificationResult,
    DepartmentKeywords,
    ExtractedTerm,
)
from src.modules.keyword.domain.value_objects.normalization import chuan_hoa

logger = logging.getLogger(__name__)

_MAX_TOKENS = 1024

_SYSTEM_PROMPT = (
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


class IAnthropicClient(Protocol):
    """Phần tối thiểu của ``anthropic.AsyncAnthropic`` mà adapter dùng.

    Định nghĩa hẹp để test bơm client giả (không ra mạng) mà vẫn khớp kiểu.
    """

    @property
    def messages(self) -> Any: ...


class ClaudeConversationClassifier:
    """Gọi Claude để phân loại hội thoại và trích cụm nhu cầu."""

    def __init__(self, client: IAnthropicClient, model: str) -> None:
        self._client = client
        self._model = model

    async def classify(
        self, texts: tuple[str, ...], departments: tuple[DepartmentKeywords, ...]
    ) -> ClassificationResult:
        prompt = self._dung_prompt(texts, departments)
        try:
            response = await self._client.messages.create(
                model=self._model,
                max_tokens=_MAX_TOKENS,
                system=_SYSTEM_PROMPT,
                messages=[{"role": "user", "content": prompt}],
            )
            raw = self._lay_text(response)
        except ClassifierError:
            raise
        except Exception as exc:  # mọi lỗi SDK/mạng đều gói lại thành ClassifierError
            raise ClassifierError("Gọi Claude thất bại.") from exc

        return self._parse(raw)

    @staticmethod
    def _dung_prompt(texts: tuple[str, ...], departments: tuple[DepartmentKeywords, ...]) -> str:
        danh_muc = "\n".join(
            f"- Phòng {d.department_id}: {', '.join(d.keywords)}" for d in departments
        )
        tin = "\n".join(f"{i}. {t}" for i, t in enumerate(texts, start=1))
        return (
            f"Danh mục từ khoá theo phòng:\n{danh_muc or '(chưa có phòng nào)'}\n\n"
            f"Tin nhắn đầu của khách:\n{tin}"
        )

    @staticmethod
    def _lay_text(response: Any) -> str:
        """Ghép các khối text trong phản hồi Claude thành một chuỗi."""
        parts: list[str] = []
        for block in getattr(response, "content", []):
            text = getattr(block, "text", None)
            if isinstance(text, str):
                parts.append(text)
        noi_dung = "".join(parts).strip()
        if not noi_dung:
            raise ClassifierError("Claude trả về nội dung rỗng.")
        return noi_dung

    def _parse(self, raw: str) -> ClassificationResult:
        try:
            data = json.loads(self._cat_json(raw))
        except (json.JSONDecodeError, ValueError) as exc:
            raise ClassifierError("Không parse được JSON từ Claude.") from exc
        if not isinstance(data, dict):
            raise ClassifierError("JSON từ Claude không phải object.")

        department_id = self._doc_department_id(data.get("department_id"))
        confidence = self._doc_confidence(data.get("confidence"))
        terms = self._doc_terms(data.get("terms"))
        return ClassificationResult(department_id=department_id, confidence=confidence, terms=terms)

    @staticmethod
    def _cat_json(raw: str) -> str:
        """Cắt lấy phần ``{...}`` — phòng khi Claude bọc thêm văn bản/```json."""
        dau = raw.find("{")
        cuoi = raw.rfind("}")
        if dau == -1 or cuoi == -1 or cuoi < dau:
            raise ValueError("Không thấy object JSON trong phản hồi.")
        return raw[dau : cuoi + 1]

    @staticmethod
    def _doc_department_id(value: object) -> UUID | None:
        if value is None or value == "":
            return None
        try:
            return UUID(str(value))
        except (ValueError, AttributeError):
            # LLM trả id không phải UUID — coi như không chọn được phòng.
            return None

    @staticmethod
    def _doc_confidence(value: object) -> Decimal:
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

    @staticmethod
    def _doc_terms(value: object) -> tuple[ExtractedTerm, ...]:
        if not isinstance(value, list):
            return ()
        terms: list[ExtractedTerm] = []
        for item in value:
            text = str(item).strip()
            if not text:
                continue
            terms.append(ExtractedTerm(text=text, normalized=chuan_hoa(text)))
        return tuple(terms)
