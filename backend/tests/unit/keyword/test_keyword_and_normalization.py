from datetime import UTC, datetime

import pytest

from src.modules.keyword.domain.entities.keyword import EmptyKeywordError, Keyword
from src.modules.keyword.domain.value_objects.extracted_term import (
    AnalysisOutcome,
    ExtractedTerm,
)
from src.modules.keyword.domain.value_objects.normalization import chuan_hoa
from src.shared.domain.identifiers import new_id

BAY_GIO = datetime(2026, 8, 1, 9, 0, tzinfo=UTC)
PHONG = new_id()


class TestChuanHoa:
    def test_bo_dau_va_thuong_hoa(self) -> None:
        assert chuan_hoa("Bảo Hành") == "bao hanh"
        assert chuan_hoa("bao hanh") == "bao hanh"

    def test_xu_ly_chu_d(self) -> None:
        assert chuan_hoa("Đổi trả") == "doi tra"
        assert chuan_hoa("đơn hàng") == "don hang"

    def test_gop_khoang_trang(self) -> None:
        assert chuan_hoa("  báo   giá  ") == "bao gia"

    def test_hai_dang_viet_cho_cung_ket_qua(self) -> None:
        assert chuan_hoa("KHUYẾN MÃI") == chuan_hoa("khuyến mãi") == "khuyen mai"


class TestKeyword:
    def test_tao_keyword_giu_goc_va_normalized(self) -> None:
        kw = Keyword.create(department_id=PHONG, text="Bảo Hành", now=BAY_GIO)

        assert kw.text == "Bảo Hành"
        assert kw.normalized == "bao hanh"
        assert kw.department_id == PHONG

    def test_cat_khoang_trang(self) -> None:
        kw = Keyword.create(department_id=PHONG, text="  Đổi trả  ", now=BAY_GIO)

        assert kw.text == "Đổi trả"
        assert kw.normalized == "doi tra"

    def test_rong_bi_tu_choi(self) -> None:
        with pytest.raises(EmptyKeywordError):
            Keyword.create(department_id=PHONG, text="   ", now=BAY_GIO)

    def test_rename_chuan_hoa_lai(self) -> None:
        kw = Keyword.create(department_id=PHONG, text="Bảo Hành", now=BAY_GIO)
        kw.rename("Báo giá", BAY_GIO)

        assert kw.text == "Báo giá"
        assert kw.normalized == "bao gia"

    def test_rename_rong_bi_tu_choi(self) -> None:
        kw = Keyword.create(department_id=PHONG, text="Bảo Hành", now=BAY_GIO)

        with pytest.raises(EmptyKeywordError):
            kw.rename("  ", BAY_GIO)


class TestExtractedTerm:
    def test_giu_goc_va_normalized(self) -> None:
        term = ExtractedTerm(text="Bảo hành sản phẩm", normalized="bao hanh san pham")

        assert term.text == "Bảo hành sản phẩm"
        assert term.normalized == "bao hanh san pham"


class TestAnalysisOutcome:
    def test_co_ba_ket_cuc(self) -> None:
        assert AnalysisOutcome.AUTO_ASSIGNED == "AUTO_ASSIGNED"
        assert AnalysisOutcome.AMBIGUOUS == "AMBIGUOUS"
        assert AnalysisOutcome.NOT_ANALYZED == "NOT_ANALYZED"
