"""Người gọi use case, mô tả trung lập với module identity.

Assignment không được import ``identity.User``. Presentation dựng
``AssignmentActor`` từ JWT rồi truyền vào (chỉ dùng ở endpoint kéo hàng đợi thủ
công; các trigger tự động chạy như hành động hệ thống, không cần actor).
"""

from dataclasses import dataclass
from enum import StrEnum
from uuid import UUID


class ActorRole(StrEnum):
    """Vai trò người gọi, phản chiếu ``Role`` bên identity qua giá trị chuỗi."""

    ADMIN = "ADMIN"
    MANAGER = "MANAGER"
    STAFF = "STAFF"


@dataclass(frozen=True)
class AssignmentActor:
    """Danh tính tối thiểu của người gọi để phân quyền trong assignment."""

    user_id: UUID
    role: ActorRole
    department_id: UUID | None = None
