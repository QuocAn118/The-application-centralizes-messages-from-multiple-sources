from datetime import UTC, datetime

import pytest

from src.modules.identity.application.use_cases.change_password import (
    ChangePassword,
    InvalidCurrentPasswordError,
    WeakPasswordError,
)
from src.modules.identity.application.use_cases.login_user import (
    InactiveAccountError,
    InvalidCredentialsError,
    LoginUser,
)
from src.modules.identity.application.use_cases.logout_user import LogoutUser
from src.modules.identity.application.use_cases.refresh_access_token import (
    InvalidRefreshTokenError,
    RefreshAccessToken,
)
from src.modules.identity.domain.entities.audit_log import AuditAction
from src.modules.identity.domain.entities.user import User
from src.modules.identity.domain.value_objects.email import Email
from src.modules.identity.domain.value_objects.password_hash import PasswordHash
from src.modules.identity.domain.value_objects.role import Role
from src.modules.identity.infrastructure.security.password_hasher import (
    BcryptPasswordHasher,
)
from src.modules.identity.infrastructure.security.token_service import JwtTokenService
from src.shared.domain.identifiers import new_id
from tests.unit.identity.fakes import (
    FakeAuditLogRepository,
    FakeClock,
    FakeRefreshTokenRepository,
    FakeTransaction,
    FakeUserRepository,
)

BAY_GIO = datetime(2026, 7, 21, 10, 0, tzinfo=UTC)
MAT_KHAU = "MatKhauDung123"
PHONG_A = new_id()
KHOA = "khoa-test-khong-dung-that"


class _BoiCanh:
    """Gom các thành phần dùng chung cho test luồng xác thực."""

    def __init__(self, users: list[User] | None = None) -> None:
        self.clock = FakeClock(BAY_GIO)
        self.hasher = BcryptPasswordHasher(rounds=4)
        self.token_service = JwtTokenService(KHOA, "HS256", 15, self.clock)
        self.user_repo = FakeUserRepository(users or [])
        self.token_repo = FakeRefreshTokenRepository()
        self.audit_repo = FakeAuditLogRepository()
        self.transaction = FakeTransaction()

    def dang_nhap(self) -> LoginUser:
        return LoginUser(
            user_repo=self.user_repo,
            refresh_token_repo=self.token_repo,
            audit_repo=self.audit_repo,
            hasher=self.hasher,
            token_service=self.token_service,
            clock=self.clock,
            refresh_token_expire_days=7,
        )

    def lam_moi(self) -> RefreshAccessToken:
        return RefreshAccessToken(
            user_repo=self.user_repo,
            refresh_token_repo=self.token_repo,
            audit_repo=self.audit_repo,
            token_service=self.token_service,
            clock=self.clock,
            transaction=self.transaction,
            refresh_token_expire_days=7,
        )

    def dang_xuat(self) -> LogoutUser:
        return LogoutUser(
            refresh_token_repo=self.token_repo,
            audit_repo=self.audit_repo,
            token_service=self.token_service,
            clock=self.clock,
        )

    def doi_mat_khau(self) -> ChangePassword:
        return ChangePassword(
            user_repo=self.user_repo,
            refresh_token_repo=self.token_repo,
            audit_repo=self.audit_repo,
            hasher=self.hasher,
            clock=self.clock,
        )


def _tao_user(
    bc: _BoiCanh,
    email: str = "nhanvien@congty.vn",
    role: Role = Role.STAFF,
    mat_khau: str = MAT_KHAU,
    dang_hoat_dong: bool = True,
    must_change_password: bool = False,
) -> User:
    """Tạo người dùng với mật khẩu băm thật rồi nạp vào repository.

    Dùng hasher thật thay vì giả lập vì luồng đăng nhập phụ thuộc vào việc
    ``verify`` khớp với ``hash`` — giả lập chỗ này sẽ che mất lỗi thật.
    """
    user = User.create(
        email=Email(email),
        password_hash=PasswordHash(bc.hasher.hash(mat_khau)),
        full_name="Nguyễn Văn A",
        role=role,
        department_id=PHONG_A if role.requires_department() else None,
        now=BAY_GIO,
        must_change_password=must_change_password,
    )
    if not dang_hoat_dong:
        user.deactivate(is_last_active_admin=False, now=BAY_GIO)
    bc.user_repo._users[user.id] = user
    return user


