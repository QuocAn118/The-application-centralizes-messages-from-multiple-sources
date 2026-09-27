"""Notifier theo request: giữ tín hiệu lại, CHỈ phát sau khi session commit.

Use case gọi ``notify_*`` giữa transaction; nếu phát ngay, client nhận tín hiệu rồi
gọi REST trước khi commit → đọc dữ liệu CŨ và ghi đè lên dữ liệu mới trong cache
(lộ ra ở 2a: gỡ người phụ trách xong ô chọn vẫn hiện người cũ). Rollback thì bỏ
hết — thao tác hỏng không được báo cho ai.
"""

import asyncio
import logging
from collections.abc import Awaitable, Callable
from uuid import UUID

from sqlalchemy import event
from sqlalchemy.ext.asyncio import AsyncSession

from src.modules.inbox.domain.ports import IRealtimeNotifier

logger = logging.getLogger(__name__)


class NotifierSauCommit:
    def __init__(self, goc: IRealtimeNotifier, session: AsyncSession) -> None:
        self._goc = goc
        self._cho: list[Callable[[], Awaitable[None]]] = []
        self._tac_vu: set[asyncio.Task[None]] = set()
        event.listen(session.sync_session, "after_commit", self._sau_commit)
        event.listen(session.sync_session, "after_rollback", self._sau_rollback)

    async def notify_conversation_changed(
        self, conversation_id: UUID, department_id: UUID | None, change: str
    ) -> None:
        self._cho.append(
            lambda: self._goc.notify_conversation_changed(conversation_id, department_id, change)
        )

    async def notify_user(self, user_id: UUID, conversation_id: UUID, change: str) -> None:
        self._cho.append(lambda: self._goc.notify_user(user_id, conversation_id, change))

    def _sau_commit(self, _session: object) -> None:
        # Sự kiện SQLAlchemy là hàm đồng bộ — đẩy việc gửi sang event loop.
        cho, self._cho = self._cho, []
        if cho:
            tac_vu = asyncio.get_running_loop().create_task(self._phat(cho))
            self._tac_vu.add(tac_vu)  # giữ tham chiếu để task không bị GC giữa chừng
            tac_vu.add_done_callback(self._tac_vu.discard)

    def _sau_rollback(self, _session: object) -> None:
        self._cho = []

    async def _phat(self, cho: list[Callable[[], Awaitable[None]]]) -> None:
        for gui in cho:
            try:
                await gui()
            except Exception:
                logger.exception("Phát tín hiệu realtime sau commit lỗi — bỏ qua")
