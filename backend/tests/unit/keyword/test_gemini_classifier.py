import json
from decimal import Decimal
from uuid import uuid4

import httpx
import pytest

from src.modules.keyword.domain.ports import ClassifierError
from src.modules.keyword.domain.value_objects.extracted_term import DepartmentKeywords
from src.modules.keyword.infrastructure.classifier.gemini_classifier import (
    GeminiConversationClassifier,
)

API_KEY = "khoa_gemini_gia_lap"
MODEL = "gemini-2.0-flash"
TIN = ("toi muon doi tra hang", "don hang 123")


def _phong() -> tuple[DepartmentKeywords, ...]:
    return (DepartmentKeywords(department_id=uuid4(), keywords=("doi tra", "hoan tien")),)


def _classifier(handler):  # type: ignore[no-untyped-def]
    transport = httpx.MockTransport(handler)
    return GeminiConversationClassifier(
        API_KEY, MODEL, client_factory=lambda: httpx.AsyncClient(transport=transport)
    )


def _phan_hoi(text: str) -> httpx.Response:
    """Dung phan hoi Gemini that: candidates[].content.parts[].text."""
    return httpx.Response(200, json={"candidates": [{"content": {"parts": [{"text": text}]}}]})


class TestGoiApi:
    async def test_goi_dung_url_va_gui_khoa_qua_header(self) -> None:
        ghi_lai: dict[str, object] = {}

        def handler(request: httpx.Request) -> httpx.Response:
            ghi_lai["url"] = str(request.url)
            ghi_lai["api_key_header"] = request.headers.get("x-goog-api-key")
            ghi_lai["body"] = json.loads(request.content)
            return _phan_hoi('{"department_id": null, "confidence": 0.1, "terms": []}')

        await _classifier(handler).classify(TIN, _phong())

        assert ghi_lai["url"] == (
            f"https://generativelanguage.googleapis.com/v1beta/models/{MODEL}:generateContent"
        )
        assert ghi_lai["api_key_header"] == API_KEY
        # Khoa KHONG duoc nam trong query string (de bi ghi vao log proxy).
        assert API_KEY not in str(ghi_lai["url"])

    async def test_prompt_mang_tin_khach_va_danh_muc_phong(self) -> None:
        ghi_lai: dict[str, object] = {}
        phong = _phong()

        def handler(request: httpx.Request) -> httpx.Response:
            ghi_lai["body"] = json.loads(request.content)
            return _phan_hoi('{"department_id": null, "confidence": 0, "terms": []}')

        await _classifier(handler).classify(TIN, phong)

        body = ghi_lai["body"]
        assert isinstance(body, dict)
        prompt = body["contents"][0]["parts"][0]["text"]
        assert "toi muon doi tra hang" in prompt
        assert str(phong[0].department_id) in prompt
        assert "doi tra" in prompt
        # Chi dan he thong di rieng o systemInstruction (khac Claude).
        assert "JSON" in body["systemInstruction"]["parts"][0]["text"]


class TestPhanHoiHopLe:
    async def test_doc_dung_phong_confidence_va_terms(self) -> None:
        phong = _phong()
        dept_id = phong[0].department_id

        def handler(request: httpx.Request) -> httpx.Response:
            return _phan_hoi(
                json.dumps(
                    {
                        "department_id": str(dept_id),
                        "confidence": 0.87,
                        "terms": ["doi tra hang", "don hang"],
                    }
                )
            )

        kq = await _classifier(handler).classify(TIN, phong)

        assert kq.department_id == dept_id
        assert kq.confidence == Decimal("0.87")
        assert [t.text for t in kq.terms] == ["doi tra hang", "don hang"]

    async def test_department_id_null_la_khong_chon_duoc_phong(self) -> None:
        def handler(request: httpx.Request) -> httpx.Response:
            return _phan_hoi('{"department_id": null, "confidence": 0.2, "terms": ["chao hoi"]}')

        kq = await _classifier(handler).classify(TIN, _phong())
        assert kq.department_id is None

    async def test_van_doc_duoc_khi_llm_boc_them_fence_json(self) -> None:
        def handler(request: httpx.Request) -> httpx.Response:
            return _phan_hoi(
                '```json\n{"department_id": null, "confidence": 0.5, "terms": []}\n```'
            )

        kq = await _classifier(handler).classify(TIN, _phong())
        assert kq.confidence == Decimal("0.5")


