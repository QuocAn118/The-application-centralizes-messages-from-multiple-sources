"""Test phân quyền báo cáo: phạm vi phòng theo vai."""

from uuid import UUID

import pytest

from src.modules.analytics.application.actor import ActorRole, AnalyticsActor
from src.modules.analytics.application.authorization import (
    bao_dam_xem_bao_cao,
    pham_vi_phong_bao_cao,
)
from src.shared.application.exceptions import PermissionDeniedError

D1 = UUID("00000000-0000-0000-0000-0000000000d1")
D2 = UUID("00000000-0000-0000-0000-0000000000d2")

ADMIN = AnalyticsActor(user_id=UUID(int=1), role=ActorRole.ADMIN)
MANAGER_D1 = AnalyticsActor(user_id=UUID(int=2), role=ActorRole.MANAGER, department_id=D1)
MANAGER_KHONG_PHONG = AnalyticsActor(user_id=UUID(int=4), role=ActorRole.MANAGER)
STAFF = AnalyticsActor(user_id=UUID(int=3), role=ActorRole.STAFF, department_id=D1)


class TestBaoDamXemBaoCao:
    def test_admin_va_manager_qua(self) -> None:
        bao_dam_xem_bao_cao(ADMIN)
        bao_dam_xem_bao_cao(MANAGER_D1)  # không ném

    def test_staff_bi_chan(self) -> None:
        with pytest.raises(PermissionDeniedError) as e:
            bao_dam_xem_bao_cao(STAFF)
        assert e.value.code == "ANALYTICS_MANAGER_REQUIRED"


class TestPhamViPhong:
    def test_admin_khong_gioi_han_khi_khong_truyen(self) -> None:
        assert pham_vi_phong_bao_cao(ADMIN, None) is None

    def test_admin_gioi_han_dung_phong_khi_truyen(self) -> None:
        assert pham_vi_phong_bao_cao(ADMIN, D2) == (D2,)

    def test_manager_luon_ep_phong_minh(self) -> None:
        # Truyền D2 nhưng Manager D1 vẫn bị ép về D1.
        assert pham_vi_phong_bao_cao(MANAGER_D1, D2) == (D1,)
        assert pham_vi_phong_bao_cao(MANAGER_D1, None) == (D1,)

    def test_manager_khong_phong_bi_chan(self) -> None:
        with pytest.raises(PermissionDeniedError) as e:
            pham_vi_phong_bao_cao(MANAGER_KHONG_PHONG, None)
        assert e.value.code == "ANALYTICS_MANAGER_NO_DEPARTMENT"
