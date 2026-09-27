"""BE-5: ca biên phân quyền của ghi chú theo phòng (phần HTTP ở tests/e2e)."""

from datetime import UTC, datetime
from uuid import UUID

import pytest

from src.modules.inbox.application.actor import ActorRole, InboxActor
from src.modules.inbox.application.use_cases.customer_notes import CustomerNotes
from src.modules.inbox.domain.entities.conversation import Conversation
from src.modules.inbox.domain.entities.customer_note import CustomerNote
from src.shared.application.exceptions import PermissionDeniedError
from src.shared.domain.identifiers import new_id
from tests.unit.inbox.fakes import FakeClock, FakeConversationRepository, FakeWorkforceDirectory

BAY_GIO = datetime(2026, 9, 27, 10, 0, tzinfo=UTC)


class _Notes:
    def __init__(self) -> None:
        self.ds: list[CustomerNote] = []

    async def add(self, note: CustomerNote) -> None:
        self.ds.append(note)

    async def get_by_id(self, note_id: UUID) -> CustomerNote | None:
        return next((n for n in self.ds if n.id == note_id), None)

    async def list_for_customer(
        self, customer_id: UUID, *, tat_ca_phong: bool, department_id: UUID | None
    ) -> list[CustomerNote]:
        return [
            n
            for n in self.ds
            if n.customer_id == customer_id and (tat_ca_phong or n.department_id == department_id)
        ]

    async def delete(self, note_id: UUID) -> None:
        self.ds = [n for n in self.ds if n.id != note_id]


async def test_manager_khong_phong_khong_thay_ghi_chu_admin() -> None:
    """Manager chưa có phòng vẫn thấy hội thoại CHỜ PHÂN — nhưng ``department_id=None``
    của họ không được khớp ghi chú Admin (cũng ``None``)."""
    khach = new_id()
    repo = FakeConversationRepository()
    await repo.add(
        Conversation.start(channel_id=new_id(), customer_id=khach, department_id=None, now=BAY_GIO)
    )
    notes = _Notes()
    await notes.add(CustomerNote.viet(khach, None, new_id(), "bi mat cua admin", BAY_GIO))
    uc = CustomerNotes(notes, repo, FakeWorkforceDirectory(), FakeClock(BAY_GIO))
    manager = InboxActor(user_id=new_id(), role=ActorRole.MANAGER, department_id=None)

    assert await uc.xem(manager, khach) == []
    with pytest.raises(PermissionDeniedError):
        await uc.viet(manager, khach, "x")