class TestDangNhap:
    async def test_dang_nhap_dung_tra_ve_cap_token(self) -> None:
        bc = _BoiCanh()
        _tao_user(bc)

        ket_qua = await bc.dang_nhap().execute("nhanvien@congty.vn", MAT_KHAU)

        assert ket_qua.tokens.access_token
        assert ket_qua.tokens.refresh_token
        assert ket_qua.tokens.expires_in == 15 * 60
        assert ket_qua.tokens.token_type == "bearer"

    async def test_email_khong_phan_biet_hoa_thuong(self) -> None:
        bc = _BoiCanh()
        _tao_user(bc)

        ket_qua = await bc.dang_nhap().execute("NhanVien@CongTy.VN", MAT_KHAU)

        assert ket_qua.tokens.access_token

    async def test_access_token_chua_dung_vai_tro_va_phong_ban(self) -> None:
        bc = _BoiCanh()
        user = _tao_user(bc, role=Role.MANAGER)

        ket_qua = await bc.dang_nhap().execute("nhanvien@congty.vn", MAT_KHAU)

        payload = bc.token_service.decode_access_token(ket_qua.tokens.access_token)
        assert payload.user_id == user.id
        assert payload.role is Role.MANAGER
        assert payload.department_id == PHONG_A

    async def test_ghi_nhan_moc_dang_nhap_gan_nhat(self) -> None:
        bc = _BoiCanh()
        user = _tao_user(bc)

        await bc.dang_nhap().execute("nhanvien@congty.vn", MAT_KHAU)

        assert user.last_login_at == BAY_GIO

    async def test_luu_refresh_token_duoi_dang_hash(self) -> None:
        bc = _BoiCanh()
        _tao_user(bc)

        ket_qua = await bc.dang_nhap().execute("nhanvien@congty.vn", MAT_KHAU)

        tho = ket_qua.tokens.refresh_token
        assert await bc.token_repo.get_by_hash(tho) is None
        assert await bc.token_repo.get_by_hash(
            bc.token_service.hash_refresh_token(tho)
        ) is not None

    async def test_bao_lai_yeu_cau_doi_mat_khau(self) -> None:
        bc = _BoiCanh()
        _tao_user(bc, must_change_password=True)

        ket_qua = await bc.dang_nhap().execute("nhanvien@congty.vn", MAT_KHAU)

        assert ket_qua.must_change_password is True

    async def test_mat_khau_sai_bi_tu_choi(self) -> None:
        bc = _BoiCanh()
        _tao_user(bc)

        with pytest.raises(InvalidCredentialsError):
            await bc.dang_nhap().execute("nhanvien@congty.vn", "MatKhauSai123")

    async def test_email_khong_ton_tai_bi_tu_choi(self) -> None:
        bc = _BoiCanh()

        with pytest.raises(InvalidCredentialsError):
            await bc.dang_nhap().execute("khongton@tai.vn", MAT_KHAU)

    async def test_sai_email_va_sai_mat_khau_cho_cung_mot_loi(self) -> None:
        """Phân biệt hai trường hợp sẽ để lộ email nào có trong hệ thống."""
        bc = _BoiCanh()
        _tao_user(bc)

        loi_sai_email = None
        loi_sai_mat_khau = None
        try:
            await bc.dang_nhap().execute("khongton@tai.vn", MAT_KHAU)
        except InvalidCredentialsError as e:
            loi_sai_email = e
        try:
            await bc.dang_nhap().execute("nhanvien@congty.vn", "SaiRoi123")
        except InvalidCredentialsError as e:
            loi_sai_mat_khau = e

        assert loi_sai_email is not None
        assert loi_sai_mat_khau is not None
        assert loi_sai_email.code == loi_sai_mat_khau.code
        assert loi_sai_email.message == loi_sai_mat_khau.message

    async def test_tai_khoan_bi_vo_hieu_hoa_khong_dang_nhap_duoc(self) -> None:
        bc = _BoiCanh()
        _tao_user(bc, dang_hoat_dong=False)

        with pytest.raises(InactiveAccountError):
            await bc.dang_nhap().execute("nhanvien@congty.vn", MAT_KHAU)

    async def test_ghi_nhat_ky_khi_dang_nhap_thanh_cong(self) -> None:
        bc = _BoiCanh()
        user = _tao_user(bc)

        await bc.dang_nhap().execute("nhanvien@congty.vn", MAT_KHAU, ip_address="10.0.0.1")

        ban_ghi = bc.audit_repo.entries[-1]
        assert ban_ghi.action is AuditAction.AUTH_LOGIN_SUCCEEDED
        assert ban_ghi.actor_id == user.id
        assert ban_ghi.ip_address == "10.0.0.1"

    async def test_ghi_nhat_ky_khi_dang_nhap_that_bai(self) -> None:
        bc = _BoiCanh()
        _tao_user(bc)

        with pytest.raises(InvalidCredentialsError):
            await bc.dang_nhap().execute("nhanvien@congty.vn", "SaiRoi123")

        ban_ghi = bc.audit_repo.entries[-1]
        assert ban_ghi.action is AuditAction.AUTH_LOGIN_FAILED

    async def test_nhat_ky_that_bai_khong_luu_mat_khau(self) -> None:
        bc = _BoiCanh()
        _tao_user(bc)

        with pytest.raises(InvalidCredentialsError):
            await bc.dang_nhap().execute("nhanvien@congty.vn", "MatKhauBiLo999")

        noi_dung = str(bc.audit_repo.entries[-1].changes)
        assert "MatKhauBiLo999" not in noi_dung

    async def test_email_sai_dinh_dang_cho_cung_mot_loi_khong_no(self) -> None:
        """Email sai cú pháp phải trả về ``InvalidCredentialsError`` như mọi
        thất bại khác, không được để ``InvalidEmailError`` lọt ra thành lỗi 500
        — và phải được ghi nhật ký thất bại như các lần thử khác."""
        bc = _BoiCanh()
        _tao_user(bc)

        with pytest.raises(InvalidCredentialsError):
            await bc.dang_nhap().execute("khong-phai-email", MAT_KHAU)

        assert bc.audit_repo.entries[-1].action is AuditAction.AUTH_LOGIN_FAILED


