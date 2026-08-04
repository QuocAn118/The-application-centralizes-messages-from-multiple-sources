"""Integration test cho hạ tầng #5 trên PostgreSQL thật.

Kiểm chỗ fake in-memory không kiểm được:
- ``SqlAlchemyRollupRepository``: UPSERT cộng-delta (ON CONFLICT NULLS NOT
  DISTINCT), ghi-đè-ngày, đọc theo khoảng + lọc phòng.
- ``InboxStatsSource``: backfill event-time (bucket theo giờ địa phương từng bản
  ghi), first_response từ tin đầu, closed/resolution theo updated_at.
- ``HrmStatsSource``: đọc thẳng #4 (ca + đơn), gộp đúng.
"""

from datetime import UTC, date, datetime, time
from uuid import UUID

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from src.modules.analytics.domain.value_objects.metrics import (
    DailyAgentMetric,
    DailyConversationMetric,
    DateRange,
)
from src.modules.analytics.infrastructure.repositories.rollup_repository import (
    SqlAlchemyRollupRepository,
)
from src.modules.analytics.infrastructure.sources.hrm_stats_source import HrmStatsSource
from src.modules.analytics.infrastructure.sources.inbox_stats_source import InboxStatsSource
from src.modules.hrm.infrastructure.models.request_model import RequestModel
from src.modules.hrm.infrastructure.models.shift_assignment_model import (
    ShiftAssignmentModel,
)
from src.modules.hrm.infrastructure.models.shift_model import ShiftModel
from src.modules.inbox.infrastructure.models.channel_model import ChannelModel
from src.modules.inbox.infrastructure.models.conversation_model import ConversationModel
from src.modules.inbox.infrastructure.models.customer_model import CustomerModel
from src.modules.inbox.infrastructure.models.message_model import MessageModel
from src.shared.domain.identifiers import new_id

pytestmark = pytest.mark.integration


@pytest.fixture
def session(db_session: AsyncSession) -> AsyncSession:
    """Bí danh cho ``db_session`` (rollback mỗi test) để helper dùng tên ``session``."""
    return db_session


TZ = "Asia/Ho_Chi_Minh"
D1 = UUID("00000000-0000-0000-0000-0000000000d1")
D2 = UUID("00000000-0000-0000-0000-0000000000d2")
U1 = UUID("00000000-0000-0000-0000-0000000000a1")
U2 = UUID("00000000-0000-0000-0000-0000000000a2")


# ----- SqlAlchemyRollupRepository -----


class TestRollupRepository:
    async def test_bump_cong_don_qua_nhieu_lan(self, session: AsyncSession) -> None:
        repo = SqlAlchemyRollupRepository(session)
        for _ in range(3):
            await repo.bump_conversation(
                DailyConversationMetric(
                    work_date=date(2026, 7, 1),
                    department_id=D1,
                    channel_platform="ZALO",
                    inbound_count=2,
                )
            )
        await session.flush()
        rows = await repo.doc_conversation(DateRange(date(2026, 7, 1), date(2026, 7, 1)), None)
        assert len(rows) == 1
        assert rows[0].inbound_count == 6  # 2*3 cộng dồn qua ON CONFLICT

    async def test_bump_department_none_gop_dung_nulls_not_distinct(
        self, session: AsyncSession
    ) -> None:
        repo = SqlAlchemyRollupRepository(session)
        for _ in range(2):
            await repo.bump_conversation(
                DailyConversationMetric(
                    work_date=date(2026, 7, 1),
                    department_id=None,  # chưa phân phòng
                    channel_platform="ZALO",
                    inbound_count=1,
                )
            )
        await session.flush()
        rows = await repo.doc_conversation(DateRange(date(2026, 7, 1), date(2026, 7, 1)), None)
        # NULLS NOT DISTINCT: hai lần department NULL gộp một dòng, không tách.
        assert len(rows) == 1
        assert rows[0].inbound_count == 2

    async def test_ghi_de_ngay_thay_the_khong_cong_don(self, session: AsyncSession) -> None:
        repo = SqlAlchemyRollupRepository(session)
        ngay = date(2026, 7, 1)
        await repo.bump_conversation(
            DailyConversationMetric(
                work_date=ngay, department_id=D1, channel_platform="ZALO", inbound_count=99
            )
        )
        await session.flush()
        await repo.ghi_de_conversation_ngay(
            ngay,
            (
                DailyConversationMetric(
                    work_date=ngay, department_id=D1, channel_platform="ZALO", inbound_count=5
                ),
            ),
        )
        await session.flush()
        rows = await repo.doc_conversation(DateRange(ngay, ngay), None)
        assert [r.inbound_count for r in rows] == [5]  # ghi đè, không phải 104

    async def test_doc_loc_phong(self, session: AsyncSession) -> None:
        repo = SqlAlchemyRollupRepository(session)
        ngay = date(2026, 7, 1)
        for dept in (D1, D2):
            await repo.bump_agent(
                DailyAgentMetric(work_date=ngay, user_id=U1, department_id=dept, handled_count=1)
            )
        await session.flush()
        chi_d1 = await repo.doc_agent(DateRange(ngay, ngay), (D1,))
        assert {r.department_id for r in chi_d1} == {D1}


