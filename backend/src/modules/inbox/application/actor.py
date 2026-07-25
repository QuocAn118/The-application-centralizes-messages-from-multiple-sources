"""Người gọi use case, mô tả trung lập với module identity.

Inbox không được import ``identity.User``. Presentation dựng ``InboxActor`` này
từ JWT (đã chứa user_id, role, department_id) rồi truyền vào use case. Nhờ vậy
tầng application của inbox biết ai đang gọi và quyền của họ mà không phụ thuộc
identity.
"""

from dataclasses import dataclass
from enum import StrEnum
from uuid import UUID


class ActorRole(StrEnum):
    """Vai trò của người gọi, phản chiếu ``Role`` bên identity qua giá trị chuỗi.

    Cố ý là enum riêng của inbox: hai module dùng chung *giá trị* ("ADMIN",
    "MANAGER", "STAFF") chứ không chung *kiểu*, để không nối phụ thuộc.
    """

    ADMIN = "ADMIN"
    MANAGER = "MANAGER"
    STAFF = "STAFF"


@dataclass(frozen=True)
class InboxActor:
    """Danh tính tối thiểu của người gọi để phân quyền trong inbox."""

    user_id: UUID
    role: ActorRole
    department_id: UUID | None = None