class TestLamMoiToken:
    async def test_lam_moi_tra_ve_cap_token_moi(self) -> None:
        bc = _BoiCanh()
        _tao_user(bc)
        dang_nhap = await bc.dang_nhap().execute("nhanvien@congty.vn", MAT_KHAU)

        moi = await bc.lam_moi().execute(dang_nhap.tokens.refresh_token)

        assert moi.refresh_token != dang_nhap.tokens.refresh_token

    async def test_token_cu_khong_dung_lai_duoc_sau_khi_lam_moi(self) -> None:
        bc = _BoiCanh()
        _tao_user(bc)
        dang_nhap = await bc.dang_nhap().execute("nhanvien@congty.vn", MAT_KHAU)
        cu = dang_nhap.tokens.refresh_token
        await bc.lam_moi().execute(cu)

        with pytest.raises(InvalidRefreshTokenError):
            await bc.lam_moi().execute(cu)

    async def test_dung_lai_token_cu_thu_hoi_ca_chuoi(self) -> None:
        """Token bị tái sử dụng nghĩa là đã lộ — mọi token trong chuỗi mất hiệu lực."""
        bc = _BoiCanh()
        _tao_user(bc)
        dang_nhap = await bc.dang_nhap().execute("nhanvien@congty.vn", MAT_KHAU)
        cu = dang_nhap.tokens.refresh_token
        moi = await bc.lam_moi().execute(cu)

        with pytest.raises(InvalidRefreshTokenError):
            await bc.lam_moi().execute(cu)

        with pytest.raises(InvalidRefreshTokenError):
            await bc.lam_moi().execute(moi.refresh_token)

    async def test_ghi_nhat_ky_khi_phat_hien_tai_su_dung(self) -> None:
        bc = _BoiCanh()
        _tao_user(bc)
        dang_nhap = await bc.dang_nhap().execute("nhanvien@congty.vn", MAT_KHAU)
        cu = dang_nhap.tokens.refresh_token
        await bc.lam_moi().execute(cu)

        with pytest.raises(InvalidRefreshTokenError):
            await bc.lam_moi().execute(cu)

        assert any(
            e.action is AuditAction.AUTH_TOKEN_REUSE_DETECTED
            for e in bc.audit_repo.entries
        )

    async def test_phat_hien_tai_su_dung_chot_giao_dich_truoc_khi_nem_loi(
        self,
    ) -> None:
        """Việc thu hồi chuỗi phải được commit dù request kết thúc bằng lỗi.

        Nếu không chốt giao dịch ở đây, lớp HTTP sẽ rollback theo lỗi và xoá
        luôn hành động thu hồi — kẻ tấn công vẫn dùng được token đã lộ.
        """
        bc = _BoiCanh()
        _tao_user(bc)
        dang_nhap = await bc.dang_nhap().execute("nhanvien@congty.vn", MAT_KHAU)
        cu = dang_nhap.tokens.refresh_token
        await bc.lam_moi().execute(cu)

        with pytest.raises(InvalidRefreshTokenError):
            await bc.lam_moi().execute(cu)

        assert bc.transaction.commit_count == 1

    async def test_token_khong_ton_tai_bi_tu_choi(self) -> None:
        bc = _BoiCanh()

        with pytest.raises(InvalidRefreshTokenError):
            await bc.lam_moi().execute("token-bia-dat")

    async def test_token_het_han_bi_tu_choi(self) -> None:
        bc = _BoiCanh()
        _tao_user(bc)
        dang_nhap = await bc.dang_nhap().execute("nhanvien@congty.vn", MAT_KHAU)

        bc.clock.advance(days=8)

        with pytest.raises(InvalidRefreshTokenError):
            await bc.lam_moi().execute(dang_nhap.tokens.refresh_token)

    async def test_user_bi_vo_hieu_hoa_thi_khong_lam_moi_duoc(self) -> None:
        bc = _BoiCanh()
        user = _tao_user(bc)
        dang_nhap = await bc.dang_nhap().execute("nhanvien@congty.vn", MAT_KHAU)

        user.deactivate(is_last_active_admin=False, now=BAY_GIO)

        with pytest.raises(InvalidRefreshTokenError):
            await bc.lam_moi().execute(dang_nhap.tokens.refresh_token)


