"""Use case CRUD mẫu ca — Manager (phòng mình) và Admin.

Gom bốn thao tác đơn giản của mẫu ca vào một file: chúng chia sẻ cùng repository
và cùng luật phân quyền. Bản thân bất biến khung giờ nằm trong entity ``Shift``.
"""

from datetime import time
from uuid import UUID

from src.modules.hrm.application.actor import HrmActor
from src.modules.hrm.application.authorization import (
    bao_dam_quan_ly_dung_phong,
    bao_dam_quan_ly_hoac_admin,
    pham_vi_phong_doc,
)
from src.modules.hrm.application.dto.hrm_dto import ShiftView
from src.modules.hrm.domain.entities.shift import Shift
from src.modules.hrm.domain.ports import IWorkforceDirectory
from src.modules.hrm.domain.repositories.shift_repository import IShiftRepository
from src.shared.application.exceptions import NotFoundError
from src.shared.application.ports import IClock


def _view(shift: Shift) -> ShiftView:
    return ShiftView(
        id=shift.id,
        department_id=shift.department_id,
        name=shift.name,
        start_time=shift.start_time,
        end_time=shift.end_time,
        is_active=shift.is_active,
    )


def _khong_thay_ca() -> NotFoundError:
    return NotFoundError("Không tìm thấy mẫu ca.", code="SHIFT_NOT_FOUND")


class CreateShift:
    """Tạo một mẫu ca cho một phòng ban."""

    def __init__(
        self,
        shift_repo: IShiftRepository,
        directory: IWorkforceDirectory,
        clock: IClock,
    ) -> None:
        self._shift_repo = shift_repo
        self._directory = directory
        self._clock = clock

    async def execute(
        self,
        actor: HrmActor,
        department_id: UUID,
        name: str,
        start_time: time,
        end_time: time,
    ) -> ShiftView:
        bao_dam_quan_ly_hoac_admin(actor)
        bao_dam_quan_ly_dung_phong(actor, department_id)

        if not await self._directory.department_exists_active(department_id):
            raise NotFoundError(
                "Không tìm thấy phòng ban đang hoạt động.", code="DEPARTMENT_NOT_FOUND"
            )

        shift = Shift.create(
            department_id=department_id,
            name=name,
            start_time=start_time,
            end_time=end_time,
            now=self._clock.now(),
        )
        await self._shift_repo.add(shift)
        return _view(shift)


class UpdateShift:
    """Đổi tên/khung giờ một mẫu ca."""

    def __init__(self, shift_repo: IShiftRepository, clock: IClock) -> None:
        self._shift_repo = shift_repo
        self._clock = clock

    async def execute(
        self,
        actor: HrmActor,
        shift_id: UUID,
        name: str,
        start_time: time,
        end_time: time,
    ) -> ShiftView:
        bao_dam_quan_ly_hoac_admin(actor)
        shift = await self._shift_repo.get_by_id(shift_id)
        if shift is None:
            raise _khong_thay_ca()
        bao_dam_quan_ly_dung_phong(actor, shift.department_id)

        shift.update_window(name, start_time, end_time, self._clock.now())
        await self._shift_repo.update(shift)
        return _view(shift)


class DeactivateShift:
    """Vô hiệu hoá một mẫu ca (không xoá cứng)."""

    def __init__(self, shift_repo: IShiftRepository, clock: IClock) -> None:
        self._shift_repo = shift_repo
        self._clock = clock

    async def execute(self, actor: HrmActor, shift_id: UUID) -> ShiftView:
        bao_dam_quan_ly_hoac_admin(actor)
        shift = await self._shift_repo.get_by_id(shift_id)
        if shift is None:
            raise _khong_thay_ca()
        bao_dam_quan_ly_dung_phong(actor, shift.department_id)

        shift.deactivate(self._clock.now())
        await self._shift_repo.update(shift)
        return _view(shift)


class ListShifts:
    """Liệt kê mẫu ca theo phạm vi phòng ban của người gọi."""

    def __init__(self, shift_repo: IShiftRepository) -> None:
        self._shift_repo = shift_repo

    async def execute(self, actor: HrmActor, is_active: bool | None = None) -> list[ShiftView]:
        department_ids = pham_vi_phong_doc(actor)
        shifts = await self._shift_repo.list_for_departments(department_ids, is_active)
        return [_view(s) for s in shifts]
