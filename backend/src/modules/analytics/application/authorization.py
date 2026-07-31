"""Quy tắc phân quyền cho báo cáo analytics.

Báo cáo tổng hợp chỉ dành cho **Manager (phòng mình) / Admin (mọi phòng)** —
Staff KHÔNG xem số liệu tổng hợp toàn phòng. Manager bị ép phạm vi về phòng mình:
dù truyền ``department_id`` nào, kết quả vẫn chỉ của phòng họ (RB-4).

``pham_vi_phong_bao_cao`` trả **danh sách phòng được phép** để lọc:
- Admin: ``None`` (không giới hạn) — nếu Admin truyền ``department_id`` cụ thể thì
  giới hạn đúng phòng đó.
- Manager: luôn ``[department_id của họ]`` bất kể tham số truyền vào.
- Staff / người không phòng: bị chặn (``PermissionDeniedError``).
"""

from uuid import UUID

from src.modules.analytics.application.actor import ActorRole, AnalyticsActor
from src.shared.application.exceptions import PermissionDeniedError


def bao_dam_xem_bao_cao(actor: AnalyticsActor) -> None:
    """Chỉ Manager hoặc Admin được xem báo cáo tổng hợp."""
    if actor.role not in (ActorRole.ADMIN, ActorRole.MANAGER):
        raise PermissionDeniedError(
            "Chỉ quản lý hoặc quản trị viên được xem báo cáo.",
            code="ANALYTICS_MANAGER_REQUIRED",
        )


def pham_vi_phong_bao_cao(
    actor: AnalyticsActor, department_id: UUID | None
) -> tuple[UUID, ...] | None:
    """Danh sách phòng được phép cho báo cáo; ``None`` = không giới hạn (Admin).

    Gọi sau ``bao_dam_xem_bao_cao``. Manager luôn bị ép về phòng mình (không xem
    phòng khác kể cả khi truyền ``department_id`` khác); Manager không thuộc phòng
    nào bị chặn (bất thường).
    """
    if actor.role is ActorRole.ADMIN:
        return (department_id,) if department_id is not None else None
    # Manager: ép về phòng mình.
    if actor.department_id is None:
        raise PermissionDeniedError(
            "Quản lý không thuộc phòng nào không có báo cáo.",
            code="ANALYTICS_MANAGER_NO_DEPARTMENT",
        )
    return (actor.department_id,)
