"""Người gọi use case, mô tả trung lập với module identity.

Hrm không được import ``identity.User``. Presentation dựng ``HrmActor`` này từ
JWT (đã chứa user_id, role, department_id) rồi truyền vào use case. Nhờ vậy
tầng application của hrm biết ai đang gọi và quyền của họ mà không phụ thuộc
identity.
"""

from dataclasses import dataclass
from enum import StrEnum
from uuid import UUID


class ActorRole(StrEnum):
    """Vai trò của người gọi, phản chiếu ``Role`` bên identity qua giá trị chuỗi.

    Cố ý là enum riêng của hrm: các module dùng chung *giá trị* ("ADMIN",
    "MANAGER", "STAFF") chứ không chung *kiểu*, để không nối phụ thuộc.
    """

    ADMIN = "ADMIN"
    MANAGER = "MANAGER"
    STAFF = "STAFF"


@dataclass(frozen=True)
class HrmActor:
    """Danh tính tối thiểu của người gọi để phân quyền trong hrm."""

    user_id: UUID
    role: ActorRole
    department_id: UUID | None = None
