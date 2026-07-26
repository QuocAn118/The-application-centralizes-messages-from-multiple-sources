"""Fake in-memory cho unit test use case của hrm.

Fake phản ánh hành vi thật của repository/port; khi hợp đồng đổi, fake sai làm
test đỏ — đúng thứ ta muốn. Mock thì không.
"""

from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

from src.modules.hrm.domain.entities.kpi_target import KpiTarget
from src.modules.hrm.domain.entities.leave_request import LeaveRequest
from src.modules.hrm.domain.entities.shift import Shift
from src.modules.hrm.domain.entities.shift_assignment import ShiftAssignment
from src.modules.hrm.domain.ports import AgentInfo
from src.modules.hrm.domain.value_objects.kpi import (
    KpiMetricType,
    KpiPeriod,
    KpiSubjectType,
)
from src.modules.hrm.domain.value_objects.request_kind import RequestStatus


class FakeClock:
    """Đồng hồ cố định để test kiểm soát thời gian."""

    def __init__(self, now: datetime) -> None:
        self._now = now

    def now(self) -> datetime:
        return self._now

    def set(self, now: datetime) -> None:
        self._now = now


class FakeShiftRepository:
    def __init__(self, shifts: list[Shift] | None = None) -> None:
        self._shifts: dict[UUID, Shift] = {s.id: s for s in (shifts or [])}

    async def get_by_id(self, shift_id: UUID) -> Shift | None:
        return self._shifts.get(shift_id)

    async def add(self, shift: Shift) -> None:
        self._shifts[shift.id] = shift

    async def update(self, shift: Shift) -> None:
        self._shifts[shift.id] = shift

    async def list_for_departments(
        self, department_ids: list[UUID] | None, is_active: bool | None = None
    ) -> list[Shift]:
        ket_qua = list(self._shifts.values())
        if department_ids is not None:
            ket_qua = [s for s in ket_qua if s.department_id in department_ids]
        if is_active is not None:
            ket_qua = [s for s in ket_qua if s.is_active is is_active]
        return sorted(ket_qua, key=lambda s: s.created_at)


class FakeShiftAssignmentRepository:
    def __init__(self, assignments: list[ShiftAssignment] | None = None) -> None:
        self._items: dict[UUID, ShiftAssignment] = {a.id: a for a in (assignments or [])}

    async def get_by_id(self, assignment_id: UUID) -> ShiftAssignment | None:
        return self._items.get(assignment_id)

    async def add(self, assignment: ShiftAssignment) -> None:
        self._items[assignment.id] = assignment

    async def update(self, assignment: ShiftAssignment) -> None:
        self._items[assignment.id] = assignment

    async def list_active_for_user_on_date(
        self, user_id: UUID, work_date: date
    ) -> list[ShiftAssignment]:
        return [
            a
            for a in self._items.values()
            if a.user_id == user_id and a.work_date == work_date and a.is_active
        ]

    async def list_for_scope(
        self,
        user_ids: list[UUID] | None,
        department_ids: list[UUID] | None,
        date_from: date | None = None,
        date_to: date | None = None,
    ) -> list[ShiftAssignment]:
        ket_qua = list(self._items.values())
        if user_ids is not None:
            ket_qua = [a for a in ket_qua if a.user_id in user_ids]
        if department_ids is not None:
            ket_qua = [a for a in ket_qua if a.department_id in department_ids]
        if date_from is not None:
            ket_qua = [a for a in ket_qua if a.work_date >= date_from]
        if date_to is not None:
            ket_qua = [a for a in ket_qua if a.work_date <= date_to]
        return sorted(ket_qua, key=lambda a: (a.work_date, a.start_time))


class FakeKpiTargetRepository:
    def __init__(self, targets: list[KpiTarget] | None = None) -> None:
        self._items: dict[UUID, KpiTarget] = {t.id: t for t in (targets or [])}

    async def get_by_id(self, target_id: UUID) -> KpiTarget | None:
        return self._items.get(target_id)

    async def get_for(
        self,
        subject_type: KpiSubjectType,
        subject_id: UUID,
        metric_type: KpiMetricType,
        period: KpiPeriod,
    ) -> KpiTarget | None:
        for t in self._items.values():
            if (
                t.subject_type is subject_type
                and t.subject_id == subject_id
                and t.metric_type is metric_type
                and t.period == period
            ):
                return t
        return None

    async def add(self, target: KpiTarget) -> None:
        self._items[target.id] = target

    async def update(self, target: KpiTarget) -> None:
        self._items[target.id] = target

    async def list_for_subjects(
        self,
        subject_ids: list[UUID] | None,
        period: KpiPeriod | None = None,
    ) -> list[KpiTarget]:
        ket_qua = list(self._items.values())
        if subject_ids is not None:
            ket_qua = [t for t in ket_qua if t.subject_id in subject_ids]
        if period is not None:
            ket_qua = [t for t in ket_qua if t.period == period]
        return sorted(ket_qua, key=lambda t: t.created_at)


