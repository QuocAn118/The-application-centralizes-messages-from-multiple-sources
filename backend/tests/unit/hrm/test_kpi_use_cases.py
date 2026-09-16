from datetime import UTC, datetime
from decimal import Decimal

import pytest

from src.modules.hrm.application.actor import ActorRole, HrmActor
from src.modules.hrm.application.use_cases.kpi_use_cases import (
    GetKpiProgress,
    ListKpiProgress,
    ListKpiTargets,
    SetKpiTarget,
)
from src.modules.hrm.domain.ports import AgentInfo
from src.modules.hrm.domain.value_objects.kpi import (
    KpiMetricType,
    KpiPeriod,
    KpiSubjectType,
)
from src.shared.application.exceptions import NotFoundError, PermissionDeniedError
from src.shared.domain.identifiers import new_id
from tests.unit.hrm.fakes import (
    FakeClock,
    FakeKpiTargetRepository,
    FakePerformanceSource,
    FakeWorkforceDirectory,
)

BAY_GIO = datetime(2026, 8, 1, 9, 0, tzinfo=UTC)
PHONG_A = new_id()
PHONG_B = new_id()
KY = KpiPeriod(year=2026, month=8)
DONG = KpiMetricType.CONVERSATIONS_CLOSED
PHAN_HOI = KpiMetricType.AVG_RESPONSE_MINUTES


def _manager(department_id=PHONG_A) -> HrmActor:
    return HrmActor(user_id=new_id(), role=ActorRole.MANAGER, department_id=department_id)


def _admin() -> HrmActor:
    return HrmActor(user_id=new_id(), role=ActorRole.ADMIN, department_id=None)


def _staff(user_id, department_id=PHONG_A) -> HrmActor:
    return HrmActor(user_id=user_id, role=ActorRole.STAFF, department_id=department_id)


class _Boi:
    def __init__(self) -> None:
        self.clock = FakeClock(BAY_GIO)
        self.repo = FakeKpiTargetRepository()
        self.directory = FakeWorkforceDirectory()
        self.directory.active_departments = {PHONG_A, PHONG_B}
        self.perf = FakePerformanceSource()
        self.set = SetKpiTarget(self.repo, self.directory, self.clock)
        self.list = ListKpiTargets(self.repo)
        self.progress = GetKpiProgress(self.repo, self.perf, self.directory)
        self.progress_lo = ListKpiProgress(self.repo, self.perf)

    def them_nhan_vien(self, department_id=PHONG_A):
        nv = new_id()
        self.directory.add_agent(
            AgentInfo(user_id=nv, department_id=department_id, role="STAFF", is_active=True)
        )
        return nv


class TestSetKpiTarget:
    async def test_dat_muc_tieu_cho_nhan_vien(self) -> None:
        bc = _Boi()
        nv = bc.them_nhan_vien(PHONG_A)

        view = await bc.set.execute(_manager(), KpiSubjectType.USER, nv, DONG, KY, Decimal("200"))

        assert view.target_value == Decimal("200")
        assert view.subject_id == nv

    async def test_dat_lai_thi_cap_nhat_khong_tao_moi(self) -> None:
        bc = _Boi()
        nv = bc.them_nhan_vien(PHONG_A)
        await bc.set.execute(_manager(), KpiSubjectType.USER, nv, DONG, KY, Decimal("200"))

        await bc.set.execute(_manager(), KpiSubjectType.USER, nv, DONG, KY, Decimal("250"))

        targets = await bc.repo.list_in_scope(None)
        assert len(targets) == 1
        assert targets[0].target_value == Decimal("250")

    async def test_dat_muc_tieu_cho_phong(self) -> None:
        bc = _Boi()

        view = await bc.set.execute(
            _manager(), KpiSubjectType.DEPARTMENT, PHONG_A, DONG, KY, Decimal("1000")
        )

        assert view.subject_type is KpiSubjectType.DEPARTMENT

    async def test_staff_bi_tu_choi(self) -> None:
        bc = _Boi()
        nv = bc.them_nhan_vien(PHONG_A)

        with pytest.raises(PermissionDeniedError):
            await bc.set.execute(_staff(nv), KpiSubjectType.USER, nv, DONG, KY, Decimal("200"))

    async def test_manager_dat_cho_nhan_vien_phong_khac_bi_tu_choi(self) -> None:
        bc = _Boi()
        nv_b = bc.them_nhan_vien(PHONG_B)

        with pytest.raises(PermissionDeniedError):
            await bc.set.execute(
                _manager(PHONG_A), KpiSubjectType.USER, nv_b, DONG, KY, Decimal("200")
            )


