"""WebSocket notifier — implementation ``IRealtimeNotifier`` (spec §6).

Chỉ đẩy **tín hiệu** ``{conversation_id, change, department_id}``, không gửi nội
dung tin — client tự gọi REST để lấy. Lọc theo phạm vi quyền: Staff/Manager chỉ
nhận tín hiệu của phòng mình (và chờ-phân với Manager); Admin nhận tất cả.
"""

import asyncio
from dataclasses import dataclass
from uuid import UUID

from starlette.websockets import WebSocket

from src.modules.inbox.application.actor import ActorRole, InboxActor


@dataclass
class _KetNoi:
    """Một client đang lắng nghe, kèm phạm vi quyền của họ."""

    websocket: WebSocket
    role: ActorRole
    department_id: UUID | None
    # BE-2: để gửi tín hiệu riêng cho đúng người (được giao / bị gỡ).
    user_id: UUID | None = None

    def duoc_nhan(self, conversation_department_id: UUID | None) -> bool:
        """Client này có được nhận tín hiệu của một hội thoại không."""
        if self.role is ActorRole.ADMIN:
            return True
        if conversation_department_id is None:
            # Hội thoại chờ-phân: chỉ Manager thấy.
            return self.role is ActorRole.MANAGER
        return conversation_department_id == self.department_id


class WebSocketNotifier:
    """Quản lý kết nối WebSocket và phát tín hiệu thay đổi theo phạm vi quyền."""

    def __init__(self) -> None:
        self._connections: list[_KetNoi] = []
        self._lock = asyncio.Lock()

    async def connect(self, websocket: WebSocket, actor: InboxActor) -> _KetNoi:
        await websocket.accept()
        ket_noi = _KetNoi(
            websocket=websocket,
            role=actor.role,
            department_id=actor.department_id,
            user_id=actor.user_id,
        )
        async with self._lock:
            self._connections.append(ket_noi)
        return ket_noi

    async def disconnect(self, ket_noi: _KetNoi) -> None:
        async with self._lock:
            if ket_noi in self._connections:
                self._connections.remove(ket_noi)

    async def notify_conversation_changed(
        self, conversation_id: UUID, department_id: UUID | None, change: str
    ) -> None:
        tin_hieu: dict[str, str | None] = {
            "conversation_id": str(conversation_id),
            "change": change,
            "department_id": str(department_id) if department_id else None,
        }
        async with self._lock:
            nguoi_nhan = [c for c in self._connections if c.duoc_nhan(department_id)]
        await self._gui(nguoi_nhan, tin_hieu)

    async def notify_user(self, user_id: UUID, conversation_id: UUID, change: str) -> None:
        """Tín hiệu riêng cho mọi kết nối (mọi tab) của đúng MỘT người."""
        tin_hieu: dict[str, str | None] = {
            "conversation_id": str(conversation_id),
            "change": change,
        }
        async with self._lock:
            nguoi_nhan = [c for c in self._connections if c.user_id == user_id]
        await self._gui(nguoi_nhan, tin_hieu)

    async def _gui(self, nguoi_nhan: list[_KetNoi], tin_hieu: dict[str, str | None]) -> None:
        """Gửi tới từng kết nối; kết nối rớt thì gỡ khỏi danh sách."""
        # Gửi ngoài lock để không giữ lock khi chờ mạng; client rớt thì bỏ.
        chet: list[_KetNoi] = []
        for c in nguoi_nhan:
            try:
                await c.websocket.send_json(tin_hieu)
            except Exception:
                chet.append(c)
        if chet:
            async with self._lock:
                for c in chet:
                    if c in self._connections:
                        self._connections.remove(c)
