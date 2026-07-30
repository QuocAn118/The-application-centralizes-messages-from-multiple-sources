"""Integration test cho các cầu nối #3 trên PostgreSQL thật.

Xác nhận AgentPool gom đúng (ca #4 + tải #1), assigner gán qua use case #1, và
waiting queue sắp đúng thứ tự chờ — chỗ fake in-memory không kiểm được.
"""

from datetime import UTC, date, datetime, time, timedelta
from uuid import UUID

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from src.modules.assignment.infrastructure.agent_pool.hrm_identity_pool import (
    HrmIdentityAgentPool,
)
from src.modules.assignment.infrastructure.inbox_bridge.conversation_assigner import (
    InboxConversationAssigner,
)
from src.modules.assignment.infrastructure.inbox_bridge.waiting_queue import (
    InboxWaitingQueue,
)
from src.modules.hrm.domain.entities.shift import Shift
from src.modules.hrm.domain.entities.shift_assignment import ShiftAssignment
from src.modules.hrm.infrastructure.repositories.shift_assignment_repository import (
    SqlAlchemyShiftAssignmentRepository,
)
from src.modules.hrm.infrastructure.repositories.shift_repository import (
    SqlAlchemyShiftRepository,
)
from src.modules.identity.domain.entities.department import Department
from src.modules.identity.domain.entities.user import User
from src.modules.identity.domain.value_objects.email import Email
from src.modules.identity.domain.value_objects.password_hash import PasswordHash
from src.modules.identity.domain.value_objects.role import Role
from src.modules.identity.infrastructure.repositories.department_repository import (
    SqlAlchemyDepartmentRepository,
)
from src.modules.identity.infrastructure.repositories.user_repository import (
    SqlAlchemyUserRepository,
)
from src.modules.inbox.domain.entities.channel import Channel
from src.modules.inbox.domain.entities.conversation import Conversation, ConversationStatus
from src.modules.inbox.domain.entities.customer import Customer
from src.modules.inbox.domain.value_objects.platform import Platform
from src.modules.inbox.infrastructure.repositories.channel_repository import (
    SqlAlchemyChannelRepository,
)
from src.modules.inbox.infrastructure.repositories.conversation_repository import (
    SqlAlchemyConversationRepository,
)
from src.modules.inbox.infrastructure.repositories.customer_repository import (
    SqlAlchemyCustomerRepository,
)
from src.shared.domain.identifiers import new_id

pytestmark = pytest.mark.integration

# Đồng hồ cố định: 10:00 một ngày, để ca 08:00-12:00 cùng ngày là "đang trong ca".
NOW = datetime(2026, 8, 3, 10, 0, tzinfo=UTC)
HOM_NAY = NOW.date()


class _Clock:
    def __init__(self, moment: datetime = NOW) -> None:
        self._moment = moment

    def now(self) -> datetime:
        return self._moment


async def _phong(session: AsyncSession) -> Department:
    dept = Department.create(name=f"Phong {new_id()}", description=None, now=NOW)
    await SqlAlchemyDepartmentRepository(session).add(dept)
    await session.flush()
    return dept


async def _nhan_vien(session: AsyncSession, department_id: UUID, role: Role = Role.STAFF) -> User:
    u = User.create(
        email=Email(f"u_{new_id().hex}@x.vn"),
        password_hash=PasswordHash("$2b$12$" + "a" * 53),
        full_name="NV",
        role=role,
        department_id=department_id,
        now=NOW,
    )
    await SqlAlchemyUserRepository(session).add(u)
    await session.flush()
    return u


async def _ca(
    session: AsyncSession,
    user_id: UUID,
    department_id: UUID,
    work_date: date,
    start: time,
    end: time,
) -> None:
    # Buổi phân ca có khoá ngoại tới ``shifts`` -> phải seed một mẫu ca thật.
    shift = Shift.create(
        department_id=department_id, name="Ca", start_time=start, end_time=end, now=NOW
    )
    await SqlAlchemyShiftRepository(session).add(shift)
    await session.flush()
    sa = ShiftAssignment.assign(
        shift_id=shift.id,
        user_id=user_id,
        department_id=department_id,
        work_date=work_date,
        start_time=start,
        end_time=end,
        now=NOW,
    )
    await SqlAlchemyShiftAssignmentRepository(session).add(sa)
    await session.flush()


async def _hoi_thoai(
    session: AsyncSession,
    department_id: UUID,
    *,
    assigned_user_id: UUID | None,
    status: ConversationStatus,
    last_message_at: datetime,
) -> Conversation:
    ch = Channel.connect(
        platform=Platform.ZALO,
        external_channel_id=f"oa_{new_id()}",
        name="OA",
        department_id=department_id,
        encrypted_credential="e",
        now=NOW,
    )
    await SqlAlchemyChannelRepository(session).add(ch)
    await session.flush()
    cu = Customer.register(
        channel_id=ch.id,
        platform=Platform.ZALO,
        external_id=f"c_{new_id()}",
        display_name="K",
        now=NOW,
    )
    await SqlAlchemyCustomerRepository(session).add(cu)
    await session.flush()
    conv = Conversation.start(
        channel_id=ch.id, customer_id=cu.id, department_id=department_id, now=NOW
    )
    conv.status = status
    conv.assigned_user_id = assigned_user_id
    conv.last_message_at = last_message_at
    await SqlAlchemyConversationRepository(session).add(conv)
    await session.flush()
    return conv


