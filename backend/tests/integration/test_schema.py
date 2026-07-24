"""Kiểm tra schema thật trong PostgreSQL, không chỉ kiểm tra khai báo Python.

Các ràng buộc quan trọng nhất của hệ thống nằm ở tầng cơ sở dữ liệu; test này
xác nhận chúng thực sự tồn tại và thực sự có hiệu lực.
"""

from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

pytestmark = pytest.mark.integration

BAY_GIO = datetime(2026, 7, 21, 10, 0, tzinfo=UTC)


async def _them_phong_ban(session: AsyncSession, ten: str) -> str:
    ket_qua = await session.execute(
        text(
            "INSERT INTO departments (id, name, description, is_active, created_at, updated_at) "
            "VALUES (gen_random_uuid(), :ten, NULL, true, :bg, :bg) RETURNING id"
        ),
        {"ten": ten, "bg": BAY_GIO},
    )
    return str(ket_qua.scalar_one())


async def _them_user(
    session: AsyncSession,
    email: str,
    role: str,
    department_id: str | None,
    is_active: bool = True,
) -> str:
    ket_qua = await session.execute(
        text(
            "INSERT INTO users (id, email, password_hash, full_name, phone, role, "
            "department_id, is_active, must_change_password, last_login_at, "
            "created_at, updated_at) "
            "VALUES (gen_random_uuid(), :email, 'hash', 'Ho Ten', NULL, :role, "
            ":dept, :active, true, NULL, :bg, :bg) RETURNING id"
        ),
        {
            "email": email,
            "role": role,
            "dept": department_id,
            "active": is_active,
            "bg": BAY_GIO,
        },
    )
    return str(ket_qua.scalar_one())


class TestBangTonTai:
    @pytest.mark.parametrize("ten_bang", ["departments", "users", "refresh_tokens", "audit_logs"])
    async def test_bang_da_duoc_tao(self, db_session: AsyncSession, ten_bang: str) -> None:
        ket_qua = await db_session.execute(
            text("SELECT to_regclass(:ten) IS NOT NULL"), {"ten": f"public.{ten_bang}"}
        )

        assert ket_qua.scalar_one() is True


class TestRangBuocEmail:
    async def test_email_trung_bi_tu_choi(self, db_session: AsyncSession) -> None:
        phong = await _them_phong_ban(db_session, "Phong Email 1")
        await _them_user(db_session, "trung@congty.vn", "STAFF", phong)

        with pytest.raises(IntegrityError):
            await _them_user(db_session, "trung@congty.vn", "STAFF", phong)

    async def test_email_khac_kieu_chu_van_bi_coi_la_trung(self, db_session: AsyncSession) -> None:
        """Index đặt trên lower(email) nên hoa thường không tạo ra bản ghi mới."""
        phong = await _them_phong_ban(db_session, "Phong Email 2")
        await _them_user(db_session, "hoathuong@congty.vn", "STAFF", phong)

        with pytest.raises(IntegrityError):
            await _them_user(db_session, "HoaThuong@CongTy.VN", "STAFF", phong)

    async def test_user_da_vo_hieu_hoa_van_giu_email(self, db_session: AsyncSession) -> None:
        """Email duy nhất vĩnh viễn — kể cả khi tài khoản đã bị vô hiệu hoá."""
        phong = await _them_phong_ban(db_session, "Phong Email 3")
        await _them_user(db_session, "nghiviec@congty.vn", "STAFF", phong, is_active=False)

        with pytest.raises(IntegrityError):
            await _them_user(db_session, "nghiviec@congty.vn", "STAFF", phong)


class TestRangBuocMotManagerMoiPhong:
    async def test_hai_manager_dang_hoat_dong_cung_phong_bi_tu_choi(
        self, db_session: AsyncSession
    ) -> None:
        """Đây là ràng buộc quan trọng nhất — chỉ cơ sở dữ liệu mới chặn được
        khi hai request xảy ra đồng thời."""
        phong = await _them_phong_ban(db_session, "Phong Manager 1")
        await _them_user(db_session, "m1@congty.vn", "MANAGER", phong)

        with pytest.raises(IntegrityError):
            await _them_user(db_session, "m2@congty.vn", "MANAGER", phong)

    async def test_manager_da_vo_hieu_hoa_khong_chiem_cho(self, db_session: AsyncSession) -> None:
        phong = await _them_phong_ban(db_session, "Phong Manager 2")
        await _them_user(db_session, "cu@congty.vn", "MANAGER", phong, is_active=False)

        ma_moi = await _them_user(db_session, "moi@congty.vn", "MANAGER", phong)

        assert ma_moi is not None

    async def test_nhieu_staff_cung_phong_van_duoc(self, db_session: AsyncSession) -> None:
        phong = await _them_phong_ban(db_session, "Phong Staff")
        await _them_user(db_session, "s1@congty.vn", "STAFF", phong)

        ma = await _them_user(db_session, "s2@congty.vn", "STAFF", phong)

        assert ma is not None

    async def test_hai_manager_o_hai_phong_khac_nhau_van_duoc(
        self, db_session: AsyncSession
    ) -> None:
        phong_a = await _them_phong_ban(db_session, "Phong A")
        phong_b = await _them_phong_ban(db_session, "Phong B")
        await _them_user(db_session, "ma@congty.vn", "MANAGER", phong_a)

        ma = await _them_user(db_session, "mb@congty.vn", "MANAGER", phong_b)

        assert ma is not None