# ----- InboxStatsSource (backfill event-time) -----


async def _channel(session: AsyncSession, platform: str, dept: UUID | None) -> UUID:
    cid = new_id()
    session.add(
        ChannelModel(
            id=cid,
            platform=platform,
            external_channel_id=f"ext_{cid.hex}",
            name="OA",
            credential="x",
            department_id=dept,
            is_active=True,
        )
    )
    await session.flush()
    return cid


async def _customer(session: AsyncSession, channel_id: UUID) -> UUID:
    cid = new_id()
    session.add(
        CustomerModel(
            id=cid,
            channel_id=channel_id,
            platform="ZALO",
            external_id=f"kh_{cid.hex}",
            display_name="Khach",
        )
    )
    await session.flush()
    return cid


async def _conversation(
    session: AsyncSession,
    channel_id: UUID,
    customer_id: UUID,
    *,
    dept: UUID | None,
    status: str,
    assigned: UUID | None,
    created_at: datetime,
    updated_at: datetime,
) -> UUID:
    cid = new_id()
    session.add(
        ConversationModel(
            id=cid,
            channel_id=channel_id,
            customer_id=customer_id,
            status=status,
            department_id=dept,
            assigned_user_id=assigned,
            last_message_at=updated_at,
            created_at=created_at,
            updated_at=updated_at,
        )
    )
    await session.flush()
    return cid


async def _message(
    session: AsyncSession,
    conversation_id: UUID,
    direction: str,
    created_at: datetime,
    sender: UUID | None = None,
) -> None:
    session.add(
        MessageModel(
            id=new_id(),
            conversation_id=conversation_id,
            direction=direction,
            text="hi",
            external_message_id=None,
            sender_user_id=sender,
            created_at=created_at,
        )
    )


class TestInboxStatsSource:
    async def test_inbound_outbound_theo_ngay_dia_phuong(self, session: AsyncSession) -> None:
        ch = await _channel(session, "ZALO", D1)
        kh = await _customer(session, ch)
        conv = await _conversation(
            session,
            ch,
            kh,
            dept=D1,
            status="DANG_MO",
            assigned=U1,
            created_at=datetime(2026, 7, 1, 3, 0, tzinfo=UTC),
            updated_at=datetime(2026, 7, 1, 3, 0, tzinfo=UTC),
        )
        # 03:00 UTC = 10:00 giờ VN ngày 1 → thuộc ngày 1 local.
        await _message(session, conv, "INBOUND", datetime(2026, 7, 1, 3, 0, tzinfo=UTC))
        await _message(session, conv, "OUTBOUND", datetime(2026, 7, 1, 4, 0, tzinfo=UTC), sender=U1)
        await session.flush()

        rows = await InboxStatsSource(session, TZ).conversation_metrics_cho_ngay(date(2026, 7, 1))
        d1 = [r for r in rows if r.department_id == D1 and r.channel_platform == "ZALO"]
        assert len(d1) == 1
        assert d1[0].inbound_count == 1
        assert d1[0].outbound_count == 1

    async def test_tin_qua_nua_dem_gan_dung_ngay_su_kien(self, session: AsyncSession) -> None:
        # 18:00 UTC ngày 1 = 01:00 VN ngày 2 → tin thuộc NGÀY 2 local (event-time).
        ch = await _channel(session, "ZALO", D1)
        kh = await _customer(session, ch)
        conv = await _conversation(
            session,
            ch,
            kh,
            dept=D1,
            status="DANG_MO",
            assigned=U1,
            created_at=datetime(2026, 7, 1, 18, 0, tzinfo=UTC),
            updated_at=datetime(2026, 7, 1, 18, 0, tzinfo=UTC),
        )
        await _message(session, conv, "INBOUND", datetime(2026, 7, 1, 18, 0, tzinfo=UTC))
        await session.flush()

        ngay1 = await InboxStatsSource(session, TZ).conversation_metrics_cho_ngay(date(2026, 7, 1))
        ngay2 = await InboxStatsSource(session, TZ).conversation_metrics_cho_ngay(date(2026, 7, 2))
        assert sum(r.inbound_count for r in ngay1) == 0  # không thuộc ngày 1
        assert sum(r.inbound_count for r in ngay2) == 1  # thuộc ngày 2

    async def test_first_response_va_closed(self, session: AsyncSession) -> None:
        ch = await _channel(session, "ZALO", D1)
        kh = await _customer(session, ch)
        # Khách nhắn 10:00 VN, nhân viên trả lời 10:05 VN → first_response 300s.
        conv = await _conversation(
            session,
            ch,
            kh,
            dept=D1,
            status="DA_DONG",
            assigned=U1,
            created_at=datetime(2026, 7, 1, 3, 0, tzinfo=UTC),
            updated_at=datetime(2026, 7, 1, 5, 0, tzinfo=UTC),  # đóng 12:00 VN
        )
        await _message(session, conv, "INBOUND", datetime(2026, 7, 1, 3, 0, tzinfo=UTC))
        await _message(session, conv, "OUTBOUND", datetime(2026, 7, 1, 3, 5, tzinfo=UTC), sender=U1)
        await session.flush()

        agents = await InboxStatsSource(session, TZ).agent_metrics_cho_ngay(date(2026, 7, 1))
        u1 = [a for a in agents if a.user_id == U1]
        assert len(u1) == 1
        assert u1[0].first_response_samples == 1
        assert u1[0].sum_first_response_seconds == 300
        assert u1[0].handled_count == 1  # đóng trong ngày
        assert u1[0].resolution_samples == 1
        assert u1[0].department_id == D1


