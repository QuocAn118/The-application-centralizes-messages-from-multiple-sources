"""Adapter LLM: cho Claude đọc vài tin đầu của khách và tự chọn phòng phù hợp.

Implementation của port ``IConversationClassifier`` bằng Claude API (SDK
``anthropic``). Phần dựng prompt và parse/gác JSON nằm ở ``prompt_parsing`` —
dùng chung với adapter Gemini; ở đây chỉ còn phần **riêng của Claude**: gọi
``messages.create`` và ghép các khối text trong phản hồi.

Mọi lỗi (mạng/quota/parse) gói thành ``ClassifierError`` để use case nuốt gọn,
không làm hỏng nhận tin.

Khoá API là bí mật (``ANTHROPIC_API_KEY`` trong ``.env``) — không log prompt kèm
khoá, không đưa khoá vào thông điệp lỗi.
"""

import logging
from typing import Any, Protocol

from src.modules.keyword.domain.ports import ClassifierError
from src.modules.keyword.domain.value_objects.extracted_term import (
    ClassificationResult,
    DepartmentKeywords,
)
from src.modules.keyword.infrastructure.classifier.prompt_parsing import (
    MAX_TOKENS,
    SYSTEM_PROMPT,
    dung_prompt,
    parse_ket_qua,
)

logger = logging.getLogger(__name__)

_TEN = "Claude"


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
        prompt = dung_prompt(texts, departments)
        try:
            response = await self._client.messages.create(
                model=self._model,
                max_tokens=MAX_TOKENS,
                system=SYSTEM_PROMPT,
                messages=[{"role": "user", "content": prompt}],
            )
            raw = self._lay_text(response)
        except ClassifierError:
            raise
        except Exception as exc:  # mọi lỗi SDK/mạng đều gói lại thành ClassifierError
            raise ClassifierError("Gọi Claude thất bại.") from exc

        return parse_ket_qua(raw, _TEN)

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
