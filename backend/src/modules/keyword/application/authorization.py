"""Quy tắc phân quyền dùng chung cho các use case keyword.

- CRUD từ khoá: chỉ Manager (phòng mình) và Admin.
- Xem từ khoá / phân tích: Admin tất cả; Manager phòng mình; Staff phòng mình.
  Biểu diễn bằng "danh sách phòng được phép" (``None`` = không giới hạn).
"""

from uuid import UUID

from src.modules.keyword.application.actor import ActorRole, KeywordActor
from src.shared.application.exceptions import PermissionDeniedError


def bao_dam_quan_ly_hoac_admin(actor: KeywordActor) -> None:
    """Chỉ Manager hoặc Admin mới CRUD từ khoá."""
    if actor.role not in (ActorRole.ADMIN, ActorRole.MANAGER):
        raise PermissionDeniedError(
            "Chỉ quản lý hoặc quản trị viên được quản lý từ khoá.",
            code="KEYWORD_MANAGER_REQUIRED",
        )


def bao_dam_quan_ly_dung_phong(actor: KeywordActor, department_id: UUID) -> None:
    """Manager chỉ thao tác trong phòng mình; Admin mọi phòng.

    Gọi sau ``bao_dam_quan_ly_hoac_admin`` — ở đây chỉ còn phân biệt Manager với
    Admin.
    """
    if actor.role is ActorRole.ADMIN:
        return
    if actor.department_id != department_id:
        raise PermissionDeniedError(
            "Bạn chỉ được quản lý từ khoá của phòng mình.",
            code="KEYWORD_OUT_OF_SCOPE",
        )


def pham_vi_phong_doc(actor: KeywordActor) -> list[UUID] | None:
    """Danh sách phòng được xem, ``None`` = không giới hạn (Admin).

    Manager/Staff: đúng phòng mình. Người không thuộc phòng nào (bất thường với
    Manager/Staff) → danh sách rỗng, không thấy gì.
    """
    if actor.role is ActorRole.ADMIN:
        return None
    if actor.department_id is None:
        return []
    return [actor.department_id]
