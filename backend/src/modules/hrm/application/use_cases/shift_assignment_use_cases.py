"""Use case phân ca — gán mẫu ca cho nhân viên theo ngày, chống chồng ca.

Chồng ca được chặn ở đây (đọc các buổi hiện có rồi so), không ở DB: đủ cho #4.
Nếu cần chống race condition tuyệt đối khi hai Manager phân đồng thời, thêm ràng
buộc DB — đã ghi nợ trong spec §10.
"""

from datetime import date
from uuid import UUID

from src.modules.hrm.application.actor import ActorRole, HrmActor
from src.modules.hrm.application.authorization import (
    bao_dam_quan_ly_dung_phong,
    bao_dam_quan_ly_hoac_admin,
    pham_vi_phong_doc,
)
from src.modules.hrm.application.dto.hrm_dto import ShiftAssignmentView
from src.modules.hrm.domain.entities.shift_assignment import ShiftAssignment
from src.modules.hrm.domain.ports import IWorkforceDirectory
from src.modules.hrm.domain.repositories.shift_assignment_repository import (
    IShiftAssignmentRepository,
)
from src.modules.hrm.domain.repositories.shift_repository import IShiftRepository
from src.shared.application.exceptions import ConflictError, NotFoundError, PermissionDeniedError
from src.shared.application.ports import IClock


def _view(a: ShiftAssignment) -> ShiftAssignmentView:
    return ShiftAssignmentView(
        id=a.id,
        shift_id=a.shift_id,
        user_id=a.user_id,
        department_id=a.department_id,
        work_date=a.work_date,
        start_time=a.start_time,
        end_time=a.end_time,
        status=a.status,
    )


class ShiftOverlapError(ConflictError):
    """Nhân viên đã có một buổi ca giẫm giờ trong ngày đó."""

    def __init__(self) -> None:
        super().__init__(
            "Nhân viên đã có một ca giẫm giờ trong ngày này.",
            code="SHIFT_OVERLAP",
        )


class AssignShift:
    """Phân một buổi ca cho một nhân viên vào một ngày."""

    def __init__(
        self,
        assignment_repo: IShiftAssignmentRepository,
        shift_repo: IShiftRepository,
        directory: IWorkforceDirectory,
        clock: IClock,
    ) -> None:
        self._assignment_repo = assignment_repo
        self._shift_repo = shift_repo
        self._directory = directory
        self._clock = clock

    async def execute(
        self, actor: HrmActor, shift_id: UUID, user_id: UUID, work_date: date
    ) -> ShiftAssignmentView:
        bao_dam_quan_ly_hoac_admin(actor)

        shift = await self._shift_repo.get_by_id(shift_id)
        if shift is None or not shift.is_active:
            raise NotFoundError("Không tìm thấy mẫu ca đang hoạt động.", code="SHIFT_NOT_FOUND")

        # Manager chỉ phân ca của phòng mình.
        bao_dam_quan_ly_dung_phong(actor, shift.department_id)

        # Nhân viên phải tồn tại, đang active, và thuộc đúng phòng của mẫu ca.
        agent = await self._directory.get_agent(user_id)
        if agent is None or not agent.is_active:
            raise NotFoundError("Không tìm thấy nhân viên đang hoạt động.", code="AGENT_NOT_FOUND")
        if agent.department_id != shift.department_id:
            raise PermissionDeniedError(
                "Nhân viên không thuộc phòng của mẫu ca này.",
                code="AGENT_OUT_OF_DEPARTMENT",
            )

        now = self._clock.now()
        # Tạo trước để domain chặn ngày quá khứ / giờ ngược, rồi mới kiểm chồng.
        assignment = ShiftAssignment.assign(
            shift_id=shift.id,
            user_id=user_id,
            department_id=shift.department_id,
            work_date=work_date,
            start_time=shift.start_time,
            end_time=shift.end_time,
            now=now,
        )

        existing = await self._assignment_repo.list_active_for_user_on_date(user_id, work_date)
        if any(assignment.overlaps(e) for e in existing):
            raise ShiftOverlapError

        await self._assignment_repo.add(assignment)
        return _view(assignment)


class CancelShiftAssignment:
    """Huỷ một buổi phân ca."""

    def __init__(self, assignment_repo: IShiftAssignmentRepository, clock: IClock) -> None:
        self._assignment_repo = assignment_repo
        self._clock = clock

    async def execute(self, actor: HrmActor, assignment_id: UUID) -> ShiftAssignmentView:
        bao_dam_quan_ly_hoac_admin(actor)
        assignment = await self._assignment_repo.get_by_id(assignment_id)
        if assignment is None:
            raise NotFoundError("Không tìm thấy buổi phân ca.", code="SHIFT_ASSIGNMENT_NOT_FOUND")
        bao_dam_quan_ly_dung_phong(actor, assignment.department_id)

        assignment.cancel(self._clock.now())
        await self._assignment_repo.update(assignment)
        return _view(assignment)


class ListShiftAssignments:
    """Liệt kê buổi phân ca theo phạm vi người gọi.

    Admin: tất cả. Manager: cả phòng mình. Staff: chỉ ca của chính mình.
    """

    def __init__(self, assignment_repo: IShiftAssignmentRepository) -> None:
        self._assignment_repo = assignment_repo

    async def execute(
        self,
        actor: HrmActor,
        date_from: date | None = None,
        date_to: date | None = None,
    ) -> list[ShiftAssignmentView]:
        if actor.role is ActorRole.STAFF:
            user_ids: list[UUID] | None = [actor.user_id]
            department_ids: list[UUID] | None = None
        else:
            user_ids = None
            department_ids = pham_vi_phong_doc(actor)

        items = await self._assignment_repo.list_for_scope(
            user_ids, department_ids, date_from, date_to
        )
        return [_view(a) for a in items]