class TestRangBuocVaiTro:
    async def test_vai_tro_khong_hop_le_bi_tu_choi(self, db_session: AsyncSession) -> None:
        phong = await _them_phong_ban(db_session, "Phong Vai Tro")

        with pytest.raises(IntegrityError):
            await _them_user(db_session, "sai@congty.vn", "SUPERUSER", phong)

    async def test_admin_luu_duoc_voi_phong_ban_rong(self, db_session: AsyncSession) -> None:
        ma = await _them_user(db_session, "admin@congty.vn", "ADMIN", None)

        assert ma is not None


class TestRangBuocTenPhongBan:
    async def test_ten_phong_ban_trung_bi_tu_choi(self, db_session: AsyncSession) -> None:
        await _them_phong_ban(db_session, "Trung Ten")

        with pytest.raises(IntegrityError):
            await _them_phong_ban(db_session, "Trung Ten")


class TestKieuDuLieuThoiGian:
    @pytest.mark.parametrize(
        ("ten_bang", "ten_cot"),
        [
            ("users", "created_at"),
            ("users", "last_login_at"),
            ("departments", "created_at"),
            ("refresh_tokens", "expires_at"),
            ("audit_logs", "created_at"),
        ],
    )
    async def test_cot_thoi_gian_co_kem_mui_gio(
        self, db_session: AsyncSession, ten_bang: str, ten_cot: str
    ) -> None:
        ket_qua = await db_session.execute(
            text(
                "SELECT data_type FROM information_schema.columns "
                "WHERE table_name = :bang AND column_name = :cot"
            ),
            {"bang": ten_bang, "cot": ten_cot},
        )

        assert ket_qua.scalar_one() == "timestamp with time zone"


class TestXoaTheoQuanHe:
    async def test_xoa_user_thi_refresh_token_cung_bi_xoa(self, db_session: AsyncSession) -> None:
        phong = await _them_phong_ban(db_session, "Phong Cascade")
        user_id = await _them_user(db_session, "cascade@congty.vn", "STAFF", phong)
        await db_session.execute(
            text(
                "INSERT INTO refresh_tokens (id, user_id, token_hash, expires_at, "
                "revoked_at, replaced_by_id, user_agent, ip_address, created_at) "
                "VALUES (gen_random_uuid(), :uid, 'h', :het_han, NULL, NULL, NULL, NULL, :bg)"
            ),
            {"uid": user_id, "het_han": BAY_GIO + timedelta(days=7), "bg": BAY_GIO},
        )

        await db_session.execute(text("DELETE FROM users WHERE id = :uid"), {"uid": user_id})

        con_lai = await db_session.execute(
            text("SELECT count(*) FROM refresh_tokens WHERE user_id = :uid"),
            {"uid": user_id},
        )
        assert con_lai.scalar_one() == 0

    async def test_xoa_user_khong_lam_mat_nhat_ky(self, db_session: AsyncSession) -> None:
        """Nhật ký phải sống sót — đó là mục đích tồn tại của nó."""
        phong = await _them_phong_ban(db_session, "Phong Audit")
        user_id = await _them_user(db_session, "audit@congty.vn", "STAFF", phong)
        # ``actor_id`` là cột uuid còn ``resource_id`` là cột varchar. Dùng cùng
        # một tham số cho cả hai khiến psycopg3 không suy được kiểu và ném
        # AmbiguousParameter, nên phải tách thành ``:uid`` và ``:rid`` riêng.
        await db_session.execute(
            text(
                "INSERT INTO audit_logs (id, actor_id, action, resource_type, "
                "resource_id, changes, ip_address, user_agent, created_at) "
                "VALUES (gen_random_uuid(), :uid, 'user.created', 'user', :rid, "
                "NULL, NULL, NULL, :bg)"
            ),
            {"uid": user_id, "rid": str(user_id), "bg": BAY_GIO},
        )

        await db_session.execute(text("DELETE FROM users WHERE id = :uid"), {"uid": user_id})

        con_lai = await db_session.execute(
            text("SELECT actor_id FROM audit_logs WHERE resource_id = :rid"),
            {"rid": str(user_id)},
        )
        assert con_lai.scalar_one() is None
