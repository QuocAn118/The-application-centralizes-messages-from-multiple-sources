"""Cầu nối assignment → identity + #4(hrm) + #1(inbox): gom ứng viên một phòng.

Implementation ``IAgentPool`` — chỗ DUY NHẤT (cùng các bridge khác) assignment
được biết các module kia tồn tại. Với mỗi nhân viên active của phòng, gom:
- ``on_shift``: có buổi phân ca ACTIVE hôm nay bao thời điểm hiện tại (#4). Giờ ca
  (#4) lưu theo **giờ nghiệp vụ địa phương** (nhân viên nhập "ca sáng 08:00" theo
  giờ VN), trong khi ``clock.now()`` là UTC — nên phải quy đổi UTC → giờ địa
  phương (``timezone``) trước khi so, nếu không sẽ lệch đúng bằng offset và gần
  như không ai được coi là trong ca.
- ``open_load``: số hội thoại DANG_MO đang gán cho họ (#1).
- ``last_assigned_at``: mốc gán gần nhất **chính xác** = ``max(assigned_at)`` trong
  ``assignment_log`` (#3). Trước đây là proxy ``max(updated_at)`` hội thoại (bị bước
  bởi đóng/nhận-tin); nay dùng nhật ký gán thật. Phá hoà round-robin (tiebreaker
  thứ 4). Hội thoại gán tay (chưa qua auto-assign) không có dòng log → người đó xem
  như "chưa từng được hệ thống gán" (None, ưu tiên round-robin sớm) — đúng ngữ nghĩa.
- ``kpi_percent``: % hoàn thành mục tiêu ``CONVERSATIONS_CLOSED`` của THÁNG HIỆN TẠI
  (chốt 2026-08-04). Ghép mục tiêu (#4 KpiTarget) với thực đạt (#4 nguồn hiệu suất
  Inbox) qua ``tinh_phan_tram_kpi``. Người dưới target (thấp hơn) được selector ưu
  tiên nhận thêm việc. Nhân viên **chưa đặt target** tháng này → ``None`` (selector
  xử như thấp nhất, trung tính). Kỳ lấy theo giờ địa phương ``timezone``.
"""

from datetime import date, datetime, time
from decimal import Decimal
from uuid import UUID
from zoneinfo import ZoneInfo

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.modules.assignment.domain.value_objects.candidate import AgentCandidate
from src.modules.assignment.infrastructure.persistence.assignment_log_model import (
    AssignmentLogModel,
)
from src.modules.hrm.domain.services.kpi_achievement import tinh_phan_tram_kpi
from src.modules.hrm.domain.value_objects.kpi import (
    KpiMetricType,
    KpiPeriod,
    KpiSubjectType,
)
from src.modules.hrm.infrastructure.performance.inbox_performance_source import (
    InboxPerformanceSource,
)
from src.modules.hrm.infrastructure.repositories.kpi_target_repository import (
    SqlAlchemyKpiTargetRepository,
)
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

# Chỉ số dùng định tuyến (chốt 2026-08-04): % hoàn thành mục tiêu số hội thoại đóng
# trong THÁNG HIỆN TẠI. Người dưới target được ưu tiên nhận thêm việc để đạt KPI.
_METRIC_DINH_TUYEN = KpiMetricType.CONVERSATIONS_CLOSED


class HrmIdentityAgentPool:
    """Gom ứng viên của một phòng từ identity + ca (#4) + tải hội thoại (#1)."""

    def __init__(self, session: AsyncSession, clock: IClock, timezone: str) -> None:
        self._session = session
        self._user_repo = SqlAlchemyUserRepository(session)
        self._shift_repo = SqlAlchemyShiftAssignmentRepository(session)
        self._target_repo = SqlAlchemyKpiTargetRepository(session)
        self._performance = InboxPerformanceSource(session)
        self._clock = clock
        self._tz = ZoneInfo(timezone)

    async def candidates_for_department(self, department_id: UUID) -> tuple[AgentCandidate, ...]:
        # Quy đổi UTC → giờ nghiệp vụ địa phương để so với giờ ca (#4 lưu theo giờ
        # địa phương). ``hom_nay``/``gio`` phải lấy SAU khi đổi múi để không lệch
        # ngày quanh nửa đêm.
        local = self._clock.now().astimezone(self._tz)
        hom_nay = local.date()
        gio = local.time()
        ky = KpiPeriod(year=local.year, month=local.month)

        # Nhân viên active của phòng: cả STAFF lẫn MANAGER đều có thể nhận việc.
        users = [
            *await self._user_repo.list_users(
                department_id=department_id, role=Role.STAFF, is_active=True, limit=1000
            ),
            *await self._user_repo.list_users(
                department_id=department_id, role=Role.MANAGER, is_active=True, limit=1000
            ),
        ]

        # Mục tiêu KPI định tuyến của phòng cho kỳ hiện tại — MỘT truy vấn, index
        # theo subject_id (user). Chỉ giữ mục tiêu cấp NHÂN VIÊN đúng chỉ số.
        muc_tieu = {
            t.subject_id: t.target_value
            for t in await self._target_repo.list_in_scope([department_id], period=ky)
            if t.subject_type is KpiSubjectType.USER and t.metric_type is _METRIC_DINH_TUYEN
        }

        # N+1: vài truy vấn mỗi nhân viên (ca, tải, mốc gán, thực đạt KPI nếu có
        # target). Chấp nhận ở bản đầu (phòng thường vài tới vài chục người); gộp
        # thành truy vấn tổng hợp theo phòng là tối ưu để sau.
        candidates: list[AgentCandidate] = []
        for user in users:
            candidates.append(
                AgentCandidate(
                    user_id=user.id,
                    on_shift=await self._dang_trong_ca(user.id, hom_nay, gio),
                    open_load=await self._tai_dang_giu(user.id),
                    kpi_percent=await self._kpi_percent(user.id, muc_tieu.get(user.id), ky),
                    last_assigned_at=await self._moc_gan_gan_nhat(user.id),
                )
            )
        return tuple(candidates)

    async def _kpi_percent(
        self, user_id: UUID, target: Decimal | None, ky: KpiPeriod
    ) -> Decimal | None:
        """% hoàn thành ``CONVERSATIONS_CLOSED`` kỳ hiện tại; ``None`` nếu chưa có
        target (selector xử như thấp nhất — trung tính giữa các ứng viên hoà tải)."""
        if target is None:
            return None
        actual = await self._performance.get_metric_for_user(user_id, _METRIC_DINH_TUYEN, ky)
        return tinh_phan_tram_kpi(_METRIC_DINH_TUYEN, target, actual)

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
        # Mốc gán gần nhất CHÍNH XÁC từ assignment_log (#3) — nhật ký mỗi lần gán
        # thật, không phải proxy updated_at (vốn bị bước bởi đóng/nhận-tin).
        ket_qua = await self._session.execute(
            select(func.max(AssignmentLogModel.assigned_at)).where(
                AssignmentLogModel.user_id == user_id
            )
        )
        return ket_qua.scalar_one_or_none()
