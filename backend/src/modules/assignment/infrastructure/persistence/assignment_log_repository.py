"""Implementation ``IAssignmentLog`` — ghi một dòng lịch sử gán vào Postgres.

Ghi log KHÔNG được làm hỏng luồng gán: khi tới đây inbox đã chấp nhận gán rồi
(cùng session, cùng giao dịch của request auto-assign). Chèn dòng và để giao dịch
của lời gọi commit; lỗi ghi được lời gọi (router bọc try/except như các hook khác)
xử lý — không nuốt ở đây để mypy/giao dịch rõ ràng.
"""

from sqlalchemy.ext.asyncio import AsyncSession

from src.modules.assignment.domain.ports import IAssignmentLog
from src.modules.assignment.domain.value_objects.candidate import AssignmentEvent
from src.modules.assignment.infrastructure.persistence.assignment_log_model import (
    AssignmentLogModel,
)
from src.shared.domain.identifiers import new_id


class SqlAlchemyAssignmentLog(IAssignmentLog):
    """Ghi ``assignment_log`` qua SQLAlchemy async."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def ghi(self, su_kien: AssignmentEvent) -> None:
        self._session.add(
            AssignmentLogModel(
                id=new_id(),
                conversation_id=su_kien.conversation_id,
                user_id=su_kien.user_id,
                department_id=su_kien.department_id,
                assigned_at=su_kien.assigned_at,
            )
        )