# ----- HrmStatsSource (đọc thẳng #4) -----


async def _shift_assignment(
    session: AsyncSession, user_id: UUID, dept: UUID, work_date: date, start: time, end: time
) -> None:
    shift_id = new_id()
    session.add(
        ShiftModel(
            id=shift_id,
            department_id=dept,
            name="Ca",
            start_time=start,
            end_time=end,
            is_active=True,
        )
    )
    await session.flush()
    session.add(
        ShiftAssignmentModel(
            id=new_id(),
            shift_id=shift_id,
            user_id=user_id,
            department_id=dept,
            work_date=work_date,
            start_time=start,
            end_time=end,
            status="ACTIVE",
        )
    )


class TestHrmStatsSource:
    async def test_workforce_dem_ca_va_gio_cong(self, session: AsyncSession) -> None:
        await _shift_assignment(session, U1, D1, date(2026, 7, 1), time(8, 0), time(12, 0))
        await _shift_assignment(session, U1, D1, date(2026, 7, 2), time(8, 0), time(12, 0))
        await session.flush()
        rows = await HrmStatsSource(session).workforce_rows(
            DateRange(date(2026, 7, 1), date(2026, 7, 31)), (D1,)
        )
        u1 = [r for r in rows if r.user_id == U1]
        assert len(u1) == 1
        assert u1[0].shift_count == 2
        assert u1[0].worked_seconds == 2 * 4 * 3600  # 2 ca x 4 giờ
        assert u1[0].kpi_percent is None  # nợ

    async def test_request_gop_theo_loai_trang_thai(self, session: AsyncSession) -> None:
        # 1 đơn đã duyệt (tính thời gian), 1 đơn chờ (không tính mẫu).
        session.add(
            RequestModel(
                id=new_id(),
                requester_id=U1,
                department_id=D1,
                request_type="NGHI_PHEP",
                reason="x",
                status="DA_DUYET",
                created_at=datetime(2026, 7, 1, 0, 0, tzinfo=UTC),
                decided_at=datetime(2026, 7, 1, 1, 0, tzinfo=UTC),  # 3600s
            )
        )
        session.add(
            RequestModel(
                id=new_id(),
                requester_id=U2,
                department_id=D1,
                request_type="NGHI_PHEP",
                reason="y",
                status="CHO_DUYET",
                created_at=datetime(2026, 7, 1, 0, 0, tzinfo=UTC),
                decided_at=None,
            )
        )
        await session.flush()
        rows = await HrmStatsSource(session).request_rows(
            DateRange(date(2026, 7, 1), date(2026, 7, 31)), (D1,)
        )
        duyet = [r for r in rows if r.status == "DA_DUYET"]
        cho = [r for r in rows if r.status == "CHO_DUYET"]
        assert duyet[0].count == 1
        assert duyet[0].sum_decision_seconds == 3600
        assert duyet[0].decided_samples == 1
        assert cho[0].decided_samples == 0
