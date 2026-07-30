"""Quy tắc phân quyền cho endpoint kéo hàng đợi thủ công của assignment.

Kéo hàng đợi một phòng (``POST /departments/{id}/auto-assign``): Admin mọi phòng;
Manager chỉ phòng mình; Staff không được (việc điều phối thuộc quản lý). Thống nhất
mô hình quyền định tuyến (nợ F1 của #2): auto-assign chỉ trong phòng của hội thoại;
kéo thủ công giới hạn Manager theo phòng mình / Admin toàn cục.
"""

from uuid import UUID

from src.modules.assignment.application.actor import ActorRole, AssignmentActor
from src.shared.application.exceptions import PermissionDeniedError


def bao_dam_dieu_phoi_duoc_phong(actor: AssignmentActor, department_id: UUID) -> None:
    """Chỉ Admin (mọi phòng) hoặc Manager của đúng phòng mới kéo hàng đợi."""
    if actor.role is ActorRole.ADMIN:
        return
    if actor.role is ActorRole.MANAGER and actor.department_id == department_id:
        return
    raise PermissionDeniedError(
        "Chỉ quản trị viên hoặc quản lý phòng được kéo hàng đợi phòng này.",
        code="ASSIGNMENT_OUT_OF_SCOPE",
    )
