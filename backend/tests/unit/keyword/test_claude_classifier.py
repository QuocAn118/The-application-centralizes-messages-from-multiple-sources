"""Test adapter Claude với client GIẢ — không ra mạng.

Kiểm: parse JSON đúng; bọc ```json/văn bản thừa vẫn cắt được object; department_id
không hợp lệ → None; confidence ngoài [0,1] bị kẹp; lỗi client/rỗng/parse →
ClassifierError. Không test Claude thật (để thủ công, ngoài CI).
"""

from dataclasses import dataclass
from decimal import Decimal
from typing import Any

import pytest

from src.modules.keyword.domain.ports import ClassifierError, IConversationClassifier
from src.modules.keyword.domain.value_objects.extracted_term import DepartmentKeywords
from src.modules.keyword.infrastructure.classifier.claude_classifier import (
    ClaudeConversationClassifier,
)
from src.shared.domain.identifiers import new_id

_PHONG = new_id()
_DEPARTMENTS = (DepartmentKeywords(department_id=_PHONG, keywords=("bao hanh", "sua chua")),)
_TEXTS = ("May giat cua toi bi hong, con bao hanh khong?",)


@dataclass
class _Block:
    text: str


@dataclass
class _Response:
    content: list[_Block]


class _FakeMessages:
    """Bắt chước ``client.messages`` — trả sẵn nội dung, hoặc ném lỗi."""

    def __init__(self, text: str | None, error: Exception | None) -> None:
        self._text = text
        self._error = error
        self.last_kwargs: dict[str, Any] | None = None

    async def create(self, **kwargs: Any) -> _Response:
        self.last_kwargs = kwargs
        if self._error is not None:
            raise self._error
        assert self._text is not None
        return _Response(content=[_Block(text=self._text)])


class _FakeClient:
    def __init__(self, text: str | None = None, error: Exception | None = None) -> None:
        self.messages = _FakeMessages(text, error)


def _classifier(
    text: str | None = None, error: Exception | None = None
) -> tuple[ClaudeConversationClassifier, _FakeClient]:
    client = _FakeClient(text=text, error=error)
    return ClaudeConversationClassifier(client=client, model="claude-test"), client


class TestClaudeClassifier:
    def test_fake_khop_hop_dong_port(self) -> None:
        classifier, _ = _classifier(text="{}")
        _typed: IConversationClassifier = classifier
        assert _typed is not None

    async def test_parse_json_day_du(self) -> None:
        raw = (
            f'{{"department_id": "{_PHONG}", "confidence": 0.87, '
            f'"terms": ["bao hanh may giat", "sua chua"]}}'
        )
        classifier, _ = _classifier(text=raw)

        ket_qua = await classifier.classify(_TEXTS, _DEPARTMENTS)

        assert ket_qua.department_id == _PHONG
        assert ket_qua.confidence == Decimal("0.87")
        assert tuple(t.text for t in ket_qua.terms) == ("bao hanh may giat", "sua chua")
        # normalized do adapter tự chuẩn hoá.
        assert ket_qua.terms[0].normalized == "bao hanh may giat"

    async def test_bao_json_bang_van_ban_thua_van_cat_duoc(self) -> None:
        raw = f'Đây là kết quả:\n```json\n{{"department_id": "{_PHONG}", "confidence": 0.6}}\n```'
        classifier, _ = _classifier(text=raw)

        ket_qua = await classifier.classify(_TEXTS, _DEPARTMENTS)

        assert ket_qua.department_id == _PHONG
        assert ket_qua.confidence == Decimal("0.6")
        assert ket_qua.terms == ()

    async def test_department_null_thi_khong_chon_phong(self) -> None:
        classifier, _ = _classifier(text='{"department_id": null, "confidence": 0.2}')

        ket_qua = await classifier.classify(_TEXTS, _DEPARTMENTS)

        assert ket_qua.department_id is None
        assert ket_qua.confidence == Decimal("0.2")

    async def test_department_id_khong_phai_uuid_thi_thanh_none(self) -> None:
        classifier, _ = _classifier(text='{"department_id": "phong-ky-thuat", "confidence": 0.9}')

        ket_qua = await classifier.classify(_TEXTS, _DEPARTMENTS)

        assert ket_qua.department_id is None

    async def test_confidence_ngoai_khoang_bi_kep(self) -> None:
        classifier_cao, _ = _classifier(text=f'{{"department_id": "{_PHONG}", "confidence": 5}}')
        classifier_am, _ = _classifier(text=f'{{"department_id": "{_PHONG}", "confidence": -3}}')

        cao = await classifier_cao.classify(_TEXTS, _DEPARTMENTS)
        am = await classifier_am.classify(_TEXTS, _DEPARTMENTS)

        assert cao.confidence == Decimal("1")
        assert am.confidence == Decimal("0")

    async def test_prompt_gom_tin_va_danh_muc_phong(self) -> None:
        classifier, client = _classifier(text="{}")

        await classifier.classify(_TEXTS, _DEPARTMENTS)

        kwargs = client.messages.last_kwargs
        assert kwargs is not None
        assert kwargs["model"] == "claude-test"
        noi_dung = kwargs["messages"][0]["content"]
        assert str(_PHONG) in noi_dung
        assert "bao hanh" in noi_dung
        assert _TEXTS[0] in noi_dung

    async def test_loi_client_thanh_classifier_error(self) -> None:
        classifier, _ = _classifier(error=RuntimeError("mạng lỗi"))

        with pytest.raises(ClassifierError):
            await classifier.classify(_TEXTS, _DEPARTMENTS)

    async def test_noi_dung_rong_thanh_classifier_error(self) -> None:
        classifier, _ = _classifier(text="   ")

        with pytest.raises(ClassifierError):
            await classifier.classify(_TEXTS, _DEPARTMENTS)

    async def test_khong_phai_json_thanh_classifier_error(self) -> None:
        classifier, _ = _classifier(text="xin chào, tôi không biết")

        with pytest.raises(ClassifierError):
            await classifier.classify(_TEXTS, _DEPARTMENTS)
