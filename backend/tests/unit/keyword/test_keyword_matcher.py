from datetime import UTC, datetime

from src.modules.keyword.application.services.keyword_matcher import match_department
from src.modules.keyword.domain.entities.keyword import Keyword
from src.modules.keyword.domain.value_objects.extracted_term import ExtractedTerm
from src.shared.domain.identifiers import new_id

BAY_GIO = datetime(2026, 8, 1, 9, 0, tzinfo=UTC)
PHONG_BH = new_id()
PHONG_KD = new_id()


def _kw(department_id, text) -> Keyword:
    return Keyword.create(department_id=department_id, text=text, now=BAY_GIO)


def _term(text, normalized) -> ExtractedTerm:
    return ExtractedTerm(text=text, normalized=normalized)


DANH_MUC = [
    _kw(PHONG_BH, "bảo hành"),
    _kw(PHONG_BH, "đổi trả"),
    _kw(PHONG_KD, "báo giá"),
    _kw(PHONG_KD, "mua hàng"),
]


class TestMatchDepartment:
    def test_khop_dung_mot_phong(self) -> None:
        terms = (_term("Bảo hành sản phẩm", "bao hanh san pham"),)

        kq = match_department(terms, DANH_MUC)

        assert kq.department_id == PHONG_BH
        assert "bao hanh san pham" in kq.matched_terms

    def test_khop_keyword_la_con_cua_cum(self) -> None:
        # cụm "doi tra bao hanh" khớp cả 2 keyword phòng BH -> BH thắng rõ.
        terms = (_term("Đổi trả bảo hành", "doi tra bao hanh"),)

        kq = match_department(terms, DANH_MUC)
        assert kq.department_id == PHONG_BH

    def test_nhieu_cum_dồn_ve_mot_phong(self) -> None:
        terms = (
            _term("báo giá", "bao gia"),
            _term("mua hàng", "mua hang"),
        )

        kq = match_department(terms, DANH_MUC)
        assert kq.department_id == PHONG_KD
        assert len(kq.matched_terms) == 2

    def test_hoa_hai_phong_la_mo_ho(self) -> None:
        # 1 cụm khớp BH, 1 cụm khớp KD -> hoà -> None.
        terms = (
            _term("bảo hành", "bao hanh"),
            _term("báo giá", "bao gia"),
        )

        kq = match_department(terms, DANH_MUC)
        assert kq.department_id is None

    def test_khong_khop_phong_nao(self) -> None:
        terms = (_term("hỏi đường", "hoi duong"),)

        kq = match_department(terms, DANH_MUC)
        assert kq.department_id is None

    def test_terms_rong(self) -> None:
        kq = match_department((), DANH_MUC)
        assert kq.department_id is None

    def test_danh_muc_rong(self) -> None:
        terms = (_term("bảo hành", "bao hanh"),)
        kq = match_department(terms, [])
        assert kq.department_id is None

    def test_thang_ro_khi_hon_han(self) -> None:
        # 2 cụm khớp BH, 1 cụm khớp KD -> BH thắng.
        terms = (
            _term("bảo hành", "bao hanh"),
            _term("đổi trả", "doi tra"),
            _term("báo giá", "bao gia"),
        )

        kq = match_department(terms, DANH_MUC)
        assert kq.department_id == PHONG_BH