class TestDangXuat:
    async def test_dang_xuat_thu_hoi_token_hien_tai(self) -> None:
        bc = _BoiCanh()
        user = _tao_user(bc)
        dang_nhap = await bc.dang_nhap().execute("nhanvien@congty.vn", MAT_KHAU)

        await bc.dang_xuat().execute(dang_nhap.tokens.refresh_token, requester=user)

        with pytest.raises(InvalidRefreshTokenError):
            await bc.lam_moi().execute(dang_nhap.tokens.refresh_token)

    async def test_dang_xuat_hai_lan_khong_gay_loi(self) -> None:
        bc = _BoiCanh()
        user = _tao_user(bc)
        dang_nhap = await bc.dang_nhap().execute("nhanvien@congty.vn", MAT_KHAU)

        await bc.dang_xuat().execute(dang_nhap.tokens.refresh_token, requester=user)
        await bc.dang_xuat().execute(dang_nhap.tokens.refresh_token, requester=user)

    async def test_khong_thu_hoi_duoc_token_cua_nguoi_khac(self) -> None:
        bc = _BoiCanh()
        _tao_user(bc, email="nannhan@congty.vn")
        ke_xau = _tao_user(bc, email="kexau@congty.vn")
        cua_nan_nhan = await bc.dang_nhap().execute("nannhan@congty.vn", MAT_KHAU)

        await bc.dang_xuat().execute(
            cua_nan_nhan.tokens.refresh_token, requester=ke_xau
        )

        moi = await bc.lam_moi().execute(cua_nan_nhan.tokens.refresh_token)
        assert moi.access_token


class TestDoiMatKhau:
    async def test_doi_mat_khau_thanh_cong(self) -> None:
        bc = _BoiCanh()
        user = _tao_user(bc)

        await bc.doi_mat_khau().execute(user, MAT_KHAU, "MatKhauMoi456")

        assert bc.hasher.verify("MatKhauMoi456", user.password_hash.value)

    async def test_tat_co_yeu_cau_doi_mat_khau_sau_khi_doi(self) -> None:
        bc = _BoiCanh()
        user = _tao_user(bc, must_change_password=True)

        await bc.doi_mat_khau().execute(user, MAT_KHAU, "MatKhauMoi456")

        assert user.must_change_password is False

    async def test_mat_khau_hien_tai_sai_thi_tu_choi(self) -> None:
        bc = _BoiCanh()
        user = _tao_user(bc)

        with pytest.raises(InvalidCurrentPasswordError):
            await bc.doi_mat_khau().execute(user, "SaiRoi123", "MatKhauMoi456")

    @pytest.mark.parametrize(
        "mat_khau_yeu",
        ["ngan1", "khongcochuso", "12345678"],
    )
    async def test_tu_choi_mat_khau_yeu(self, mat_khau_yeu: str) -> None:
        bc = _BoiCanh()
        user = _tao_user(bc)

        with pytest.raises(WeakPasswordError):
            await bc.doi_mat_khau().execute(user, MAT_KHAU, mat_khau_yeu)

    async def test_doi_mat_khau_thu_hoi_moi_phien_dang_dang_nhap(self) -> None:
        """Nếu mật khẩu cũ đã bị lộ, đổi mật khẩu phải đá kẻ tấn công ra."""
        bc = _BoiCanh()
        user = _tao_user(bc)
        phien_cu = await bc.dang_nhap().execute("nhanvien@congty.vn", MAT_KHAU)

        await bc.doi_mat_khau().execute(user, MAT_KHAU, "MatKhauMoi456")

        with pytest.raises(InvalidRefreshTokenError):
            await bc.lam_moi().execute(phien_cu.tokens.refresh_token)
