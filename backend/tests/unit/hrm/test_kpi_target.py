from datetime import UTC, datetime
from decimal import Decimal

import pytest

from src.modules.hrm.domain.entities.kpi_target import (
    KpiTarget,
    NegativeKpiTargetError,
)
from src.modules.hrm.domain.value_objects.kpi import (
    KpiMetricType,
    KpiPeriod,
    KpiSubjectType,
)
from src.shared.domain.identifiers import new_id

BAY_GIO = datetime(2026, 8, 1, 9, 0, tzinfo=UTC)
KY = KpiPeriod(year=2026, month=8)


def _target(value: Decimal, *, subject_type=KpiSubjectType.USER) -> KpiTarget:
    return KpiTarget.set_target(
        subject_type=subject_type,
        subject_id=new_id(),
        metric_type=KpiMetricType.CONVERSATIONS_CLOSED,
        period=KY,
        target_value=value,
        now=BAY_GIO,
    )


class TestKpiTarget:
    def test_dat_muc_tieu_cho_nhan_vien(self) -> None:
        nv = new_id()
        t = KpiTarget.set_target(
            subject_type=KpiSubjectType.USER,
            subject_id=nv,
            metric_type=KpiMetricType.CONVERSATIONS_CLOSED,
            period=KY,
            target_value=Decimal("200"),
            now=BAY_GIO,
        )

        assert t.subject_id == nv
        assert t.subject_type is KpiSubjectType.USER
        assert t.target_value == Decimal("200")
        assert t.period == KY

    def test_dat_muc_tieu_cho_phong(self) -> None:
        t = _target(Decimal("1000"), subject_type=KpiSubjectType.DEPARTMENT)

        assert t.subject_type is KpiSubjectType.DEPARTMENT

    def test_muc_tieu_khong_bi_am(self) -> None:
        with pytest.raises(NegativeKpiTargetError):
            _target(Decimal("-1"))

    def test_muc_tieu_bang_khong_hop_le(self) -> None:
        t = _target(Decimal("0"))

        assert t.target_value == Decimal("0")

    def test_doi_muc_tieu(self) -> None:
        t = _target(Decimal("200"))
        t.change_target(Decimal("250"), BAY_GIO)

        assert t.target_value == Decimal("250")

    def test_doi_muc_tieu_am_bi_tu_choi(self) -> None:
        t = _target(Decimal("200"))

        with pytest.raises(NegativeKpiTargetError):
            t.change_target(Decimal("-5"), BAY_GIO)
