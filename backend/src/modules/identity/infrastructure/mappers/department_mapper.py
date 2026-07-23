"""Chuyển đổi giữa ORM model và domain entity của phòng ban."""

from src.modules.identity.domain.entities.department import Department
from src.modules.identity.infrastructure.models.department_model import DepartmentModel


class DepartmentMapper:
    """Cầu nối giữa bảng ``departments`` và entity ``Department``."""

    @staticmethod
    def to_domain(model: DepartmentModel) -> Department:
        return Department(
            id=model.id,
            name=model.name,
            description=model.description,
            is_active=model.is_active,
            created_at=model.created_at,
            updated_at=model.updated_at,
        )

    @staticmethod
    def to_model(entity: Department) -> DepartmentModel:
        return DepartmentModel(
            id=entity.id,
            name=entity.name,
            description=entity.description,
            is_active=entity.is_active,
            created_at=entity.created_at,
            updated_at=entity.updated_at,
        )

    @staticmethod
    def update_model(model: DepartmentModel, entity: Department) -> None:
        """Ghi thay đổi lên model đang được session theo dõi.

        Không tạo model mới: SQLAlchemy sẽ coi model mới là một bản ghi khác.
        """
        model.name = entity.name
        model.description = entity.description
        model.is_active = entity.is_active
        model.updated_at = entity.updated_at
