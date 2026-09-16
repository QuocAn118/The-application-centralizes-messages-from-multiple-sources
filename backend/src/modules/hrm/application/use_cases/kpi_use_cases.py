"""Use case KPI — đặt mục tiêu và xem tiến độ (mục tiêu ghép thực đạt).

Mục tiêu do Manager/Admin đặt; giá trị thực đạt lấy từ nguồn hiệu suất (Inbox)
qua ``IPerformanceSource`` — hrm không truy vấn inbox trực tiếp.
"""

from decimal import Decimal
from uuid import UUID

from src.modules.hrm.application.actor import ActorRole, HrmActor
from src.modules.hrm.application.authorization import (
    bao_dam_quan_ly_dung_phong,
    bao_dam_quan_ly_hoac_admin,
)
from src.modules.hrm.application.dto.hrm_dto import KpiProgressView, KpiTargetView
from src.modules.hrm.domain.entities.kpi_target import KpiTarget
from src.modules.hrm.domain.ports import IPerformanceSource, IWorkforceDirectory
from src.modules.hrm.domain.repositories.kpi_target_repository import (
    IKpiTargetRepository,
)
from src.modules.hrm.domain.services.kpi_achievement import tinh_phan_tram_kpi
from src.modules.hrm.domain.value_objects.kpi import (
    KpiMetricType,
    KpiPeriod,
    KpiSubjectType,
)
from src.shared.application.exceptions import NotFoundError, PermissionDeniedError
from src.shared.application.ports import IClock


def _target_view(t: KpiTarget) -> KpiTargetView:
    return KpiTargetView(
        id=t.id,
        subject_type=t.subject_type,
        subject_id=t.subject_id,
        department_id=t.department_id,
        metric_type=t.metric_type,
        period=t.period,
        target_value=t.target_value,
    )


class SetKpiTarget:
    """Đặt hoặc cập nhật mục tiêu KPI cho một nhân viên/phòng trong một kỳ."""

    def __init__(
        self,
        target_repo: IKpiTargetRepository,
        directory: IWorkforceDirectory,
        clock: IClock,
    ) -> None:
        self._target_repo = target_repo
        self._directory = directory
        self._clock = clock

    async def execute(
        self,
        actor: HrmActor,
        subject_type: KpiSubjectType,
        subject_id: UUID,
        metric_type: KpiMetricType,
        period: KpiPeriod,
        target_value: Decimal,
    ) -> KpiTargetView:
        bao_dam_quan_ly_hoac_admin(actor)

        # Xác định phòng của đối tượng để soi phạm vi Manager.
        if subject_type is KpiSubjectType.DEPARTMENT:
            department_id = subject_id
            if not await self._directory.department_exists_active(department_id):
                raise NotFoundError(
                    "Không tìm thấy phòng ban đang hoạt động.", code="DEPARTMENT_NOT_FOUND"
                )
        else:
            agent = await self._directory.get_agent(subject_id)
            if agent is None or not agent.is_active or agent.department_id is None:
                raise NotFoundError(
                    "Không tìm thấy nhân viên đang hoạt động.", code="AGENT_NOT_FOUND"
                )
            department_id = agent.department_id

        bao_dam_quan_ly_dung_phong(actor, department_id)

        now = self._clock.now()
        existing = await self._target_repo.get_for(subject_type, subject_id, metric_type, period)
        if existing is not None:
            existing.change_target(target_value, now)
            await self._target_repo.update(existing)
            return _target_view(existing)

        target = KpiTarget.set_target(
            subject_type=subject_type,
            subject_id=subject_id,
            department_id=department_id,
            metric_type=metric_type,
            period=period,
            target_value=target_value,
            now=now,
        )
        await self._target_repo.add(target)
        return _target_view(target)


class ListKpiTargets:
    """Liệt kê mục tiêu KPI theo phạm vi phòng ban của người gọi.

    Admin: tất cả. Manager: phòng mình. Staff: chỉ mục tiêu áp cho chính mình.
    """

    def __init__(self, target_repo: IKpiTargetRepository) -> None:
        self._target_repo = target_repo

    async def execute(
        self, actor: HrmActor, period: KpiPeriod | None = None
    ) -> list[KpiTargetView]:
        if actor.role is ActorRole.STAFF:
            # Staff chỉ thấy mục tiêu áp cho chính mình (một đối tượng).
            department_ids: list[UUID] | None = None
            subject_id: UUID | None = actor.user_id
        elif actor.role is ActorRole.MANAGER:
            # Manager thấy mọi mục tiêu trong phòng mình — cả cấp phòng lẫn cấp
            # nhân viên — nhờ department_id chụp sẵn trên từng mục tiêu.
            department_ids = [actor.department_id] if actor.department_id else []
            subject_id = None
        else:
            department_ids = None
            subject_id = None

        targets = await self._target_repo.list_in_scope(department_ids, subject_id, period)
        return [_target_view(t) for t in targets]


