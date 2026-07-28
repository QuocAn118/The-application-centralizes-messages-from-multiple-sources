"""Round-trip test cho các repository hrm trên PostgreSQL thật.

Xác nhận mapper không mất field và các truy vấn (chồng ca, scope, get_for KPI,
scope đơn) chạy đúng trên SQL thật — chỗ mà fake in-memory không kiểm được.
"""

from datetime import UTC, date, datetime, time
from decimal import Decimal

import pytest
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from src.modules.hrm.domain.entities.kpi_target import KpiTarget
from src.modules.hrm.domain.entities.leave_request import LeaveRequest
from src.modules.hrm.domain.entities.shift import Shift
from src.modules.hrm.domain.entities.shift_assignment import ShiftAssignment
from src.modules.hrm.domain.value_objects.kpi import (
    KpiMetricType,
    KpiPeriod,
    KpiSubjectType,
)
from src.modules.hrm.domain.value_objects.request_kind import RequestStatus, RequestType
from src.modules.hrm.infrastructure.repositories.kpi_target_repository import (
    SqlAlchemyKpiTargetRepository,
)
from src.modules.hrm.infrastructure.repositories.request_repository import (
    SqlAlchemyRequestRepository,
)
from src.modules.hrm.infrastructure.repositories.shift_assignment_repository import (
    SqlAlchemyShiftAssignmentRepository,
)
from src.modules.hrm.infrastructure.repositories.shift_repository import (
    SqlAlchemyShiftRepository,
)
from src.shared.domain.identifiers import new_id

pytestmark = pytest.mark.integration

BAY_GIO = datetime(2026, 8, 1, 9, 0, tzinfo=UTC)
KY = KpiPeriod(year=2026, month=8)


class TestShiftRepository:
    async def test_round_trip(self, db_session: AsyncSession) -> None:
        repo = SqlAlchemyShiftRepository(db_session)
        phong = new_id()
        ca = Shift.create(
            department_id=phong,
            name="Ca sáng",
            start_time=time(8, 0),
            end_time=time(12, 0),
            now=BAY_GIO,
        )
        await repo.add(ca)
        await db_session.flush()

        doc = await repo.get_by_id(ca.id)
        assert doc is not None
        assert doc.name == "Ca sáng"
        assert doc.department_id == phong
        assert doc.start_time == time(8, 0)
        assert doc.end_time == time(12, 0)

    async def test_update_va_list_theo_phong(self, db_session: AsyncSession) -> None:
        repo = SqlAlchemyShiftRepository(db_session)
        phong_a, phong_b = new_id(), new_id()
        ca_a = Shift.create(
            department_id=phong_a,
            name="A",
            start_time=time(8, 0),
            end_time=time(12, 0),
            now=BAY_GIO,
        )
        ca_b = Shift.create(
            department_id=phong_b,
            name="B",
            start_time=time(8, 0),
            end_time=time(12, 0),
            now=BAY_GIO,
        )
        await repo.add(ca_a)
        await repo.add(ca_b)
        await db_session.flush()

        ds = await repo.list_for_departments([phong_a])
        assert {c.department_id for c in ds} == {phong_a}

    async def test_check_khung_gio_o_db(self, db_session: AsyncSession) -> None:
        # Ràng buộc end_time > start_time phải nằm ở DB, không chỉ domain.
        from sqlalchemy import text

        with pytest.raises(IntegrityError):
            await db_session.execute(
                text(
                    "INSERT INTO shifts (id, department_id, name, start_time, end_time, "
                    "is_active, created_at, updated_at) VALUES "
                    "(gen_random_uuid(), gen_random_uuid(), 'X', '12:00', '08:00', true, :bg, :bg)"
                ),
                {"bg": BAY_GIO},
            )


class TestShiftAssignmentRepository:
    async def test_round_trip_va_chong_ca_query(self, db_session: AsyncSession) -> None:
        shift_repo = SqlAlchemyShiftRepository(db_session)
        repo = SqlAlchemyShiftAssignmentRepository(db_session)
        phong = new_id()
        nv = new_id()
        ca = Shift.create(
            department_id=phong, name="Ca", start_time=time(8, 0), end_time=time(12, 0), now=BAY_GIO
        )
        await shift_repo.add(ca)
        await db_session.flush()

        pc = ShiftAssignment.assign(
            shift_id=ca.id,
            user_id=nv,
            department_id=phong,
            work_date=date(2026, 8, 5),
            start_time=time(8, 0),
            end_time=time(12, 0),
            now=BAY_GIO,
        )
        await repo.add(pc)
        await db_session.flush()

        trong_ngay = await repo.list_active_for_user_on_date(nv, date(2026, 8, 5))
        assert len(trong_ngay) == 1
        assert trong_ngay[0].user_id == nv

        # Ngày khác không trả về.
        assert await repo.list_active_for_user_on_date(nv, date(2026, 8, 6)) == []

    async def test_huy_roi_khong_con_active(self, db_session: AsyncSession) -> None:
        shift_repo = SqlAlchemyShiftRepository(db_session)
        repo = SqlAlchemyShiftAssignmentRepository(db_session)
        phong, nv = new_id(), new_id()
        ca = Shift.create(
            department_id=phong, name="Ca", start_time=time(8, 0), end_time=time(12, 0), now=BAY_GIO
        )
        await shift_repo.add(ca)
        await db_session.flush()
        pc = ShiftAssignment.assign(
            shift_id=ca.id,
            user_id=nv,
            department_id=phong,
            work_date=date(2026, 8, 5),
            start_time=time(8, 0),
            end_time=time(12, 0),
            now=BAY_GIO,
        )
        await repo.add(pc)
        await db_session.flush()

        pc.cancel(BAY_GIO)
        await repo.update(pc)
        await db_session.flush()

        assert await repo.list_active_for_user_on_date(nv, date(2026, 8, 5)) == []


