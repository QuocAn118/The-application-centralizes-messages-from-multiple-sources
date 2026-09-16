"""Integration test cho hai cầu nối của hrm sang module khác:

- IdentityWorkforceDirectory: đọc nhân viên/Manager từ identity.
- InboxPerformanceSource: tính KPI thực đạt từ hội thoại inbox.

Cả hai là chỗ DUY NHẤT hrm chạm identity/inbox; test seed dữ liệu thật của hai
module đó rồi xác nhận hrm đọc/tính đúng.
"""

from datetime import UTC, datetime
from decimal import Decimal

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from src.modules.hrm.domain.value_objects.kpi import KpiMetricType, KpiPeriod
from src.modules.hrm.infrastructure.directory.workforce_directory import (
    IdentityWorkforceDirectory,
)
from src.modules.hrm.infrastructure.performance.inbox_performance_source import (
    InboxPerformanceSource,
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
from src.shared.domain.identifiers import new_id

pytestmark = pytest.mark.integration

BAY_GIO = datetime(2026, 8, 1, 9, 0, tzinfo=UTC)
KY = KpiPeriod(year=2026, month=8)
_HASH = PasswordHash("$2b$12$" + "a" * 53)


async def _phong(session: AsyncSession, ten: str) -> Department:
    repo = SqlAlchemyDepartmentRepository(session)
    p = Department.create(name=ten, description=None, now=BAY_GIO)
    await repo.add(p)
    await session.flush()
    return p


async def _nhan_vien(session: AsyncSession, department_id, role: Role = Role.STAFF) -> User:
    repo = SqlAlchemyUserRepository(session)
    u = User.create(
        email=Email(f"{new_id().hex}@x.vn"),
        password_hash=_HASH,
        full_name="NV",
        role=role,
        department_id=department_id,
        now=BAY_GIO,
    )
    await repo.add(u)
    await session.flush()
    return u


class TestWorkforceDirectory:
    async def test_get_manager_of_department(self, db_session: AsyncSession) -> None:
        directory = IdentityWorkforceDirectory(db_session)
        phong = await _phong(db_session, "KD")
        manager = await _nhan_vien(db_session, phong.id, role=Role.MANAGER)
        await _nhan_vien(db_session, phong.id, role=Role.STAFF)

        found = await directory.get_manager_of_department(phong.id)

        assert found is not None
        assert found.user_id == manager.id
        assert found.role == "MANAGER"

    async def test_phong_khong_co_manager_tra_none(self, db_session: AsyncSession) -> None:
        directory = IdentityWorkforceDirectory(db_session)
        phong = await _phong(db_session, "Chua co manager")
        await _nhan_vien(db_session, phong.id, role=Role.STAFF)

        assert await directory.get_manager_of_department(phong.id) is None


async def _hoi_thoai_dong(
    session: AsyncSession,
    department_id,
    assigned_user_id,
    updated_at: datetime,
    status: str = "DA_DONG",
    closed_at: datetime | None = None,
    created_at: datetime = BAY_GIO,
):
    """Chèn thẳng một hội thoại inbox ở trạng thái cho trước để tính KPI.

    ``closed_at`` None → cột NULL (mô phỏng dòng cũ, KPI dùng fallback updated_at).
    Trả ``conversation_id`` để test thêm tin (tính AVG_RESPONSE_MINUTES).
    """
    # Cần channel + customer vì conversations có FK. Tạo tối thiểu.
    ch = await session.execute(
        text(
            "INSERT INTO channels (id, platform, external_channel_id, name, credential, "
            "department_id, is_active, created_at, updated_at) VALUES "
            "(gen_random_uuid(), 'ZALO', :ext, 'OA', 'enc::x', :dept, true, :bg, :bg) RETURNING id"
        ),
        {"ext": f"oa_{new_id().hex}", "dept": str(department_id), "bg": BAY_GIO},
    )
    channel_id = ch.scalar_one()
    cu = await session.execute(
        text(
            "INSERT INTO customers (id, channel_id, platform, external_id, display_name, "
            "avatar_url, created_at, updated_at) VALUES "
            "(gen_random_uuid(), :ch, 'ZALO', :ext, 'K', NULL, :bg, :bg) RETURNING id"
        ),
        {"ch": channel_id, "ext": f"c_{new_id().hex}", "bg": BAY_GIO},
    )
    customer_id = cu.scalar_one()
    conv = await session.execute(
        text(
            "INSERT INTO conversations (id, channel_id, customer_id, status, department_id, "
            "assigned_user_id, last_message_at, created_at, updated_at, closed_at) VALUES "
            "(gen_random_uuid(), :ch, :cu, :st, :dept, :asg, :bg, :cre, :upd, :cl) RETURNING id"
        ),
        {
            "ch": channel_id,
            "cu": customer_id,
            "st": status,
            "dept": str(department_id),
            "asg": str(assigned_user_id) if assigned_user_id else None,
            "bg": BAY_GIO,
            "cre": created_at,
            "upd": updated_at,
            "cl": closed_at,
        },
    )
    return conv.scalar_one()


async def _tin(
    session: AsyncSession,
    conversation_id,
    direction: str,
    created_at: datetime,
    sender_user_id=None,
) -> None:
    await session.execute(
        text(
            "INSERT INTO messages (id, conversation_id, direction, text, external_message_id, "
            "sender_user_id, created_at) VALUES "
            "(gen_random_uuid(), :cid, :dir, 'hi', NULL, :snd, :cre)"
        ),
        {
            "cid": conversation_id,
            "dir": direction,
            "snd": str(sender_user_id) if sender_user_id else None,
            "cre": created_at,
        },
    )


class TestInboxPerformanceSource:
    async def test_dem_hoi_thoai_dong_cho_nhan_vien(self, db_session: AsyncSession) -> None:
        source = InboxPerformanceSource(db_session)
        phong, nv = new_id(), new_id()
        # 2 hội thoại đóng trong kỳ (tháng 8), gán cho nv.
        await _hoi_thoai_dong(db_session, phong, nv, datetime(2026, 8, 10, tzinfo=UTC))
        await _hoi_thoai_dong(db_session, phong, nv, datetime(2026, 8, 20, tzinfo=UTC))
        # 1 hội thoại đóng ngoài kỳ (tháng 7) — không tính.
        await _hoi_thoai_dong(db_session, phong, nv, datetime(2026, 7, 30, tzinfo=UTC))
        # 1 hội thoại chưa đóng — không tính.
        await _hoi_thoai_dong(
            db_session, phong, nv, datetime(2026, 8, 15, tzinfo=UTC), status="DANG_MO"
        )
        await db_session.flush()

        so = await source.get_metric_for_user(nv, KpiMetricType.CONVERSATIONS_CLOSED, KY)

        assert so == Decimal("2")

    async def test_dem_theo_phong(self, db_session: AsyncSession) -> None:
        source = InboxPerformanceSource(db_session)
        phong_a, phong_b = new_id(), new_id()
        await _hoi_thoai_dong(db_session, phong_a, new_id(), datetime(2026, 8, 10, tzinfo=UTC))
        await _hoi_thoai_dong(db_session, phong_b, new_id(), datetime(2026, 8, 10, tzinfo=UTC))
        await db_session.flush()

        so = await source.get_metric_for_department(phong_a, KpiMetricType.CONVERSATIONS_CLOSED, KY)

        assert so == Decimal("1")

    async def test_bien_ky_la_nua_khoang(self, db_session: AsyncSession) -> None:
        # Đóng đúng 00:00:00 ngày 1 tháng sau KHÔNG thuộc kỳ tháng 8 (biên phải mở).
        source = InboxPerformanceSource(db_session)
        phong, nv = new_id(), new_id()
        await _hoi_thoai_dong(db_session, phong, nv, datetime(2026, 9, 1, 0, 0, tzinfo=UTC))
        # Cuối kỳ hợp lệ: 31/08 23:59 vẫn được đếm.
        await _hoi_thoai_dong(db_session, phong, nv, datetime(2026, 8, 31, 23, 59, tzinfo=UTC))
        await db_session.flush()

        so = await source.get_metric_for_user(nv, KpiMetricType.CONVERSATIONS_CLOSED, KY)

        assert so == Decimal("1")

    async def test_ky_thang_12_khong_tran_nam(self, db_session: AsyncSession) -> None:
        # Kỳ tháng 12/2026: biên phải là 01/01/2027, không lỗi tràn tháng.
        source = InboxPerformanceSource(db_session)
        phong, nv = new_id(), new_id()
        ky_12 = KpiPeriod(year=2026, month=12)
        await _hoi_thoai_dong(db_session, phong, nv, datetime(2026, 12, 15, tzinfo=UTC))
        await _hoi_thoai_dong(db_session, phong, nv, datetime(2027, 1, 1, 0, 0, tzinfo=UTC))
        await db_session.flush()

        so = await source.get_metric_for_user(nv, KpiMetricType.CONVERSATIONS_CLOSED, ky_12)

        assert so == Decimal("1")

    async def test_closed_at_uu_tien_hon_updated_at(self, db_session: AsyncSession) -> None:
        # closed_at ở tháng 8 (trong kỳ) nhưng updated_at ở tháng 9 (đã bị cập nhật
        # sau khi đóng). Đếm phải theo closed_at → thuộc kỳ tháng 8.
        source = InboxPerformanceSource(db_session)
        phong, nv = new_id(), new_id()
        await _hoi_thoai_dong(
            db_session,
            phong,
            nv,
            updated_at=datetime(2026, 9, 5, tzinfo=UTC),
            closed_at=datetime(2026, 8, 20, tzinfo=UTC),
        )
        await db_session.flush()

        so = await source.get_metric_for_user(nv, KpiMetricType.CONVERSATIONS_CLOSED, KY)
        assert so == Decimal("1")  # theo closed_at (tháng 8), không phải updated_at

    async def test_avg_response_khong_co_mau_tra_none(self, db_session: AsyncSession) -> None:
        source = InboxPerformanceSource(db_session)

        so = await source.get_metric_for_user(new_id(), KpiMetricType.AVG_RESPONSE_MINUTES, KY)

        assert so is None  # chưa có hội thoại/tin nào

    async def test_avg_response_tinh_phut_trung_binh(self, db_session: AsyncSession) -> None:
        # NV phản hồi 2 hội thoại: 5 phút và 15 phút → trung bình 10.0 phút.
        source = InboxPerformanceSource(db_session)
        phong, nv = new_id(), new_id()
        c1 = await _hoi_thoai_dong(
            db_session, phong, nv, updated_at=datetime(2026, 8, 10, tzinfo=UTC)
        )
        await _tin(db_session, c1, "INBOUND", datetime(2026, 8, 10, 10, 0, tzinfo=UTC))
        await _tin(db_session, c1, "OUTBOUND", datetime(2026, 8, 10, 10, 5, tzinfo=UTC), nv)
        c2 = await _hoi_thoai_dong(
            db_session, phong, nv, updated_at=datetime(2026, 8, 11, tzinfo=UTC)
        )
        await _tin(db_session, c2, "INBOUND", datetime(2026, 8, 11, 9, 0, tzinfo=UTC))
        await _tin(db_session, c2, "OUTBOUND", datetime(2026, 8, 11, 9, 15, tzinfo=UTC), nv)
        await db_session.flush()

        so = await source.get_metric_for_user(nv, KpiMetricType.AVG_RESPONSE_MINUTES, KY)
        assert so == Decimal("10.0")

    async def test_avg_response_gan_dung_nguoi_phan_hoi(self, db_session: AsyncSession) -> None:
        # Tin OUTBOUND đầu do NV khác gửi → quy cho người đó, không phải assigned.
        source = InboxPerformanceSource(db_session)
        phong, nv_gan, nv_tra = new_id(), new_id(), new_id()
        c1 = await _hoi_thoai_dong(
            db_session, phong, nv_gan, updated_at=datetime(2026, 8, 10, tzinfo=UTC)
        )
        await _tin(db_session, c1, "INBOUND", datetime(2026, 8, 10, 10, 0, tzinfo=UTC))
        await _tin(db_session, c1, "OUTBOUND", datetime(2026, 8, 10, 10, 5, tzinfo=UTC), nv_tra)
        await db_session.flush()

        assert await source.get_metric_for_user(
            nv_tra, KpiMetricType.AVG_RESPONSE_MINUTES, KY
        ) == Decimal("5.0")
        # Người được gán nhưng KHÔNG gửi tin đầu → không có mẫu.
        assert (
            await source.get_metric_for_user(nv_gan, KpiMetricType.AVG_RESPONSE_MINUTES, KY) is None
        )


class TestGetMetricsForUsers:
    """Bản gom lô chạy trên Postgres thật — nợ N4.

    Test unit dùng fake nên không kiểm được SQL; ``GROUP BY`` sai (gom nhầm
    người, mất người không có dữ liệu, trung bình tính trên sai tập) chỉ lộ ra ở
    đây. Mỗi test đối chiếu thẳng với bản một-người: hai bản lệch nhau là lỗi
    im lặng, vì UI chỉ gọi bản lô.
    """

    async def test_dem_khop_ban_mot_nguoi_va_bu_0(self, db_session: AsyncSession) -> None:
        source = InboxPerformanceSource(db_session)
        phong, nv1, nv2, nv3 = new_id(), new_id(), new_id(), new_id()
        # nv1: 2 hội thoại đóng; nv2: 1; nv3: không có gì.
        for _ in range(2):
            await _hoi_thoai_dong(
                db_session, phong, nv1, updated_at=datetime(2026, 8, 10, tzinfo=UTC)
            )
        await _hoi_thoai_dong(db_session, phong, nv2, updated_at=datetime(2026, 8, 11, tzinfo=UTC))
        await db_session.flush()

        lo = await source.get_metrics_for_users(
            [nv1, nv2, nv3], KpiMetricType.CONVERSATIONS_CLOSED, KY
        )

        assert lo[nv1] == Decimal(2)
        assert lo[nv2] == Decimal(1)
        # Người không có dòng nào KHÔNG biến mất, và là 0 chứ không phải None:
        # "đã đếm, bằng không". Đây là ngữ nghĩa màn KPI dựa vào.
        assert lo[nv3] == Decimal(0)
        assert lo[nv3] is not None

        for nv in (nv1, nv2, nv3):
            mot = await source.get_metric_for_user(nv, KpiMetricType.CONVERSATIONS_CLOSED, KY)
            assert lo[nv] == mot, f"lô lệch bản một-người cho {nv}"

    async def test_avg_khop_ban_mot_nguoi_va_thieu_khoa_la_none(
        self, db_session: AsyncSession
    ) -> None:
        source = InboxPerformanceSource(db_session)
        phong, nv1, nv2, nv3 = new_id(), new_id(), new_id(), new_id()
        # nv1: 5 phút và 15 phút -> 10.0
        c1 = await _hoi_thoai_dong(
            db_session, phong, nv1, updated_at=datetime(2026, 8, 10, tzinfo=UTC)
        )
        await _tin(db_session, c1, "INBOUND", datetime(2026, 8, 10, 10, 0, tzinfo=UTC))
        await _tin(db_session, c1, "OUTBOUND", datetime(2026, 8, 10, 10, 5, tzinfo=UTC), nv1)
        c2 = await _hoi_thoai_dong(
            db_session, phong, nv1, updated_at=datetime(2026, 8, 11, tzinfo=UTC)
        )
        await _tin(db_session, c2, "INBOUND", datetime(2026, 8, 11, 9, 0, tzinfo=UTC))
        await _tin(db_session, c2, "OUTBOUND", datetime(2026, 8, 11, 9, 15, tzinfo=UTC), nv1)
        # nv2: 4 phút
        c3 = await _hoi_thoai_dong(
            db_session, phong, nv2, updated_at=datetime(2026, 8, 12, tzinfo=UTC)
        )
        await _tin(db_session, c3, "INBOUND", datetime(2026, 8, 12, 8, 0, tzinfo=UTC))
        await _tin(db_session, c3, "OUTBOUND", datetime(2026, 8, 12, 8, 4, tzinfo=UTC), nv2)
        await db_session.flush()

        lo = await source.get_metrics_for_users(
            [nv1, nv2, nv3], KpiMetricType.AVG_RESPONSE_MINUTES, KY
        )

        # Trung bình của TỪNG người, không phải trung bình chung của cả nhóm
        # (nếu GROUP BY sai thì cả hai ra cùng một số).
        assert lo[nv1] == Decimal("10.0")
        assert lo[nv2] == Decimal("4.0")
        # nv3 không có mẫu -> None, KHÁC 0 (chỉ số trung bình không tính được).
        assert lo.get(nv3) is None

        for nv in (nv1, nv2, nv3):
            mot = await source.get_metric_for_user(nv, KpiMetricType.AVG_RESPONSE_MINUTES, KY)
            assert lo.get(nv) == mot, f"lô lệch bản một-người cho {nv}"

    async def test_khong_lan_sang_nguoi_ngoai_danh_sach(self, db_session: AsyncSession) -> None:
        # Hỏi nv1 thì không được dính dữ liệu của nv2 (lọc IN phải đúng).
        source = InboxPerformanceSource(db_session)
        phong, nv1, nv2 = new_id(), new_id(), new_id()
        await _hoi_thoai_dong(db_session, phong, nv2, updated_at=datetime(2026, 8, 10, tzinfo=UTC))
        await db_session.flush()

        lo = await source.get_metrics_for_users([nv1], KpiMetricType.CONVERSATIONS_CLOSED, KY)

        assert set(lo) == {nv1}
        assert lo[nv1] == Decimal(0)

    async def test_danh_sach_rong_khong_goi_db(self, db_session: AsyncSession) -> None:
        source = InboxPerformanceSource(db_session)
        assert await source.get_metrics_for_users([], KpiMetricType.CONVERSATIONS_CLOSED, KY) == {}


class TestGetMetricsForDepartments:
    """Bản gom lô CẤP PHÒNG trên Postgres thật.

    Khác bản nhân viên ở chiều gom: KPI phòng tính trên **mọi hội thoại của
    phòng**, bất kể ai trả lời — còn KPI nhân viên quy cho người gửi tin
    OUTBOUND đầu. Gom nhầm chiều thì số vẫn ra, chỉ là sai.
    """

    async def test_dem_khop_ban_mot_phong_va_bu_0(self, db_session: AsyncSession) -> None:
        source = InboxPerformanceSource(db_session)
        phong1, phong2, phong3 = new_id(), new_id(), new_id()
        for _ in range(3):
            await _hoi_thoai_dong(
                db_session, phong1, new_id(), updated_at=datetime(2026, 8, 10, tzinfo=UTC)
            )
        await _hoi_thoai_dong(
            db_session, phong2, new_id(), updated_at=datetime(2026, 8, 11, tzinfo=UTC)
        )
        await db_session.flush()

        lo = await source.get_metrics_for_departments(
            [phong1, phong2, phong3], KpiMetricType.CONVERSATIONS_CLOSED, KY
        )

        assert lo[phong1] == Decimal(3)
        assert lo[phong2] == Decimal(1)
        assert lo[phong3] == Decimal(0)  # phòng trống: đã đếm, bằng không

        for p in (phong1, phong2, phong3):
            mot = await source.get_metric_for_department(p, KpiMetricType.CONVERSATIONS_CLOSED, KY)
            assert lo[p] == mot, f"lô lệch bản một-phòng cho {p}"

    async def test_avg_gom_theo_phong_khong_theo_nguoi_tra_loi(
        self, db_session: AsyncSession
    ) -> None:
        # Hai hội thoại CÙNG phòng do HAI người khác nhau trả lời (4 và 6 phút).
        # KPI phòng phải là trung bình của cả hai = 5.0, không tách theo người.
        source = InboxPerformanceSource(db_session)
        phong, nv1, nv2 = new_id(), new_id(), new_id()
        c1 = await _hoi_thoai_dong(
            db_session, phong, nv1, updated_at=datetime(2026, 8, 10, tzinfo=UTC)
        )
        await _tin(db_session, c1, "INBOUND", datetime(2026, 8, 10, 10, 0, tzinfo=UTC))
        await _tin(db_session, c1, "OUTBOUND", datetime(2026, 8, 10, 10, 4, tzinfo=UTC), nv1)
        c2 = await _hoi_thoai_dong(
            db_session, phong, nv2, updated_at=datetime(2026, 8, 11, tzinfo=UTC)
        )
        await _tin(db_session, c2, "INBOUND", datetime(2026, 8, 11, 9, 0, tzinfo=UTC))
        await _tin(db_session, c2, "OUTBOUND", datetime(2026, 8, 11, 9, 6, tzinfo=UTC), nv2)
        await db_session.flush()

        lo = await source.get_metrics_for_departments(
            [phong], KpiMetricType.AVG_RESPONSE_MINUTES, KY
        )

        assert lo[phong] == Decimal("5.0")
        mot = await source.get_metric_for_department(phong, KpiMetricType.AVG_RESPONSE_MINUTES, KY)
        assert lo[phong] == mot

    async def test_avg_tung_phong_rieng_biet(self, db_session: AsyncSession) -> None:
        # Nếu GROUP BY sai thì hai phòng ra cùng một số.
        source = InboxPerformanceSource(db_session)
        phong1, phong2, phong_trong = new_id(), new_id(), new_id()
        c1 = await _hoi_thoai_dong(
            db_session, phong1, new_id(), updated_at=datetime(2026, 8, 10, tzinfo=UTC)
        )
        await _tin(db_session, c1, "INBOUND", datetime(2026, 8, 10, 10, 0, tzinfo=UTC))
        await _tin(db_session, c1, "OUTBOUND", datetime(2026, 8, 10, 10, 2, tzinfo=UTC), new_id())
        c2 = await _hoi_thoai_dong(
            db_session, phong2, new_id(), updated_at=datetime(2026, 8, 11, tzinfo=UTC)
        )
        await _tin(db_session, c2, "INBOUND", datetime(2026, 8, 11, 9, 0, tzinfo=UTC))
        await _tin(db_session, c2, "OUTBOUND", datetime(2026, 8, 11, 9, 20, tzinfo=UTC), new_id())
        await db_session.flush()

        lo = await source.get_metrics_for_departments(
            [phong1, phong2, phong_trong], KpiMetricType.AVG_RESPONSE_MINUTES, KY
        )

        assert lo[phong1] == Decimal("2.0")
        assert lo[phong2] == Decimal("20.0")
        # Phòng không có mẫu -> vắng khoá -> None (KHÁC 0).
        assert lo.get(phong_trong) is None

    async def test_danh_sach_rong(self, db_session: AsyncSession) -> None:
        source = InboxPerformanceSource(db_session)
        assert (
            await source.get_metrics_for_departments([], KpiMetricType.CONVERSATIONS_CLOSED, KY)
            == {}
        )
