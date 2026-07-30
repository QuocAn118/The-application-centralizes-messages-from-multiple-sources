"""Cầu nối assignment → identity + #4(hrm) + #1(inbox): gom ứng viên một phòng.

Implementation ``IAgentPool`` — chỗ DUY NHẤT (cùng các bridge khác) assignment
được biết các module kia tồn tại. Với mỗi nhân viên active của phòng, gom:
- ``on_shift``: có buổi phân ca ACTIVE hôm nay bao thời điểm hiện tại (#4). Giờ ca
  (#4) lưu theo **giờ nghiệp vụ địa phương** (nhân viên nhập "ca sáng 08:00" theo
  giờ VN), trong khi ``clock.now()`` là UTC — nên phải quy đổi UTC → giờ địa
  phương (``timezone``) trước khi so, nếu không sẽ lệch đúng bằng offset và gần
  như không ai được coi là trong ca.
- ``open_load``: số hội thoại DANG_MO đang gán cho họ (#1).
- ``last_assigned_at``: **proxy thô** = ``max(updated_at)`` của hội thoại đã gán
  họ. ``updated_at`` bị bước bởi cả đóng/nhận-tin-mới lẫn gán, nên đây thực chất
  là "mốc hoạt động gần nhất", KHÔNG phải "mốc gán". Dùng phá hoà round-robin
  (tiebreaker thứ 4, hiếm tới) nên lệch nhỏ chấp nhận được; ``assignment_log``
  (#5) mới cho mốc gán chính xác.
- ``kpi_percent``: **NỢ** — hiện để ``None``. Tính KPI đủ nghĩa cần chốt "chỉ số
  định tuyến chuẩn" + kỳ + nguồn hiệu suất (quyết định nghiệp vụ chưa có). KPI là
  tiêu chí phá hoà thứ 3, ``None`` được selector xử như thấp nhất (trung tính giữa
  các ứng viên hoà tải) nên chưa nối vẫn đúng thứ tự ưu tiên còn lại.
"""

from datetime import date, datetime, time
from uuid import UUID
from zoneinfo import ZoneInfo

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

    def __init__(self, session: AsyncSession, clock: IClock, timezone: str) -> None:
        self._session = session
        self._user_repo = SqlAlchemyUserRepository(session)
        self._shift_repo = SqlAlchemyShiftAssignmentRepository(session)
        self._clock = clock
        self._tz = ZoneInfo(timezone)

    async def candidates_for_department(self, department_id: UUID) -> tuple[AgentCandidate, ...]:
        # Quy đổi UTC → giờ nghiệp vụ địa phương để so với giờ ca (#4 lưu theo giờ
        # địa phương). ``hom_nay``/``gio`` phải lấy SAU khi đổi múi để không lệch
        # ngày quanh nửa đêm.
        local = self._clock.now().astimezone(self._tz)
        hom_nay = local.date()
        gio = local.time()

        # Nhân viên active của phòng: cả STAFF lẫn MANAGER đều có thể nhận việc.
        users = [
            *await self._user_repo.list_users(
                department_id=department_id, role=Role.STAFF, is_active=True, limit=1000
            ),
            *await self._user_repo.list_users(
                department_id=department_id, role=Role.MANAGER, is_active=True, limit=1000
            ),
        ]

        # N+1: 3 truy vấn mỗi nhân viên. Chấp nhận ở bản đầu (phòng thường vài tới
        # vài chục người); gộp thành truy vấn tổng hợp theo phòng là tối ưu để sau.
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
