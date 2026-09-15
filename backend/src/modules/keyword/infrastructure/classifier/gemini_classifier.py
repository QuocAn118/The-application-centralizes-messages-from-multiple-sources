"""Adapter LLM: cho Gemini (Google AI Studio) đọc tin khách và tự chọn phòng.

Implementation thứ hai của port ``IConversationClassifier``, song song adapter
Claude. Phần dựng prompt và parse/gác JSON dùng chung ở ``prompt_parsing`` — ở
đây chỉ có phần **riêng của Gemini**: gọi REST ``generateContent`` và bóc text
ra khỏi cấu trúc ``candidates[].content.parts[].text``.

**Vì sao gọi REST thẳng bằng ``httpx`` thay vì cài SDK ``google-generativeai``:**
adapter chỉ cần đúng MỘT endpoint không streaming. ``httpx`` đã là dependency sẵn
có (Zalo/Meta/Telegram adapter đều dùng), nên thêm SDK là thêm một cây phụ thuộc
cho một lời gọi HTTP. Dùng ``httpx`` cũng cho phép test bơm ``MockTransport``
đúng cách các adapter kênh đang làm, không cần cơ chế giả riêng.

Khoá API là bí mật (``GEMINI_API_KEY`` trong ``.env``): truyền qua header
``x-goog-api-key``, **không** đặt vào query string — query string hay bị ghi vào
log của proxy/server. Không log prompt kèm khoá, không đưa khoá vào thông điệp lỗi.
"""

import logging
from collections.abc import Callable
from typing import Any

import httpx

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

_API_GOC = "https://generativelanguage.googleapis.com/v1beta"
_TEN = "Gemini"


class GeminiConversationClassifier:
    """Gọi Gemini để phân loại hội thoại và trích cụm nhu cầu."""

    def __init__(
        self,
        api_key: str,
        model: str,
        client_factory: Callable[[], httpx.AsyncClient] | None = None,
    ) -> None:
        self._api_key = api_key
        self._model = model
        # Cho test tiêm transport giả; production dùng client mặc định.
        self._client_factory = client_factory or (lambda: httpx.AsyncClient(timeout=30.0))

    async def classify(
        self, texts: tuple[str, ...], departments: tuple[DepartmentKeywords, ...]
    ) -> ClassificationResult:
        body = {
            # Gemini tách chỉ dẫn hệ thống ra ``systemInstruction``, khác Claude
            # (tham số ``system``) — nội dung prompt thì giống hệt.
            "systemInstruction": {"parts": [{"text": SYSTEM_PROMPT}]},
            "contents": [{"role": "user", "parts": [{"text": dung_prompt(texts, departments)}]}],
            "generationConfig": {
                "maxOutputTokens": MAX_TOKENS,
                # Phân loại cần tính ổn định, không cần sáng tạo: nhiệt độ 0 để
                # cùng một hội thoại cho cùng một kết quả.
                "temperature": 0,
                # Ép trả JSON thuần, đỡ phải cắt fence ```json. Vẫn giữ bước cắt
                # ở ``parse_ket_qua`` vì đây là gợi ý, không phải bảo đảm.
                "responseMimeType": "application/json",
            },
        }

        try:
            async with self._client_factory() as client:
                resp = await client.post(
                    f"{_API_GOC}/models/{self._model}:generateContent",
                    headers={"x-goog-api-key": self._api_key},
                    json=body,
                )
                resp.raise_for_status()
                raw = self._lay_text(resp.json())
        except ClassifierError:
            raise
        except httpx.HTTPStatusError as exc:
            # Nêu rõ mã lỗi và model: 404 gần như luôn là "model đã bị Google gỡ"
            # — thông điệp chung chung khiến việc chẩn đoán mất hàng giờ.
            ma = exc.response.status_code
            goi_y = ""
            if ma == 404:
                goi_y = (
                    f" Model {self._model!r} có thể đã bị gỡ; đổi GEMINI_MODEL "
                    "(ví dụ 'gemini-flash-latest')."
                )
            elif ma in (401, 403):
                goi_y = " Kiểm tra GEMINI_API_KEY."
            elif ma == 429:
                goi_y = " Đã chạm giới hạn quota."
            elif ma == 503:
                goi_y = (
                    " Model đang quá tải (lỗi TẠM THỜI của Google, không phải lỗi cấu"
                    " hình) — hàng đợi sẽ thử lại. Hay gặp với bí danh '-latest'."
                )
            raise ClassifierError(f"Gọi Gemini lỗi HTTP {ma}.{goi_y}") from exc
        except Exception as exc:  # mạng/JSON hỏng đều gói lại
            raise ClassifierError("Gọi Gemini thất bại (mạng hoặc phản hồi hỏng).") from exc

        return parse_ket_qua(raw, _TEN)

    @staticmethod
    def _lay_text(payload: Any) -> str:
        """Ghép text trong ``candidates[0].content.parts[]``.

        Gemini có thể trả về không có ``candidates`` khi nội dung bị chặn bởi bộ
        lọc an toàn — khi đó coi như phân loại thất bại, use case sẽ giữ hội
        thoại ở ``CHO_PHAN`` cho Manager phân tay.
        """
        if not isinstance(payload, dict):
            raise ClassifierError("Phản hồi Gemini không phải JSON object.")

        candidates = payload.get("candidates")
        if not isinstance(candidates, list) or not candidates:
            raise ClassifierError("Gemini không trả candidate nào.")

        parts = candidates[0].get("content", {}).get("parts", [])
        if not isinstance(parts, list):
            raise ClassifierError("Phản hồi Gemini thiếu parts.")

        noi_dung = "".join(
            p["text"] for p in parts if isinstance(p, dict) and isinstance(p.get("text"), str)
        ).strip()
        if not noi_dung:
            raise ClassifierError("Gemini trả về nội dung rỗng.")
        return noi_dung
