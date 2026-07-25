"""Quy tắc phân quyền dùng chung cho các use case inbox.

Gom về một chỗ để mọi use case áp cùng một luật: Admin thấy tất cả; Manager và
Staff chỉ chạm hội thoại thuộc phòng mình; mục chờ-phân (chưa có phòng) chỉ
Manager/Admin thấy.
"""

from src.modules.inbox.application.actor import ActorRole, InboxActor
from src.modules.inbox.domain.entities.conversation import Conversation
from src.shared.application.exceptions import PermissionDeniedError


def _tu_choi() -> PermissionDeniedError:
    # Không tiết lộ hội thoại thuộc phòng nào — chỉ báo không có quyền.
    return PermissionDeniedError(
        "Bạn không có quyền thao tác trên hội thoại này.",
        code="CONVERSATION_FORBIDDEN",
    )


def co_the_thao_tac(actor: InboxActor, conversation: Conversation) -> bool:
    """Người gọi có được đọc/thao tác trên hội thoại này không."""
    if actor.role is ActorRole.ADMIN:
        return True
    if conversation.department_id is None:
        # Hội thoại chờ-phân: chỉ Manager (và Admin ở trên) mới với tới.
        return actor.role is ActorRole.MANAGER
    return conversation.department_id == actor.department_id


def bao_dam_thao_tac(actor: InboxActor, conversation: Conversation) -> None:
    """Ném ``PermissionDeniedError`` nếu người gọi không được phép."""
    if not co_the_thao_tac(actor, conversation):
        raise _tu_choi()


def bao_dam_admin(actor: InboxActor) -> None:
    """Chỉ Admin mới được quản lý kênh (kết nối, đổi credential, ngắt...)."""
    if actor.role is not ActorRole.ADMIN:
        raise PermissionDeniedError(
            "Chỉ quản trị viên được quản lý kênh.", code="CHANNEL_ADMIN_REQUIRED"
        )