class TestAgentPool:
    async def test_gom_on_shift_va_tai(self, db_session: AsyncSession) -> None:
        phong = await _phong(db_session)
        khac = await _phong(db_session)
        trong_ca = await _nhan_vien(db_session, phong.id)
        ngoai_ca = await _nhan_vien(db_session, phong.id)
        nguoi_phong_khac = await _nhan_vien(db_session, khac.id)

        # trong_ca có ca bao 10:00; ngoai_ca có ca sáng sớm đã qua.
        await _ca(db_session, trong_ca.id, phong.id, HOM_NAY, time(8, 0), time(12, 0))
        await _ca(db_session, ngoai_ca.id, phong.id, HOM_NAY, time(6, 0), time(9, 0))
        # người phòng khác không nên xuất hiện.
        await _ca(db_session, nguoi_phong_khac.id, khac.id, HOM_NAY, time(8, 0), time(12, 0))

        # trong_ca đang giữ 2 hội thoại DANG_MO.
        for _ in range(2):
            await _hoi_thoai(
                db_session,
                phong.id,
                assigned_user_id=trong_ca.id,
                status=ConversationStatus.DANG_MO,
                last_message_at=NOW,
            )

        # timezone="UTC" để giờ địa phương == NOW (10:00) rơi vào ca 08:00-12:00.
        pool = HrmIdentityAgentPool(db_session, _Clock(), timezone="UTC")
        cands = {c.user_id: c for c in await pool.candidates_for_department(phong.id)}

        assert set(cands) == {trong_ca.id, ngoai_ca.id}  # chỉ nhân viên phòng này
        assert cands[trong_ca.id].on_shift is True
        assert cands[trong_ca.id].open_load == 2
        assert cands[ngoai_ca.id].on_shift is False
        assert cands[ngoai_ca.id].open_load == 0
        assert cands[trong_ca.id].kpi_percent is None  # nợ KPI

    async def test_on_shift_quy_doi_ve_gio_dia_phuong(self, db_session: AsyncSession) -> None:
        # Regression F1: giờ ca lưu theo giờ VN. now() = 03:00 UTC ~ 10:00 VN, phải
        # rơi vào ca 08:00-12:00. Nếu so thẳng UTC (03:00) sẽ SAI (coi ngoài ca).
        phong = await _phong(db_session)
        nv = await _nhan_vien(db_session, phong.id)
        await _ca(db_session, nv.id, phong.id, date(2026, 8, 3), time(8, 0), time(12, 0))

        utc_3h = datetime(2026, 8, 3, 3, 0, tzinfo=UTC)
        pool = HrmIdentityAgentPool(db_session, _Clock(utc_3h), timezone="Asia/Ho_Chi_Minh")
        cands = {c.user_id: c for c in await pool.candidates_for_department(phong.id)}

        assert cands[nv.id].on_shift is True


class TestWaitingQueue:
    async def test_hang_doi_cho_lau_nhat_truoc(self, db_session: AsyncSession) -> None:
        phong = await _phong(db_session)
        cu = await _hoi_thoai(
            db_session,
            phong.id,
            assigned_user_id=None,
            status=ConversationStatus.DANG_MO,
            last_message_at=NOW - timedelta(hours=2),
        )
        moi = await _hoi_thoai(
            db_session,
            phong.id,
            assigned_user_id=None,
            status=ConversationStatus.DANG_MO,
            last_message_at=NOW,
        )
        # đã gán -> không nằm trong hàng đợi.
        await _hoi_thoai(
            db_session,
            phong.id,
            assigned_user_id=new_id(),
            status=ConversationStatus.DANG_MO,
            last_message_at=NOW - timedelta(hours=1),
        )

        queue = InboxWaitingQueue(db_session)
        ds = await queue.waiting_conversations(phong.id)

        assert list(ds) == [cu.id, moi.id]  # chờ lâu nhất trước


class TestAssigner:
    async def test_gan_duoc_qua_use_case_1(self, db_session: AsyncSession) -> None:
        from tests.unit.inbox.fakes import FakeRealtimeNotifier

        phong = await _phong(db_session)
        nv = await _nhan_vien(db_session, phong.id)
        conv = await _hoi_thoai(
            db_session,
            phong.id,
            assigned_user_id=None,
            status=ConversationStatus.DANG_MO,
            last_message_at=NOW,
        )

        assigner = InboxConversationAssigner(db_session, FakeRealtimeNotifier(), _Clock())
        ok = await assigner.assign_to_agent(conv.id, nv.id)
        await db_session.flush()

        assert ok is True
        moi = await SqlAlchemyConversationRepository(db_session).get_by_id(conv.id)
        assert moi is not None
        assert moi.assigned_user_id == nv.id

    async def test_gan_that_bai_khi_da_co_nguoi(self, db_session: AsyncSession) -> None:
        from tests.unit.inbox.fakes import FakeRealtimeNotifier

        phong = await _phong(db_session)
        nv = await _nhan_vien(db_session, phong.id)
        conv = await _hoi_thoai(
            db_session,
            phong.id,
            assigned_user_id=new_id(),
            status=ConversationStatus.DANG_MO,
            last_message_at=NOW,
        )
        assigner = InboxConversationAssigner(db_session, FakeRealtimeNotifier(), _Clock())
        ok = await assigner.assign_to_agent(conv.id, nv.id)
        assert ok is False  # #1 khước từ (đã có người), nuốt lỗi