class TestGetKpiProgress:
    async def test_ghep_muc_tieu_va_thuc_dat(self) -> None:
        bc = _Boi()
        nv = bc.them_nhan_vien(PHONG_A)
        await bc.set.execute(_manager(), KpiSubjectType.USER, nv, DONG, KY, Decimal("200"))
        bc.perf.set_user_metric(nv, DONG, KY, Decimal("150"))

        view = await bc.progress.execute(_manager(), KpiSubjectType.USER, nv, DONG, KY)

        assert view.target_value == Decimal("200")
        assert view.actual_value == Decimal("150")
        # càng-cao-càng-tốt: 150/200 = 75%
        assert view.achievement_percent == Decimal("75.0")

    async def test_chua_co_thuc_dat_thi_phan_tram_none(self) -> None:
        bc = _Boi()
        nv = bc.them_nhan_vien(PHONG_A)
        await bc.set.execute(_manager(), KpiSubjectType.USER, nv, DONG, KY, Decimal("200"))
        # không set_user_metric -> nguồn trả None

        view = await bc.progress.execute(_manager(), KpiSubjectType.USER, nv, DONG, KY)

        assert view.actual_value is None
        assert view.achievement_percent is None

    async def test_metric_thoi_gian_phan_hoi_tinh_nguoc(self) -> None:
        # F4: AVG_RESPONSE_MINUTES càng thấp càng tốt. Mục tiêu 10 phút, thực đạt
        # 5 phút (nhanh gấp đôi) -> 200%, KHÔNG phải 50%.
        bc = _Boi()
        nv = bc.them_nhan_vien(PHONG_A)
        await bc.set.execute(_manager(), KpiSubjectType.USER, nv, PHAN_HOI, KY, Decimal("10"))
        bc.perf.set_user_metric(nv, PHAN_HOI, KY, Decimal("5"))

        view = await bc.progress.execute(_manager(), KpiSubjectType.USER, nv, PHAN_HOI, KY)

        assert view.achievement_percent == Decimal("200.0")

    async def test_metric_thoi_gian_phan_hoi_cham_hon_duoi_100(self) -> None:
        # Mục tiêu 10 phút, thực đạt 20 phút (chậm gấp đôi) -> 50%.
        bc = _Boi()
        nv = bc.them_nhan_vien(PHONG_A)
        await bc.set.execute(_manager(), KpiSubjectType.USER, nv, PHAN_HOI, KY, Decimal("10"))
        bc.perf.set_user_metric(nv, PHAN_HOI, KY, Decimal("20"))

        view = await bc.progress.execute(_manager(), KpiSubjectType.USER, nv, PHAN_HOI, KY)

        assert view.achievement_percent == Decimal("50.0")

    async def test_staff_xem_kpi_cua_minh(self) -> None:
        bc = _Boi()
        nv = bc.them_nhan_vien(PHONG_A)
        await bc.set.execute(_manager(), KpiSubjectType.USER, nv, DONG, KY, Decimal("200"))
        bc.perf.set_user_metric(nv, DONG, KY, Decimal("100"))

        view = await bc.progress.execute(_staff(nv), KpiSubjectType.USER, nv, DONG, KY)

        assert view.actual_value == Decimal("100")

    async def test_staff_xem_kpi_nguoi_khac_bi_tu_choi(self) -> None:
        bc = _Boi()
        nv = bc.them_nhan_vien(PHONG_A)
        nguoi_khac = bc.them_nhan_vien(PHONG_A)
        await bc.set.execute(_manager(), KpiSubjectType.USER, nguoi_khac, DONG, KY, Decimal("200"))

        with pytest.raises(PermissionDeniedError):
            await bc.progress.execute(_staff(nv), KpiSubjectType.USER, nguoi_khac, DONG, KY)

    async def test_chua_dat_muc_tieu_bi_not_found(self) -> None:
        bc = _Boi()
        nv = bc.them_nhan_vien(PHONG_A)

        with pytest.raises(NotFoundError):
            await bc.progress.execute(_manager(), KpiSubjectType.USER, nv, DONG, KY)


