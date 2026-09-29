"""HT-2 trên PostgreSQL thật: "Nhận việc" / tự giao KHÔNG ghi đè một lần giao tay chen giữa.

Tái hiện đúng thứ tự xen kẽ: use case ĐỌC hội thoại (lúc chưa ai phụ trách) → Manager
giao cho B qua đường ``/assign-user`` thật (``ChangeAssignee``) → use case mới GHI.
Trước khi sửa, lần ghi cuối đè B (B đã được báo "bạn vừa được giao" mà không còn việc).
"""

from uuid import UUID

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from src.modules.inbox.application.actor import ActorRole, InboxActor
from src.modules.inbox.application.use_cases.assign_conversation_to_agent import (
    AssignConversationToAgent,
)
from src.modules.inbox.application.use_cases.change_assignee import ChangeAssignee
from src.modules.inbox.application.use_cases.take_conversation import TakeConversation
from src.modules.inbox.domain.entities.conversation import AlreadyAssignedError, Conversation
from src.modules.inbox.domain.entities.conversation_event import ConversationEventKind
from src.modules.inbox.domain.ports import AgentInfo
from src.modules.inbox.infrastructure.repositories.conversation_event_repository import (
    SqlAlchemyConversationEventRepository,
)
from src.modules.inbox.infrastructure.repositories.conversation_repository import (
    SqlAlchemyConversationRepository,
)
from src.shared.domain.identifiers import new_id
from tests.integration.test_inbox_nguoi_phu_trach import T0, _hoi_thoai
from tests.unit.inbox.fakes import FakeClock, FakeRealtimeNotifier, FakeWorkforceDirectory

pytestmark = pytest.mark.integration


class _RepoQuanLyChenGiua(SqlAlchemyConversationRepository):
    """Lần ``get_by_id`` ĐẦU trả bản đọc lúc chưa ai phụ trách, rồi để Manager giao
    cho B commit xen vào TRƯỚC khi use case đang chạy kịp ghi."""

    def __init__(self, session: AsyncSession, chen_giua) -> None:  # type: ignore[no-untyped-def]
        super().__init__(session)
        self._chen_giua = chen_giua

    async def get_by_id(self, conversation_id: UUID) -> Conversation | None:
        ban_doc = await super().get_by_id(conversation_id)
        if self._chen_giua is not None:
            chen, self._chen_giua = self._chen_giua, None
            await chen()
        return ban_doc


async def _dung(s: AsyncSession) -> tuple[Conversation, UUID, FakeWorkforceDirectory, object]:
    cv = await _hoi_thoai(s)
    b = new_id()
    thu_muc = FakeWorkforceDirectory(
        [AgentInfo(user_id=b, department_id=cv.department_id, role="STAFF", is_active=True)]
    )
    quan_ly = InboxActor(user_id=new_id(), role=ActorRole.MANAGER, department_id=cv.department_id)

    async def quan_ly_giao_cho_b() -> None:
        await ChangeAssignee(
            SqlAlchemyConversationRepository(s),
            SqlAlchemyConversationEventRepository(s),
            thu_muc,
            FakeRealtimeNotifier(),
            FakeClock(T0),
        ).execute(quan_ly, cv.id, b)
        await s.flush()

    return cv, b, thu_muc, quan_ly_giao_cho_b


async def _nguoi_phu_trach(s: AsyncSession, cv_id: UUID) -> UUID | None:
    await s.flush()
    s.expire_all()
    cv = await SqlAlchemyConversationRepository(s).get_by_id(cv_id)
    assert cv is not None
    return cv.assigned_user_id


class TestNhanViecKhongDeGiaoTay:
    async def test_manager_giao_chen_giua_thi_nhan_viec_bi_tu_choi(
        self, db_session: AsyncSession
    ) -> None:
        cv, b, _, chen = await _dung(db_session)
        nhan_vien_a = InboxActor(user_id=new_id(), role=ActorRole.STAFF, department_id=cv.department_id)
        su_kien = SqlAlchemyConversationEventRepository(db_session)
        uc = TakeConversation(
            _RepoQuanLyChenGiua(db_session, chen), FakeRealtimeNotifier(), FakeClock(T0), su_kien
        )

        with pytest.raises(AlreadyAssignedError):
            await uc.execute(nhan_vien_a, cv.id)

        assert await _nguoi_phu_trach(db_session, cv.id) == b
        # Không có dòng "A đã nhận việc" giả trong timeline.
        loai = [e.kind for e in await su_kien.list_for_conversation(cv.id)]
        assert loai == [ConversationEventKind.ASSIGNED]


class TestTuGiaoKhongDeGiaoTay:
    async def test_manager_giao_chen_giua_thi_tu_giao_bi_tu_choi(
        self, db_session: AsyncSession
    ) -> None:
        cv, b, thu_muc, chen = await _dung(db_session)
        c = new_id()
        thu_muc._agents[c] = AgentInfo(
            user_id=c, department_id=cv.department_id, role="STAFF", is_active=True
        )
        he_thong = InboxActor(user_id=new_id(), role=ActorRole.ADMIN, department_id=None)
        su_kien = SqlAlchemyConversationEventRepository(db_session)
        uc = AssignConversationToAgent(
            _RepoQuanLyChenGiua(db_session, chen),
            thu_muc,
            FakeRealtimeNotifier(),
            FakeClock(T0),
            su_kien,
        )

        # #3 bắt đúng lỗi này thành ALREADY_TAKEN (rời hàng đợi, không ghi assignment_log).
        with pytest.raises(AlreadyAssignedError):
            await uc.execute(he_thong, cv.id, c)

        assert await _nguoi_phu_trach(db_session, cv.id) == b
        loai = [e.kind for e in await su_kien.list_for_conversation(cv.id)]
        assert loai == [ConversationEventKind.ASSIGNED]


class TestKhongTranhChapVanNhanDuoc:
    async def test_nhan_viec_binh_thuong(self, db_session: AsyncSession) -> None:
        cv = await _hoi_thoai(db_session)
        a = InboxActor(user_id=new_id(), role=ActorRole.STAFF, department_id=cv.department_id)
        uc = TakeConversation(
            SqlAlchemyConversationRepository(db_session), FakeRealtimeNotifier(), FakeClock(T0)
        )

        await uc.execute(a, cv.id)

        assert await _nguoi_phu_trach(db_session, cv.id) == a.user_id
