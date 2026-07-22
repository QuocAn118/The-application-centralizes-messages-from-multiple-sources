# OmniChat Foundation — Phần 4: Use case và API (Task 13–20)

> Tiếp nối [phần 3](2026-07-21-omnichat-foundation-part3-infra.md). Global Constraints ở [phần 1](2026-07-21-omnichat-foundation.md) áp dụng cho mọi task tại đây.

Giai đoạn cuối: nối domain và hạ tầng thành các luồng nghiệp vụ hoàn chỉnh, rồi phơi ra thành HTTP API.

## Quy ước chung cho mọi use case

Mỗi use case là một lớp có đúng một phương thức `execute`. Phụ thuộc nhận qua hàm khởi tạo, không tự tạo bên trong.

Use case nhận `requester: User` khi thao tác cần phân quyền theo ngữ cảnh dữ liệu. Route guard chỉ chặn được theo vai trò; câu hỏi "Manager này có được sửa nhân viên kia không" chỉ trả lời được ở đây.

Use case **không** tự commit. Router mở Unit of Work, gọi use case, rồi commit — nhờ đó nhiều thao tác gộp được vào một giao dịch.

---

## Task 13: Use case xác thực

**Files:**
- Create: `backend/src/modules/identity/application/dto/__init__.py`
- Create: `backend/src/modules/identity/application/dto/auth_dto.py`
- Create: `backend/src/modules/identity/application/use_cases/__init__.py`
- Create: `backend/src/modules/identity/application/use_cases/login_user.py`
- Create: `backend/src/modules/identity/application/use_cases/refresh_access_token.py`
- Create: `backend/src/modules/identity/application/use_cases/logout_user.py`
- Create: `backend/src/modules/identity/application/use_cases/change_password.py`
- Test: `backend/tests/unit/identity/test_auth_use_cases.py`

**Interfaces:**
- Consumes: repository interface (Task 8), `IPasswordHasher`/`ITokenService` (Task 12), fake (Task 8).
- Produces:
  - `TokenPair` — frozen dataclass: `access_token: str`, `refresh_token: str`, `token_type: str = "bearer"`, `expires_in: int`.
  - `LoginResult` — frozen dataclass: `tokens: TokenPair`, `user: User`, `must_change_password: bool`.
  - `LoginUser(user_repo, refresh_token_repo, audit_repo, hasher, token_service, clock, refresh_token_expire_days)` — `execute(email: str, password: str, ip_address: str | None = None, user_agent: str | None = None) -> LoginResult`.
  - `RefreshAccessToken(user_repo, refresh_token_repo, audit_repo, token_service, clock, refresh_token_expire_days)` — `execute(refresh_token: str, ip_address=None, user_agent=None) -> TokenPair`.
  - `LogoutUser(refresh_token_repo, audit_repo, token_service, clock)` — `execute(refresh_token: str, requester: User) -> None`.
  - `ChangePassword(user_repo, refresh_token_repo, audit_repo, hasher, clock)` — `execute(requester: User, current_password: str, new_password: str) -> None`.
  - `InvalidCredentialsError`, `InactiveAccountError`, `WeakPasswordError` — kế thừa `ApplicationError`.

**Quy tắc bảo mật cần giữ đúng:**

Đăng nhập sai email và sai mật khẩu phải trả về **cùng một lỗi**. Phân biệt hai trường hợp là để lộ email nào có tồn tại trong hệ thống.

Đổi mật khẩu thành công thu hồi **mọi** refresh token của người đó. Nếu mật khẩu bị lộ, đổi mật khẩu phải đá kẻ tấn công ra.

Refresh token dùng lại lần hai là dấu hiệu bị đánh cắp — thu hồi cả chuỗi, không chỉ token đó.

- [ ] **Step 1: Viết `dto/auth_dto.py`**

```python
"""DTO cho luồng xác thực."""

from dataclasses import dataclass

from src.modules.identity.domain.entities.user import User


@dataclass(frozen=True)
class TokenPair:
    """Cặp token trả về sau khi đăng nhập hoặc làm mới."""

    access_token: str
    refresh_token: str
    expires_in: int
    token_type: str = "bearer"


@dataclass(frozen=True)
class LoginResult:
    """Kết quả đăng nhập.

    ``must_change_password`` được nâng lên đây để client biết cần chuyển hướng
    sang màn hình đổi mật khẩu mà không phải đọc sâu vào ``user``.
    """

    tokens: TokenPair
    user: User
    must_change_password: bool
```