class FakeRequestRepository:
    def __init__(self, requests: list[LeaveRequest] | None = None) -> None:
        self._items: dict[UUID, LeaveRequest] = {r.id: r for r in (requests or [])}

    async def get_by_id(self, request_id: UUID) -> LeaveRequest | None:
        return self._items.get(request_id)

    async def add(self, request: LeaveRequest) -> None:
        self._items[request.id] = request

    async def update(self, request: LeaveRequest) -> None:
        self._items[request.id] = request

    def _loc(
        self,
        requester_id: UUID | None,
        department_ids: list[UUID] | None,
        status: RequestStatus | None,
    ) -> list[LeaveRequest]:
        ket_qua = []
        for r in self._items.values():
            # Hợp của 'đơn mình gửi' và 'đơn trong phòng mình'.
            khop_nguoi = requester_id is not None and r.requester_id == requester_id
            khop_phong = department_ids is not None and r.department_id in department_ids
            khong_gioi_han = requester_id is None and department_ids is None
            if not (khop_nguoi or khop_phong or khong_gioi_han):
                continue
            if status is not None and r.status is not status:
                continue
            ket_qua.append(r)
        return sorted(ket_qua, key=lambda r: r.created_at, reverse=True)

    async def list_for_scope(
        self,
        requester_id: UUID | None,
        department_ids: list[UUID] | None,
        status: RequestStatus | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[LeaveRequest]:
        return self._loc(requester_id, department_ids, status)[offset : offset + limit]

    async def count_for_scope(
        self,
        requester_id: UUID | None,
        department_ids: list[UUID] | None,
        status: RequestStatus | None = None,
    ) -> int:
        return len(self._loc(requester_id, department_ids, status))


class FakeWorkforceDirectory:
    def __init__(self, agents: list[AgentInfo] | None = None) -> None:
        self._agents: dict[UUID, AgentInfo] = {a.user_id: a for a in (agents or [])}
        self.active_departments: set[UUID] = set()
        # Manager của mỗi phòng, để định tuyến người duyệt.
        self._managers: dict[UUID, AgentInfo] = {}

    def add_agent(self, agent: AgentInfo) -> None:
        self._agents[agent.user_id] = agent
        if agent.department_id is not None:
            self.active_departments.add(agent.department_id)
            if agent.role == "MANAGER":
                self._managers[agent.department_id] = agent

    async def get_agent(self, user_id: UUID) -> AgentInfo | None:
        return self._agents.get(user_id)

    async def department_exists_active(self, department_id: UUID) -> bool:
        return department_id in self.active_departments

    async def get_manager_of_department(self, department_id: UUID) -> AgentInfo | None:
        return self._managers.get(department_id)


class FakePerformanceSource:
    """Nguồn hiệu suất giả: test bơm sẵn giá trị thực đạt theo (đối tượng, chỉ số, kỳ)."""

    def __init__(self) -> None:
        self.user_metrics: dict[tuple[UUID, KpiMetricType, KpiPeriod], Decimal] = {}
        self.dept_metrics: dict[tuple[UUID, KpiMetricType, KpiPeriod], Decimal] = {}

    def set_user_metric(
        self, user_id: UUID, metric: KpiMetricType, period: KpiPeriod, value: Decimal
    ) -> None:
        self.user_metrics[(user_id, metric, period)] = value

    def set_department_metric(
        self, department_id: UUID, metric: KpiMetricType, period: KpiPeriod, value: Decimal
    ) -> None:
        self.dept_metrics[(department_id, metric, period)] = value

    async def get_metric_for_user(
        self, user_id: UUID, metric_type: KpiMetricType, period: KpiPeriod
    ) -> Decimal | None:
        return self.user_metrics.get((user_id, metric_type, period))

    async def get_metric_for_department(
        self, department_id: UUID, metric_type: KpiMetricType, period: KpiPeriod
    ) -> Decimal | None:
        return self.dept_metrics.get((department_id, metric_type, period))


class FakeNotifier:
    def __init__(self) -> None:
        self.signals: list[tuple[UUID, UUID, str]] = []

    async def notify_request_changed(
        self, request_id: UUID, recipient_user_id: UUID, change: str
    ) -> None:
        self.signals.append((request_id, recipient_user_id, change))