class TestListKpiTargets:
    async def test_admin_thay_tat_ca(self) -> None:
        bc = _Boi()
        nv_a = bc.them_nhan_vien(PHONG_A)
        nv_b = bc.them_nhan_vien(PHONG_B)
        await bc.set.execute(_admin(), KpiSubjectType.USER, nv_a, DONG, KY, Decimal("100"))
        await bc.set.execute(_admin(), KpiSubjectType.USER, nv_b, DONG, KY, Decimal("100"))

        views = await bc.list.execute(_admin())

        assert len(views) == 2

    async def test_staff_chi_thay_muc_tieu_cua_minh(self) -> None:
        bc = _Boi()
        nv = bc.them_nhan_vien(PHONG_A)
        nguoi_khac = bc.them_nhan_vien(PHONG_A)
        await bc.set.execute(_manager(), KpiSubjectType.USER, nv, DONG, KY, Decimal("100"))
        await bc.set.execute(_manager(), KpiSubjectType.USER, nguoi_khac, DONG, KY, Decimal("100"))

        views = await bc.list.execute(_staff(nv))

        assert {v.subject_id for v in views} == {nv}

    async def test_manager_thay_muc_tieu_cap_nhan_vien_va_cap_phong(self) -> None:
        # F2: Manager phải thấy CẢ mục tiêu cấp nhân viên trong phòng mình lẫn
        # mục tiêu cấp phòng — không chỉ mục tiêu có subject_id == department_id.
        bc = _Boi()
        nv = bc.them_nhan_vien(PHONG_A)
        nv_phong_khac = bc.them_nhan_vien(PHONG_B)
        await bc.set.execute(_manager(), KpiSubjectType.USER, nv, DONG, KY, Decimal("200"))
        await bc.set.execute(
            _manager(), KpiSubjectType.DEPARTMENT, PHONG_A, DONG, KY, Decimal("1000")
        )
        # Mục tiêu của nhân viên phòng khác không được lọt vào.
        await bc.set.execute(_admin(), KpiSubjectType.USER, nv_phong_khac, DONG, KY, Decimal("50"))

        views = await bc.list.execute(_manager(PHONG_A))

        assert {v.subject_id for v in views} == {nv, PHONG_A}