- [ ] **Step 2: Viết test cho `LoginUser`**

File `backend/tests/unit/identity/test_auth_use_cases.py` — phần đầu:

```python
from datetime import UTC, datetime, timedelta

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
```

- [ ] **Step 3: Chạy test để xác nhận thất bại**

```bash
cd backend
uv run pytest tests/unit/identity/test_auth_use_cases.py -v
```

Expected: FAIL với `ModuleNotFoundError` cho `use_cases`.

- [ ] **Step 4: Viết `login_user.py`**

```python
"""Use case đăng nhập."""

from datetime import timedelta

from src.modules.identity.application.dto.auth_dto import LoginResult, TokenPair
from src.modules.identity.application.ports import IPasswordHasher, ITokenService
from src.modules.identity.domain.entities.audit_log import AuditAction, AuditLog
from src.modules.identity.domain.entities.refresh_token import RefreshToken
from src.modules.identity.domain.repositories.audit_log_repository import (
    IAuditLogRepository,
)
from src.modules.identity.domain.repositories.refresh_token_repository import (
    IRefreshTokenRepository,
)
from src.modules.identity.domain.repositories.user_repository import IUserRepository
from src.modules.identity.domain.value_objects.email import Email, InvalidEmailError
from src.shared.application.exceptions import ApplicationError
from src.shared.application.ports import IClock


class InvalidCredentialsError(ApplicationError):
    """Email hoặc mật khẩu không đúng.

    Cố ý không phân biệt hai trường hợp: nói rõ email nào có tồn tại là giúp
    kẻ tấn công dò danh sách tài khoản.
    """

    def __init__(self) -> None:
        super().__init__(
            "Email hoặc mật khẩu không đúng.", code="INVALID_CREDENTIALS"
        )


class InactiveAccountError(ApplicationError):
    """Tài khoản đã bị vô hiệu hoá."""

    def __init__(self) -> None:
        super().__init__(
            "Tài khoản đã bị vô hiệu hoá. Vui lòng liên hệ quản trị viên.",
            code="INACTIVE_ACCOUNT",
        )


class LoginUser:
    """Xác thực người dùng và cấp cặp token."""

    def __init__(
        self,
        user_repo: IUserRepository,
        refresh_token_repo: IRefreshTokenRepository,
        audit_repo: IAuditLogRepository,
        hasher: IPasswordHasher,
        token_service: ITokenService,
        clock: IClock,
        refresh_token_expire_days: int,
    ) -> None:
        self._user_repo = user_repo
        self._refresh_token_repo = refresh_token_repo
        self._audit_repo = audit_repo
        self._hasher = hasher
        self._token_service = token_service
        self._clock = clock
        self._refresh_token_expire = timedelta(days=refresh_token_expire_days)

    async def _ghi_that_bai(
        self, email: str, ip_address: str | None, user_agent: str | None
    ) -> None:
        """Ghi nhật ký đăng nhập thất bại.

        Chỉ lưu email được thử, tuyệt đối không lưu mật khẩu.
        """
        await self._audit_repo.add(
            AuditLog.record(
                action=AuditAction.AUTH_LOGIN_FAILED,
                actor_id=None,
                resource_type="auth",
                resource_id=None,
                now=self._clock.now(),
                changes={"email_da_thu": email},
                ip_address=ip_address,
                user_agent=user_agent,
            )
        )

    async def execute(
        self,
        email: str,
        password: str,
        ip_address: str | None = None,
        user_agent: str | None = None,
    ) -> LoginResult:
        try:
            dia_chi = Email(email)
        except InvalidEmailError as loi:
            await self._ghi_that_bai(email, ip_address, user_agent)
            raise InvalidCredentialsError from loi

        user = await self._user_repo.get_by_email(dia_chi)

        if user is None or not self._hasher.verify(
            password, user.password_hash.value
        ):
            await self._ghi_that_bai(email, ip_address, user_agent)
            raise InvalidCredentialsError

        if not user.is_active:
            await self._ghi_that_bai(email, ip_address, user_agent)
            raise InactiveAccountError

        bay_gio = self._clock.now()
        user.record_login(now=bay_gio)
        await self._user_repo.update(user)

        access_token = self._token_service.create_access_token(
            user_id=user.id, role=user.role, department_id=user.department_id
        )
        tho, chuoi_hash = self._token_service.create_refresh_token()
        await self._refresh_token_repo.add(
            RefreshToken.issue(
                user_id=user.id,
                token_hash=chuoi_hash,
                expires_at=bay_gio + self._refresh_token_expire,
                now=bay_gio,
                user_agent=user_agent,
                ip_address=ip_address,
            )
        )

        await self._audit_repo.add(
            AuditLog.record(
                action=AuditAction.AUTH_LOGIN_SUCCEEDED,
                actor_id=user.id,
                resource_type="auth",
                resource_id=str(user.id),
                now=bay_gio,
                ip_address=ip_address,
                user_agent=user_agent,
            )
        )

        payload = self._token_service.decode_access_token(access_token)
        con_lai = int((payload.expires_at - bay_gio).total_seconds())

        return LoginResult(
            tokens=TokenPair(
                access_token=access_token,
                refresh_token=tho,
                expires_in=con_lai,
            ),
            user=user,
            must_change_password=user.must_change_password,
        )
```