class TestDuLieuXau:
    async def test_json_hong_bao_classifier_error(self) -> None:
        def handler(request: httpx.Request) -> httpx.Response:
            return _phan_hoi("khong phai json gi ca")

        with pytest.raises(ClassifierError):
            await _classifier(handler).classify(TIN, _phong())

    async def test_confidence_ngoai_khoang_bi_kep_ve_0_1(self) -> None:
        def handler(request: httpx.Request) -> httpx.Response:
            return _phan_hoi('{"department_id": null, "confidence": 5, "terms": []}')

        kq = await _classifier(handler).classify(TIN, _phong())
        assert kq.confidence == Decimal("1")

    async def test_confidence_am_bi_kep_ve_0(self) -> None:
        def handler(request: httpx.Request) -> httpx.Response:
            return _phan_hoi('{"department_id": null, "confidence": -2, "terms": []}')

        kq = await _classifier(handler).classify(TIN, _phong())
        assert kq.confidence == Decimal("0")

    async def test_confidence_khong_phai_so_thanh_0(self) -> None:
        def handler(request: httpx.Request) -> httpx.Response:
            return _phan_hoi('{"department_id": null, "confidence": "cao", "terms": []}')

        kq = await _classifier(handler).classify(TIN, _phong())
        assert kq.confidence == Decimal("0")

    async def test_uuid_sai_thanh_none_chu_khong_nem_loi(self) -> None:
        # LLM "bia" id khong phai UUID -> coi nhu khong chon duoc phong, giu CHO_PHAN.
        def handler(request: httpx.Request) -> httpx.Response:
            return _phan_hoi('{"department_id": "phong-cskh", "confidence": 0.9, "terms": []}')

        kq = await _classifier(handler).classify(TIN, _phong())
        assert kq.department_id is None

    async def test_terms_khong_phai_list_thi_rong(self) -> None:
        def handler(request: httpx.Request) -> httpx.Response:
            return _phan_hoi('{"department_id": null, "confidence": 0.3, "terms": "abc"}')

        kq = await _classifier(handler).classify(TIN, _phong())
        assert kq.terms == ()


class TestLoiHaTang:
    async def test_http_loi_bao_classifier_error(self) -> None:
        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(429, json={"error": {"message": "quota"}})

        with pytest.raises(ClassifierError):
            await _classifier(handler).classify(TIN, _phong())

    async def test_mang_loi_bao_classifier_error(self) -> None:
        def handler(request: httpx.Request) -> httpx.Response:
            raise httpx.ConnectError("mat mang")

        with pytest.raises(ClassifierError):
            await _classifier(handler).classify(TIN, _phong())

    async def test_khong_co_candidate_bao_classifier_error(self) -> None:
        # Gemini chan noi dung vi bo loc an toan -> khong co candidates.
        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(200, json={"promptFeedback": {"blockReason": "SAFETY"}})

        with pytest.raises(ClassifierError):
            await _classifier(handler).classify(TIN, _phong())

    async def test_noi_dung_rong_bao_classifier_error(self) -> None:
        def handler(request: httpx.Request) -> httpx.Response:
            return _phan_hoi("   ")

        with pytest.raises(ClassifierError):
            await _classifier(handler).classify(TIN, _phong())

    async def test_khoa_api_khong_lot_vao_thong_diep_loi(self) -> None:
        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(401, json={"error": "unauthorized"})

        with pytest.raises(ClassifierError) as loi:
            await _classifier(handler).classify(TIN, _phong())
        assert API_KEY not in str(loi.value)