class TestListKpiProgress:
    """Nợ N4 — tiến độ gom lô thay cho N+1.

    Màn KPI trước đây gọi ``GET /kpi-progress`` cho TỪNG dòng. Đo thật trên DB
    dev (chỉ 172 tin nhắn): bảng 68 dòng của Admin tốn ~2,1 giây và 68 lời gọi,
    mỗi lời gọi quét lại toàn bộ dữ liệu inbox rồi vứt đi phần của người khác.
    """

    async def test_so_loi_goi_khong_tang_theo_so_dong(self) -> None:
        # Đây là test khoá chính của N4: 10 nhân viên, CÙNG một chỉ số, phải
        # gom về ĐÚNG MỘT lời gọi tới nguồn hiệu suất. Quay lại vòng lặp là đỏ.
        bc = _Boi()
        for _ in range(10):
            nv = bc.them_nhan_vien(PHONG_A)
            await bc.set.execute(_manager(), KpiSubjectType.USER, nv, DONG, KY, Decimal("50"))

        views = await bc.progress_lo.execute(_admin(), KY)

        assert len(views) == 10
        assert bc.perf.batch_calls == 1, (
            f"10 dòng lẽ ra 1 lời gọi lô, thực tế {bc.perf.batch_calls} — N+1 quay lại?"
        )

    async def test_hai_chi_so_thi_hai_loi_goi_khong_phai_hai_muoi(self) -> None:
        bc = _Boi()
        for _ in range(10):
            nv = bc.them_nhan_vien(PHONG_A)
            await bc.set.execute(_manager(), KpiSubjectType.USER, nv, DONG, KY, Decimal("50"))
            await bc.set.execute(_manager(), KpiSubjectType.USER, nv, PHAN_HOI, KY, Decimal("15"))

        views = await bc.progress_lo.execute(_admin(), KY)

        assert len(views) == 20
        # Gom theo chỉ số: hai chỉ số -> hai lời gọi, không phải 20.
        assert bc.perf.batch_calls == 2

    async def test_giu_nguyen_phan_biet_none_voi_0(self) -> None:
        # Ngữ nghĩa quan trọng nhất của màn KPI: "chưa đo được" khác "bằng 0".
        # Bản gom lô mà làm mất phân biệt này thì UI hiện sai mà không ai biết.
        bc = _Boi()
        nv = bc.them_nhan_vien(PHONG_A)
        await bc.set.execute(_manager(), KpiSubjectType.USER, nv, DONG, KY, Decimal("50"))
        await bc.set.execute(_manager(), KpiSubjectType.USER, nv, PHAN_HOI, KY, Decimal("15"))
        # KHÔNG bơm số liệu nào -> nguồn thật trả 0 cho chỉ số đếm, None cho TB.

        views = {v.metric_type: v for v in await bc.progress_lo.execute(_admin(), KY)}

        assert views[DONG].actual_value == Decimal(0), "chỉ số đếm: đã đo, bằng không"
        assert views[PHAN_HOI].actual_value is None, "chỉ số trung bình: chưa có mẫu"

    async def test_ket_qua_trung_khop_ban_mot_dong(self) -> None:
        # Bản lô và bản một-dòng phải cho cùng con số; lệch nhau là lỗi im lặng.
        bc = _Boi()
        nv = bc.them_nhan_vien(PHONG_A)
        await bc.set.execute(_manager(), KpiSubjectType.USER, nv, DONG, KY, Decimal("50"))
        bc.perf.set_user_metric(nv, DONG, KY, Decimal("30"))

        mot = await bc.progress.execute(_admin(), KpiSubjectType.USER, nv, DONG, KY)
        lo = (await bc.progress_lo.execute(_admin(), KY))[0]

        assert lo.actual_value == mot.actual_value
        assert lo.achievement_percent == mot.achievement_percent

    async def test_staff_chi_thay_tien_do_cua_minh(self) -> None:
        # Phạm vi phải khớp ListKpiTargets — endpoint lô không nhận subject_id
        # nên không có đường dò dữ liệu người khác.
        bc = _Boi()
        nv = bc.them_nhan_vien(PHONG_A)
        nguoi_khac = bc.them_nhan_vien(PHONG_A)
        await bc.set.execute(_manager(), KpiSubjectType.USER, nv, DONG, KY, Decimal("50"))
        await bc.set.execute(_manager(), KpiSubjectType.USER, nguoi_khac, DONG, KY, Decimal("50"))

        views = await bc.progress_lo.execute(_staff(nv), KY)

        assert {v.subject_id for v in views} == {nv}

    async def test_manager_khong_thay_phong_khac(self) -> None:
        bc = _Boi()
        nv_a = bc.them_nhan_vien(PHONG_A)
        nv_b = bc.them_nhan_vien(PHONG_B)
        await bc.set.execute(_manager(), KpiSubjectType.USER, nv_a, DONG, KY, Decimal("50"))
        await bc.set.execute(_admin(), KpiSubjectType.USER, nv_b, DONG, KY, Decimal("50"))

        views = await bc.progress_lo.execute(_manager(PHONG_A), KY)

        assert {v.subject_id for v in views} == {nv_a}

    async def test_ky_trong_tra_mang_rong(self) -> None:
        bc = _Boi()
        views = await bc.progress_lo.execute(_admin(), KY)
        assert views == []
        assert bc.perf.batch_calls == 0

    async def test_muc_tieu_cap_phong_cung_duoc_gom_lo(self) -> None:
        # Ban đầu tôi để cấp phòng gọi lẻ vì đoán "phòng thì ít dòng". Đo thật:
        # 18 mục tiêu cấp phòng tốn 222 ms — chậm hơn cả 68 dòng cấp nhân viên
        # đã gom lô (172 ms). Test này khoá lại để không quay về vòng lặp.
        bc = _Boi()
        for phong in (PHONG_A, PHONG_B):
            await bc.set.execute(
                _admin(), KpiSubjectType.DEPARTMENT, phong, DONG, KY, Decimal("500")
            )
            await bc.set.execute(
                _admin(), KpiSubjectType.DEPARTMENT, phong, PHAN_HOI, KY, Decimal("10")
            )

        views = await bc.progress_lo.execute(_admin(), KY)

        assert len(views) == 4
        # Hai chỉ số cho cấp phòng -> đúng hai lời gọi, không phải bốn.
        assert bc.perf.batch_calls == 2

    async def test_tron_ca_hai_cap_toi_da_bon_loi_goi(self) -> None:
        bc = _Boi()
        for _ in range(5):
            nv = bc.them_nhan_vien(PHONG_A)
            await bc.set.execute(_manager(), KpiSubjectType.USER, nv, DONG, KY, Decimal("50"))
            await bc.set.execute(_manager(), KpiSubjectType.USER, nv, PHAN_HOI, KY, Decimal("15"))
        await bc.set.execute(_admin(), KpiSubjectType.DEPARTMENT, PHONG_A, DONG, KY, Decimal("500"))
        await bc.set.execute(
            _admin(), KpiSubjectType.DEPARTMENT, PHONG_A, PHAN_HOI, KY, Decimal("10")
        )

        views = await bc.progress_lo.execute(_admin(), KY)

        assert len(views) == 12
        # 2 chỉ số cho nhân viên + 2 chỉ số cho phòng = 4, dù có 12 dòng.
        assert bc.perf.batch_calls == 4

    async def test_cap_phong_giu_phan_biet_none_voi_0(self) -> None:
        bc = _Boi()
        await bc.set.execute(_admin(), KpiSubjectType.DEPARTMENT, PHONG_A, DONG, KY, Decimal("500"))
        await bc.set.execute(
            _admin(), KpiSubjectType.DEPARTMENT, PHONG_A, PHAN_HOI, KY, Decimal("10")
        )

        views = {v.metric_type: v for v in await bc.progress_lo.execute(_admin(), KY)}

        assert views[DONG].actual_value == Decimal(0)
        assert views[PHAN_HOI].actual_value is None

    async def test_cap_phong_khop_ban_mot_dong(self) -> None:
        bc = _Boi()
        await bc.set.execute(_admin(), KpiSubjectType.DEPARTMENT, PHONG_A, DONG, KY, Decimal("500"))
        bc.perf.set_department_metric(PHONG_A, DONG, KY, Decimal("400"))

        mot = await bc.progress.execute(_admin(), KpiSubjectType.DEPARTMENT, PHONG_A, DONG, KY)
        lo = (await bc.progress_lo.execute(_admin(), KY))[0]

        assert lo.actual_value == mot.actual_value
        assert lo.achievement_percent == mot.achievement_percent
