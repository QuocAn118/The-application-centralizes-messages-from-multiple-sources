"""Quy tắc phân quyền dùng chung cho các use case hrm.

Gom về một chỗ để mọi use case áp cùng một luật. Ba loại phạm vi hay lặp lại:

- Quản lý ca/KPI: chỉ Manager (phòng mình) và Admin.
- Xem lịch/KPI/đơn: Admin thấy tất cả; Manager thấy phòng mình; Staff thấy của
  mình. Biểu diễn bằng "danh sách phòng được phép" và "chỉ của chính mình".
- Duyệt đơn: một cấp — Manager duyệt đơn Staff phòng mình; Admin duyệt đơn của
  Manager. Kiểm ở từng use case đơn từ vì phụ thuộc dữ liệu người gửi.
"""

from uuid import UUID

from src.modules.hrm.application.actor import ActorRole, HrmActor
from src.shared.application.exceptions import PermissionDeniedError


def bao_dam_quan_ly_hoac_admin(actor: HrmActor) -> None:
    """Chỉ Manager hoặc Admin mới được tạo/sửa ca, phân ca, đặt mục tiêu KPI."""
    if actor.role not in (ActorRole.ADMIN, ActorRole.MANAGER):
        raise PermissionDeniedError(
            "Chỉ quản lý hoặc quản trị viên được thực hiện thao tác này.",
            code="MANAGER_REQUIRED",
        )


def bao_dam_quan_ly_dung_phong(actor: HrmActor, department_id: UUID) -> None:
    """Manager chỉ thao tác trong phòng mình; Admin thao tác mọi phòng.

    Gọi sau ``bao_dam_quan_ly_hoac_admin`` — ở đây chỉ còn phân biệt Manager với
    Admin.
    """
    if actor.role is ActorRole.ADMIN:
        return
    if actor.department_id != department_id:
        raise PermissionDeniedError(
            "Bạn chỉ được thao tác trong phòng của mình.",
            code="OUT_OF_DEPARTMENT_SCOPE",
        )


def pham_vi_phong_doc(actor: HrmActor) -> list[UUID] | None:
    """Danh sách phòng mà người gọi được xem, hoặc ``None`` nghĩa là không giới hạn.

    Admin: ``None`` (tất cả). Manager: đúng phòng mình. Staff: cũng đúng phòng
    mình ở cấp truy vấn phòng, nhưng các use case xem-của-mình sẽ siết thêm về
    ``requester_id``/``user_id`` khi cần (ví dụ Staff chỉ xem đơn/ca của chính
    mình, không phải cả phòng).
    """
    if actor.role is ActorRole.ADMIN:
        return None
    if actor.department_id is None:
        return []
    return [actor.department_id]
