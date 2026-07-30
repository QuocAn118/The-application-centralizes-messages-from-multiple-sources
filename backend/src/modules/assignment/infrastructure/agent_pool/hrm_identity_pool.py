"""Cầu nối assignment → identity + #4(hrm) + #1(inbox): gom ứng viên một phòng.

Implementation ``IAgentPool`` — chỗ DUY NHẤT (cùng các bridge khác) assignment
được biết các module kia tồn tại. Với mỗi nhân viên active của phòng, gom:
- ``on_shift``: có buổi phân ca ACTIVE hôm nay bao thời điểm hiện tại (#4).
- ``open_load``: số hội thoại DANG_MO đang gán cho họ (#1).
- ``last_assigned_at``: mốc gán gần nhất (suy từ hội thoại đã gán họ — #1).
- ``kpi_percent``: **NỢ** — hiện để ``None``. Tính KPI đủ nghĩa cần chốt "chỉ số
  định tuyến chuẩn" + kỳ + nguồn hiệu suất (quyết định nghiệp vụ chưa có). KPI là
  tiêu chí phá hoà thứ 3, ``None`` được selector xử như thấp nhất (trung tính giữa
  các ứng viên hoà tải) nên chưa nối vẫn đúng thứ tự ưu tiên còn lại.
"""

from datetime import date, datetime, time
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.modules.assignment.domain.value_objects.candidate import AgentCandidate
from src.modules.hrm.infrastructure.repositories.shift_assignment_repository import (
    SqlAlchemyShiftAssignmentRepository,
)
from src.modules.identity.domain.value_objects.role import Role
from src.modules.identity.infrastructure.repositories.user_repository import (
    SqlAlchemyUserRepository,
)
from src.modules.inbox.domain.entities.conversation import ConversationStatus
from src.modules.inbox.infrastructure.models.conversation_model import ConversationModel
from src.shared.application.ports import IClock


class HrmIdentityAgentPool:
    """Gom ứng viên của một phòng từ identity + ca (#4) + tải hội thoại (#1)."""

    def __init__(self, session: AsyncSession, clock: IClock) -> None:
        self._session = session
        self._user_repo = SqlAlchemyUserRepository(session)
        self._shift_repo = SqlAlchemyShiftAssignmentRepository(session)
        self._clock = clock

    async def candidates_for_department(self, department_id: UUID) -> tuple[AgentCandidate, ...]:
        now = self._clock.now()
        hom_nay = now.date()
        gio = now.timetz().replace(tzinfo=None)

        # Nhân viên active của phòng: cả STAFF lẫn MANAGER đều có thể nhận việc.
        users = [
            *await self._user_repo.list_users(
                department_id=department_id, role=Role.STAFF, is_active=True, limit=1000
            ),
            *await self._user_repo.list_users(
                department_id=department_id, role=Role.MANAGER, is_active=True, limit=1000
            ),
        ]

        candidates: list[AgentCandidate] = []
        for user in users:
            candidates.append(
                AgentCandidate(
                    user_id=user.id,
                    on_shift=await self._dang_trong_ca(user.id, hom_nay, gio),
                    open_load=await self._tai_dang_giu(user.id),
                    kpi_percent=None,  # NỢ: xem docstring module.
                    last_assigned_at=await self._moc_gan_gan_nhat(user.id),
                )
            )
        return tuple(candidates)

    async def _dang_trong_ca(self, user_id: UUID, hom_nay: date, gio: time) -> bool:
        buoi = await self._shift_repo.list_active_for_user_on_date(user_id, hom_nay)
        return any(b.start_time <= gio <= b.end_time for b in buoi)

    async def _tai_dang_giu(self, user_id: UUID) -> int:
        ket_qua = await self._session.execute(
            select(func.count())
            .select_from(ConversationModel)
            .where(
                ConversationModel.assigned_user_id == user_id,
                ConversationModel.status == ConversationStatus.DANG_MO.value,
            )
        )
        return ket_qua.scalar_one()

    async def _moc_gan_gan_nhat(self, user_id: UUID) -> datetime | None:
        # Suy mốc gán gần nhất từ updated_at của hội thoại đã gán họ (bản đầu —
        # nợ assignment_log nếu cần chính xác tuyệt đối, xem plan).
        ket_qua = await self._session.execute(
            select(func.max(ConversationModel.updated_at)).where(
                ConversationModel.assigned_user_id == user_id
            )
        )
        return ket_qua.scalar_one_or_none()
