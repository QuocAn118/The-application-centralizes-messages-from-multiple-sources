"""Người gọi use case báo cáo, mô tả trung lập với module identity.

Analytics không được import ``identity.User``. Presentation dựng
``AnalyticsActor`` từ JWT rồi truyền vào. Các use case incremental/backfill chạy
như hành động hệ thống (hook/vận hành), không cần actor.
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
class AnalyticsActor:
    """Danh tính tối thiểu của người gọi để phân quyền trong analytics."""

    user_id: UUID
    role: ActorRole
    department_id: UUID | None = None