class ListKpiProgress:
    """Tiến độ của **mọi** mục tiêu trong phạm vi người gọi, gom theo lô.

    Thay cho việc client gọi ``GET /kpi-progress`` từng dòng: bảng KPI của Admin
    có thể vài chục dòng, mỗi dòng một lời gọi thì mỗi lời gọi lại quét lại toàn
    bộ dữ liệu inbox. Đo thật trên DB dev: 68 dòng ~2,1 giây, gom lại còn ~1 lời
    gọi.

    **Phạm vi an toàn theo thiết kế:** danh sách mục tiêu lấy qua đúng
    ``list_in_scope`` mà ``ListKpiTargets`` dùng (Staff chỉ mục tiêu của mình,
    Manager phòng mình, Admin tất cả), rồi chỉ tính tiến độ cho **chính những
    mục tiêu đó**. Không có tham số nào cho client chỉ định đối tượng, nên không
    có đường dò dữ liệu người khác — khác ``GetKpiProgress``, nơi client tự nêu
    ``subject_id`` nên bắt buộc phải kiểm quyền.
    """

    def __init__(
        self,
        target_repo: IKpiTargetRepository,
        performance: IPerformanceSource,
    ) -> None:
        self._target_repo = target_repo
        self._performance = performance

    async def execute(self, actor: HrmActor, period: KpiPeriod) -> list[KpiProgressView]:
        if actor.role is ActorRole.STAFF:
            department_ids: list[UUID] | None = None
            subject_id: UUID | None = actor.user_id
        elif actor.role is ActorRole.MANAGER:
            department_ids = [actor.department_id] if actor.department_id else []
            subject_id = None
        else:
            department_ids = None
            subject_id = None

        targets = await self._target_repo.list_in_scope(department_ids, subject_id, period)
        if not targets:
            return []

        # Gom theo chỉ số: mỗi chỉ số là một truy vấn cho tất cả đối tượng của
        # chỉ số đó. Hai chỉ số cho hai cấp -> tối đa BỐN truy vấn, thay vì N.
        nguoi_theo_chi_so: dict[KpiMetricType, list[UUID]] = {}
        phong_theo_chi_so: dict[KpiMetricType, list[UUID]] = {}
        for t in targets:
            gio = nguoi_theo_chi_so if t.subject_type is KpiSubjectType.USER else phong_theo_chi_so
            gio.setdefault(t.metric_type, []).append(t.subject_id)

        thuc_dat: dict[tuple[KpiSubjectType, KpiMetricType, UUID], Decimal | None] = {}
        for metric_type, uids in nguoi_theo_chi_so.items():
            ket_qua = await self._performance.get_metrics_for_users(uids, metric_type, period)
            for uid in uids:
                thuc_dat[(KpiSubjectType.USER, metric_type, uid)] = ket_qua.get(uid)
        for metric_type, dids in phong_theo_chi_so.items():
            ket_qua = await self._performance.get_metrics_for_departments(dids, metric_type, period)
            for did in dids:
                thuc_dat[(KpiSubjectType.DEPARTMENT, metric_type, did)] = ket_qua.get(did)

        views: list[KpiProgressView] = []
        for t in targets:
            actual = thuc_dat.get((t.subject_type, t.metric_type, t.subject_id))
            views.append(
                KpiProgressView(
                    subject_type=t.subject_type,
                    subject_id=t.subject_id,
                    metric_type=t.metric_type,
                    period=t.period,
                    target_value=t.target_value,
                    actual_value=actual,
                    achievement_percent=tinh_phan_tram_kpi(t.metric_type, t.target_value, actual),
                )
            )
        return views


class GetKpiProgress:
    """Trả mục tiêu KPI ghép với thực đạt và % hoàn thành cho một đối tượng/kỳ."""

    def __init__(
        self,
        target_repo: IKpiTargetRepository,
        performance: IPerformanceSource,
        directory: IWorkforceDirectory,
    ) -> None:
        self._target_repo = target_repo
        self._performance = performance
        self._directory = directory

    async def execute(
        self,
        actor: HrmActor,
        subject_type: KpiSubjectType,
        subject_id: UUID,
        metric_type: KpiMetricType,
        period: KpiPeriod,
    ) -> KpiProgressView:
        # Phạm vi xem: Staff chỉ xem của mình; Manager phòng mình; Admin tất cả.
        await self._bao_dam_xem_duoc(actor, subject_type, subject_id)

        target = await self._target_repo.get_for(subject_type, subject_id, metric_type, period)
        if target is None:
            raise NotFoundError(
                "Chưa đặt mục tiêu KPI cho đối tượng/kỳ này.", code="KPI_TARGET_NOT_FOUND"
            )

        if subject_type is KpiSubjectType.USER:
            actual = await self._performance.get_metric_for_user(subject_id, metric_type, period)
        else:
            actual = await self._performance.get_metric_for_department(
                subject_id, metric_type, period
            )

        return KpiProgressView(
            subject_type=subject_type,
            subject_id=subject_id,
            metric_type=metric_type,
            period=period,
            target_value=target.target_value,
            actual_value=actual,
            achievement_percent=tinh_phan_tram_kpi(metric_type, target.target_value, actual),
        )

    async def _bao_dam_xem_duoc(
        self, actor: HrmActor, subject_type: KpiSubjectType, subject_id: UUID
    ) -> None:
        if actor.role is ActorRole.ADMIN:
            return

        if subject_type is KpiSubjectType.USER:
            if actor.role is ActorRole.STAFF:
                if subject_id != actor.user_id:
                    raise self._tu_choi()
                return
            # Manager: nhân viên phải thuộc phòng mình.
            agent = await self._directory.get_agent(subject_id)
            if agent is None or agent.department_id != actor.department_id:
                raise self._tu_choi()
            return

        # subject là phòng: Staff không xem KPI cấp phòng; Manager chỉ phòng mình.
        if actor.role is ActorRole.STAFF or subject_id != actor.department_id:
            raise self._tu_choi()

    @staticmethod
    def _tu_choi() -> PermissionDeniedError:
        return PermissionDeniedError(
            "Bạn không có quyền xem KPI của đối tượng này.", code="KPI_FORBIDDEN"
        )