- [ ] **Step 5: Viết `refresh_access_token.py`**

```python
"""Use case làm mới access token."""

from datetime import timedelta

from src.modules.identity.application.dto.auth_dto import TokenPair
from src.modules.identity.application.ports import ITokenService
from src.modules.identity.domain.entities.audit_log import AuditAction, AuditLog
from src.modules.identity.domain.entities.refresh_token import RefreshToken
from src.modules.identity.domain.repositories.audit_log_repository import (
    IAuditLogRepository,
)
from src.modules.identity.domain.repositories.refresh_token_repository import (
    IRefreshTokenRepository,
)
from src.modules.identity.domain.repositories.user_repository import IUserRepository
from src.shared.application.exceptions import AuthenticationError
from src.shared.application.ports import IClock


class InvalidRefreshTokenError(AuthenticationError):
    """Refresh token không tồn tại, đã hết hạn, hoặc đã bị thu hồi."""

    def __init__(self) -> None:
        super().__init__(
            "Phiên đăng nhập không hợp lệ. Vui lòng đăng nhập lại.",
            code="INVALID_REFRESH_TOKEN",
        )


class RefreshAccessToken:
    """Đổi refresh token lấy cặp token mới.

    Mỗi lần làm mới sinh refresh token mới và thu hồi token cũ (rotation). Nếu
    một token đã bị thay thế lại được gửi lên, đó là dấu hiệu token bị đánh cắp
    — khi đó toàn bộ chuỗi token bị thu hồi, buộc cả kẻ tấn công lẫn người dùng
    thật phải đăng nhập lại.
    """

    def __init__(
        self,
        user_repo: IUserRepository,
        refresh_token_repo: IRefreshTokenRepository,
        audit_repo: IAuditLogRepository,
        token_service: ITokenService,
        clock: IClock,
        refresh_token_expire_days: int,
    ) -> None:
        self._user_repo = user_repo
        self._refresh_token_repo = refresh_token_repo
        self._audit_repo = audit_repo
        self._token_service = token_service
        self._clock = clock
        self._refresh_token_expire = timedelta(days=refresh_token_expire_days)

    async def execute(
        self,
        refresh_token: str,
        ip_address: str | None = None,
        user_agent: str | None = None,
    ) -> TokenPair:
        bay_gio = self._clock.now()
        chuoi_hash = self._token_service.hash_refresh_token(refresh_token)
        token_cu = await self._refresh_token_repo.get_by_hash(chuoi_hash)

        if token_cu is None:
            raise InvalidRefreshTokenError

        if token_cu.replaced_by_id is not None:
            # Token này đã được xoay trước đó mà vẫn có người dùng lại — dấu
            # hiệu bị đánh cắp. Thu hồi cả chuỗi.
            await self._refresh_token_repo.revoke_chain(token_cu, now=bay_gio)
            await self._audit_repo.add(
                AuditLog.record(
                    action=AuditAction.AUTH_TOKEN_REUSE_DETECTED,
                    actor_id=token_cu.user_id,
                    resource_type="auth",
                    resource_id=str(token_cu.user_id),
                    now=bay_gio,
                    ip_address=ip_address,
                    user_agent=user_agent,
                )
            )
            raise InvalidRefreshTokenError

        if not token_cu.is_valid(now=bay_gio):
            raise InvalidRefreshTokenError

        user = await self._user_repo.get_by_id(token_cu.user_id)
        if user is None or not user.is_active:
            raise InvalidRefreshTokenError

        tho_moi, hash_moi = self._token_service.create_refresh_token()
        token_moi = RefreshToken.issue(
            user_id=user.id,
            token_hash=hash_moi,
            expires_at=bay_gio + self._refresh_token_expire,
            now=bay_gio,
            user_agent=user_agent,
            ip_address=ip_address,
        )
        await self._refresh_token_repo.add(token_moi)

        token_cu.rotate_to(new_token_id=token_moi.id, now=bay_gio)
        await self._refresh_token_repo.update(token_cu)

        access_token = self._token_service.create_access_token(
            user_id=user.id, role=user.role, department_id=user.department_id
        )
        payload = self._token_service.decode_access_token(access_token)

        return TokenPair(
            access_token=access_token,
            refresh_token=tho_moi,
            expires_in=int((payload.expires_at - bay_gio).total_seconds()),
        )
```

