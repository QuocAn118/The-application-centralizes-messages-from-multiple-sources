"""Người gọi use case, mô tả trung lập với module identity.

Keyword không được import ``identity.User``. Presentation dựng ``KeywordActor``
này từ JWT rồi truyền vào use case.
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
class KeywordActor:
    """Danh tính tối thiểu của người gọi để phân quyền trong keyword."""

    user_id: UUID
    role: ActorRole
    department_id: UUID | None = None