class TestKpiTargetRepository:
    async def test_round_trip_va_get_for(self, db_session: AsyncSession) -> None:
        repo = SqlAlchemyKpiTargetRepository(db_session)
        nv, phong = new_id(), new_id()
        t = KpiTarget.set_target(
            subject_type=KpiSubjectType.USER,
            subject_id=nv,
            department_id=phong,
            metric_type=KpiMetricType.CONVERSATIONS_CLOSED,
            period=KY,
            target_value=Decimal("200"),
            now=BAY_GIO,
        )
        await repo.add(t)
        await db_session.flush()

        doc = await repo.get_for(KpiSubjectType.USER, nv, KpiMetricType.CONVERSATIONS_CLOSED, KY)
        assert doc is not None
        assert doc.target_value == Decimal("200")
        assert doc.department_id == phong
        assert doc.period == KY

    async def test_unique_subject_metric_period(self, db_session: AsyncSession) -> None:
        # Ràng buộc duy nhất chặn hai mục tiêu cùng (đối tượng, chỉ số, kỳ).
        repo = SqlAlchemyKpiTargetRepository(db_session)
        nv, phong = new_id(), new_id()
        for _ in range(2):
            t = KpiTarget.set_target(
                subject_type=KpiSubjectType.USER,
                subject_id=nv,
                department_id=phong,
                metric_type=KpiMetricType.CONVERSATIONS_CLOSED,
                period=KY,
                target_value=Decimal("200"),
                now=BAY_GIO,
            )
            await repo.add(t)
        with pytest.raises(IntegrityError):
            await db_session.flush()

    async def test_list_in_scope_theo_phong(self, db_session: AsyncSession) -> None:
        repo = SqlAlchemyKpiTargetRepository(db_session)
        phong_a, phong_b = new_id(), new_id()
        nv_a, nv_b = new_id(), new_id()
        await repo.add(
            KpiTarget.set_target(
                subject_type=KpiSubjectType.USER,
                subject_id=nv_a,
                department_id=phong_a,
                metric_type=KpiMetricType.CONVERSATIONS_CLOSED,
                period=KY,
                target_value=Decimal("1"),
                now=BAY_GIO,
            )
        )
        await repo.add(
            KpiTarget.set_target(
                subject_type=KpiSubjectType.USER,
                subject_id=nv_b,
                department_id=phong_b,
                metric_type=KpiMetricType.CONVERSATIONS_CLOSED,
                period=KY,
                target_value=Decimal("1"),
                now=BAY_GIO,
            )
        )
        await db_session.flush()

        ds = await repo.list_in_scope([phong_a])
        assert {t.subject_id for t in ds} == {nv_a}


class TestRequestRepository:
    async def test_round_trip_don_nghi_phep(self, db_session: AsyncSession) -> None:
        repo = SqlAlchemyRequestRepository(db_session)
        nv, phong = new_id(), new_id()
        don = LeaveRequest.submit(
            requester_id=nv,
            department_id=phong,
            request_type=RequestType.NGHI_PHEP,
            reason="Việc nhà",
            leave_start=date(2026, 8, 10),
            leave_end=date(2026, 8, 12),
            now=BAY_GIO,
        )
        await repo.add(don)
        await db_session.flush()

        doc = await repo.get_by_id(don.id)
        assert doc is not None
        assert doc.leave_start == date(2026, 8, 10)
        assert doc.status is RequestStatus.CHO_DUYET

    async def test_update_giu_quyet_dinh(self, db_session: AsyncSession) -> None:
        repo = SqlAlchemyRequestRepository(db_session)
        nv, phong, nguoi_duyet = new_id(), new_id(), new_id()
        don = LeaveRequest.submit(
            requester_id=nv,
            department_id=phong,
            request_type=RequestType.TANG_LUONG,
            reason="x",
            now=BAY_GIO,
        )
        await repo.add(don)
        await db_session.flush()

        don.reject(nguoi_duyet, "Không duyệt", BAY_GIO)
        await repo.update(don)
        await db_session.flush()

        doc = await repo.get_by_id(don.id)
        assert doc is not None
        assert doc.status is RequestStatus.TU_CHOI
        assert doc.decision_reason == "Không duyệt"
        assert doc.decided_by == nguoi_duyet

    async def test_scope_hop_don_minh_va_phong(self, db_session: AsyncSession) -> None:
        repo = SqlAlchemyRequestRepository(db_session)
        phong_a, phong_b = new_id(), new_id()
        manager = new_id()
        staff_a = new_id()
        staff_b = new_id()
        # Đơn Staff phòng A, đơn Manager (phòng A) tự gửi, đơn Staff phòng B.
        await repo.add(
            LeaveRequest.submit(
                requester_id=staff_a,
                department_id=phong_a,
                request_type=RequestType.KHAC,
                reason="a",
                now=BAY_GIO,
            )
        )
        await repo.add(
            LeaveRequest.submit(
                requester_id=manager,
                department_id=phong_a,
                request_type=RequestType.KHAC,
                reason="m",
                now=BAY_GIO,
            )
        )
        await repo.add(
            LeaveRequest.submit(
                requester_id=staff_b,
                department_id=phong_b,
                request_type=RequestType.KHAC,
                reason="b",
                now=BAY_GIO,
            )
        )
        await db_session.flush()

        # Manager phòng A: thấy đơn phòng A (gồm của mình), không thấy phòng B.
        ds = await repo.list_for_scope(requester_id=manager, department_ids=[phong_a])
        assert {r.requester_id for r in ds} == {staff_a, manager}
        assert await repo.count_for_scope(requester_id=manager, department_ids=[phong_a]) == 2