- [ ] **Step 6: Viết `logout_user.py`**

```python
"""Use case đăng xuất."""

from src.modules.identity.application.ports import ITokenService
from src.modules.identity.domain.entities.audit_log import AuditAction, AuditLog
from src.modules.identity.domain.entities.user import User
from src.modules.identity.domain.repositories.audit_log_repository import (
    IAuditLogRepository,
)
from src.modules.identity.domain.repositories.refresh_token_repository import (
    IRefreshTokenRepository,
)
from src.shared.application.ports import IClock


class LogoutUser:
    """Thu hồi refresh token của phiên hiện tại.

    Access token vẫn còn hiệu lực tới khi hết hạn — xem mục 9 của spec về giới
    hạn này.
    """

    def __init__(
        self,
        refresh_token_repo: IRefreshTokenRepository,
        audit_repo: IAuditLogRepository,
        token_service: ITokenService,
        clock: IClock,
    ) -> None:
        self._refresh_token_repo = refresh_token_repo
        self._audit_repo = audit_repo
        self._token_service = token_service
        self._clock = clock

    async def execute(self, refresh_token: str, requester: User) -> None:
        """Đăng xuất.

        Không báo lỗi khi token không tồn tại: đăng xuất hai lần, hoặc đăng
        xuất bằng token đã hết hạn, đều nên coi là thành công.
        """
        bay_gio = self._clock.now()
        chuoi_hash = self._token_service.hash_refresh_token(refresh_token)
        token = await self._refresh_token_repo.get_by_hash(chuoi_hash)

        if token is not None and token.user_id == requester.id:
            token.revoke(now=bay_gio)
            await self._refresh_token_repo.update(token)

        await self._audit_repo.add(
            AuditLog.record(
                action=AuditAction.AUTH_LOGOUT,
                actor_id=requester.id,
                resource_type="auth",
                resource_id=str(requester.id),
                now=bay_gio,
            )
        )
```

- [ ] **Step 7: Viết `change_password.py`**

