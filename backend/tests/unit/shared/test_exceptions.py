import pytest

from src.shared.application.exceptions import (
    ApplicationError,
    AuthenticationError,
    ConflictError,
    NotFoundError,
    PermissionDeniedError,
)
from src.shared.domain.exceptions import BusinessRuleViolationError, DomainError


def test_domain_error_giu_lai_ma_loi_va_thong_diep() -> None:
    loi = DomainError("Khong hop le", code="INVALID")

    assert loi.code == "INVALID"
    assert loi.message == "Khong hop le"
    assert str(loi) == "Khong hop le"


def test_business_rule_violation_la_domain_error() -> None:
    assert issubclass(BusinessRuleViolationError, DomainError)


@pytest.mark.parametrize(
    "lop_loi",
    [NotFoundError, ConflictError, PermissionDeniedError, AuthenticationError],
)
def test_cac_loi_ung_dung_deu_ke_thua_application_error(
    lop_loi: type[ApplicationError],
) -> None:
    assert issubclass(lop_loi, ApplicationError)


@pytest.mark.parametrize(
    "lop_loi",
    [NotFoundError, ConflictError, PermissionDeniedError, AuthenticationError],
)
def test_loi_ung_dung_giu_lai_ma_loi_va_thong_diep(
    lop_loi: type[ApplicationError],
) -> None:
    """Tầng presentation đọc ``.code`` để ánh xạ sang mã HTTP — nếu thuộc tính
    này không được gán, toàn bộ xử lý lỗi của API sẽ hỏng."""
    loi = lop_loi("Thong diep thu", code="MA_THU")

    assert loi.message == "Thong diep thu"
    assert loi.code == "MA_THU"
    assert str(loi) == "Thong diep thu"
