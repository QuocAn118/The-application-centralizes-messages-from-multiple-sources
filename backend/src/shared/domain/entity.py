"""Lớp cơ sở cho entity trong tầng domain."""

from dataclasses import dataclass, field
from uuid import UUID

from src.shared.domain.identifiers import new_id


@dataclass(eq=False, kw_only=True)
class Entity:
    """Entity được định danh bằng ``id``, không phải bằng giá trị thuộc tính.

    Hai entity bằng nhau khi cùng ``id``, dù các thuộc tính khác khác nhau.
    """

    id: UUID = field(default_factory=new_id)

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Entity):
            return NotImplemented
        if type(self) is not type(other):
            return False
        return self.id == other.id

    def __hash__(self) -> int:
        return hash((type(self).__name__, self.id))


@dataclass(eq=False, kw_only=True)
class AggregateRoot(Entity):
    """Entity đóng vai trò điểm vào của một aggregate.

    Repository chỉ làm việc với aggregate root, không truy cập trực tiếp
    các entity con bên trong aggregate.
    """