```python
"""Use case đổi mật khẩu."""

from src.modules.identity.application.ports import IPasswordHasher
from src.modules.identity.domain.entities.audit_log import AuditAction, AuditLog
from src.modules.identity.domain.entities.user import User
from src.modules.identity.domain.repositories.audit_log_repository import (
    IAuditLogRepository,
)
from src.modules.identity.domain.repositories.refresh_token_repository import (
    IRefreshTokenRepository,
)
from src.modules.identity.domain.repositories.user_repository import IUserRepository
from src.modules.identity.domain.value_objects.password_hash import PasswordHash
from src.shared.application.exceptions import ApplicationError
from src.shared.application.ports import IClock

DO_DAI_MAT_KHAU_TOI_THIEU = 8


class WeakPasswordError(ApplicationError):
    """Mật khẩu mới không đạt yêu cầu tối thiểu."""

    def __init__(self, ly_do: str) -> None:
        super().__init__(ly_do, code="WEAK_PASSWORD")


class InvalidCurrentPasswordError(ApplicationError):
    """Mật khẩu hiện tại không đúng."""

    def __init__(self) -> None:
        super().__init__(
            "Mật khẩu hiện tại không đúng.", code="INVALID_CURRENT_PASSWORD"
        )


def kiem_tra_do_manh(mat_khau: str) -> None:
    """Kiểm tra yêu cầu tối thiểu cho mật khẩu.

    Chỉ đặt ngưỡng độ dài và yêu cầu có cả chữ lẫn số. Không ép ký tự đặc biệt
    — quy tắc càng rườm rà, người dùng càng có xu hướng ghi mật khẩu ra giấy.
    """
    if len(mat_khau) < DO_DAI_MAT_KHAU_TOI_THIEU:
        raise WeakPasswordError(
            f"Mật khẩu phải có ít nhất {DO_DAI_MAT_KHAU_TOI_THIEU} ký tự."
        )
    if not any(k.isalpha() for k in mat_khau):
        raise WeakPasswordError("Mật khẩu phải chứa ít nhất một chữ cái.")
    if not any(k.isdigit() for k in mat_khau):
        raise WeakPasswordError("Mật khẩu phải chứa ít nhất một chữ số.")


class ChangePassword:
    """Người dùng tự đổi mật khẩu của mình."""

    def __init__(
        self,
        user_repo: IUserRepository,
        refresh_token_repo: IRefreshTokenRepository,
        audit_repo: IAuditLogRepository,
        hasher: IPasswordHasher,
        clock: IClock,
    ) -> None:
        self._user_repo = user_repo
        self._refresh_token_repo = refresh_token_repo
        self._audit_repo = audit_repo
        self._hasher = hasher
        self._clock = clock

    async def execute(
        self, requester: User, current_password: str, new_password: str
    ) -> None:
        if not self._hasher.verify(
            current_password, requester.password_hash.value
        ):
            raise InvalidCurrentPasswordError

        kiem_tra_do_manh(new_password)

        bay_gio = self._clock.now()
        requester.set_password(
            PasswordHash(self._hasher.hash(new_password)),
            must_change=False,
            now=bay_gio,
        )
        await self._user_repo.update(requester)

        # Đổi mật khẩu phải đá mọi phiên khác ra: nếu mật khẩu cũ đã bị lộ,
        # kẻ tấn công không được tiếp tục dùng refresh token của họ.
        await self._refresh_token_repo.revoke_all_for_user(
            requester.id, now=bay_gio
        )

        await self._audit_repo.add(
            AuditLog.record(
                action=AuditAction.USER_PASSWORD_CHANGED,
                actor_id=requester.id,
                resource_type="user",
                resource_id=str(requester.id),
                now=bay_gio,
            )
        )
```

- [ ] **Step 8: Bổ sung test cho làm mới, đăng xuất, đổi mật khẩu**

Thêm vào cuối `backend/tests/unit/identity/test_auth_use_cases.py`:

```python
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
        nan_nhan = _tao_user(bc, email="nannhan@congty.vn")
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
```

- [ ] **Step 9: Chạy test để xác nhận thành công**

```bash
cd backend
mkdir -p src/modules/identity/application/dto src/modules/identity/application/use_cases
touch src/modules/identity/application/dto/__init__.py \
      src/modules/identity/application/use_cases/__init__.py
uv run pytest tests/unit/identity/test_auth_use_cases.py -v
```

Expected: `31 passed`.

- [ ] **Step 10: Kiểm tra chất lượng mã**

```bash
uv run mypy src
uv run ruff check .
uv run lint-imports
```

Expected: xanh.

- [ ] **Step 11: Commit**

```bash
git add backend/src/modules/identity/application backend/tests/unit/identity/test_auth_use_cases.py
git commit -m "feat: add authentication use cases with token rotation"
```

---

## Các task còn lại

Task 14–20 tiếp tục ở các file sau, tách nhỏ để mỗi file giữ đủ chi tiết:

- [Phần 4b — Use case quản trị](2026-07-21-omnichat-foundation-part4b-admin-usecases.md) (Task 14–15)
- [Phần 4c — FastAPI và router](2026-07-21-omnichat-foundation-part4c-http.md) (Task 16–18)
- [Phần 4d — Hoàn thiện](2026-07-21-omnichat-foundation-part4d-hardening.md) (Task 19–20)
