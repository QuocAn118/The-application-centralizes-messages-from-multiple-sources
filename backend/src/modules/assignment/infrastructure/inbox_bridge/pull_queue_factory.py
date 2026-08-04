"""Builder ráp các use case của assignment từ ba cầu nối hạ tầng.

Thuộc ``assignment.infrastructure`` nên được phép biết cả inbox (assigner, queue)
lẫn hrm/identity (agent pool). Presentation và composition root gọi các builder
này qua factory ở ``app.state`` để không phải import trực tiếp các implementation —
giữ contract ``assignment.presentation`` ⊥ inbox/hrm/identity.

Dùng chung cho:
- endpoint ``POST /departments/{id}/auto-assign`` (Manager/Admin kéo thủ công),
- hook ``post_close`` (nhân viên đóng việc → kéo việc kế) — ``PullDepartmentQueue``,
- hook ``post_ingest`` (#2 phân phòng → #3 tự gán) — ``AutoAssignConversation``.
"""

from sqlalchemy.ext.asyncio import AsyncSession

from src.modules.assignment.application.use_cases.auto_assign_conversation import (
    AutoAssignConversation,
)
from src.modules.assignment.application.use_cases.pull_department_queue import (
    PullDepartmentQueue,
)
from src.modules.assignment.infrastructure.agent_pool.hrm_identity_pool import (
    HrmIdentityAgentPool,
)
from src.modules.assignment.infrastructure.inbox_bridge.conversation_assigner import (
    InboxConversationAssigner,
)
from src.modules.assignment.infrastructure.inbox_bridge.waiting_queue import (
    InboxWaitingQueue,
)
from src.modules.assignment.infrastructure.persistence.assignment_log_repository import (
    SqlAlchemyAssignmentLog,
)
from src.modules.inbox.domain.ports import IRealtimeNotifier
from src.shared.application.ports import IClock


def build_pull_department_queue(
    session: AsyncSession,
    *,
    notifier: IRealtimeNotifier,
    clock: IClock,
    timezone: str,
) -> PullDepartmentQueue:
    """Dựng ``PullDepartmentQueue`` với pool (#4+#1), hàng đợi (#1) và assigner (#1).

    ``timezone`` phải là ``settings.app_timezone`` để pool so "đang trong ca" theo
    giờ nghiệp vụ địa phương (nợ F1 review GĐ3). ``notifier`` dùng chung singleton
    realtime của inbox để đổi trạng thái phát tín hiệu đúng.
    """
    return PullDepartmentQueue(
        agent_pool=HrmIdentityAgentPool(session, clock, timezone),
        waiting_queue=InboxWaitingQueue(session),
        assigner=InboxConversationAssigner(
            session, notifier, clock, SqlAlchemyAssignmentLog(session)
        ),
    )


def build_auto_assign_conversation(
    session: AsyncSession,
    *,
    notifier: IRealtimeNotifier,
    clock: IClock,
    timezone: str,
) -> AutoAssignConversation:
    """Dựng ``AutoAssignConversation`` với pool (#4+#1) và assigner (#1).

    Dùng cho hook ``post_ingest`` của #3 (tin mới → #2 phân phòng → #3 tự gán một
    nhân viên). Cùng ràng buộc ``timezone`` như ``build_pull_department_queue``.
    """
    return AutoAssignConversation(
        agent_pool=HrmIdentityAgentPool(session, clock, timezone),
        assigner=InboxConversationAssigner(
            session, notifier, clock, SqlAlchemyAssignmentLog(session)
        ),
    )
