"""Đặt lại mật khẩu cho một tài khoản đã tồn tại.

Dùng khi quên mật khẩu, hoặc khi hash trong cơ sở dữ liệu được tạo bằng công cụ
ngoài ứng dụng và vì thế không đăng nhập được.

**Vì sao không sửa hash bằng SQL thủ công:** ``BcryptPasswordHasher`` băm mật
khẩu bằng SHA-256 rồi base64 TRƯỚC khi đưa vào bcrypt (bcrypt chỉ nhận 72 byte
và ném lỗi khi vượt; mật khẩu tiếng Việt có dấu rất dễ vượt). Một hash tạo bằng
``bcrypt.hashpw(mat_khau_tho, ...)`` trông y hệt — cũng ``$2b$`` 60 ký tự —
nhưng ứng dụng sẽ KHÔNG BAO GIỜ khớp được, và triệu chứng là
``INVALID_CREDENTIALS`` dù ``bcrypt.checkpw()`` chạy tay lại trả ``True``.
Script này dùng đúng hasher của ứng dụng nên không rơi vào bẫy đó.

Chạy:
    uv run python -m scripts.reset_password
    uv run python -m scripts.reset_password --email admin@congty.vn
    uv run python -m scripts.reset_password --email admin@congty.vn --must-change
"""

import argparse
import getpass
import sys

from src.modules.identity.application.use_cases.change_password import (
    WeakPasswordError,
    kiem_tra_do_manh,
)
from src.modules.identity.domain.entities.audit_log import AuditAction, AuditLog
from src.modules.identity.domain.value_objects.email import Email, InvalidEmailError
from src.modules.identity.domain.value_objects.password_hash import PasswordHash

# Import model để ``Base.metadata`` biết tới các bảng liên quan. Bắt buộc: khi
# SQLAlchemy flush bảng ``users`` nó phải giải được khoá ngoại
# ``users.department_id -> departments.id``; thiếu import thì ném
# ``NoReferencedTableError`` ngay giữa lúc lưu. Cùng lý do với ``migrations/env.py``.
from src.modules.identity.infrastructure.models.audit_log_model import (  # noqa: F401
    AuditLogModel,
)
from src.modules.identity.infrastructure.models.department_model import (  # noqa: F401
    DepartmentModel,
)
from src.modules.identity.infrastructure.models.refresh_token_model import (  # noqa: F401
    RefreshTokenModel,
)
from src.modules.identity.infrastructure.models.user_model import UserModel  # noqa: F401
from src.modules.identity.infrastructure.repositories.audit_log_repository import (
    SqlAlchemyAuditLogRepository,
)
from src.modules.identity.infrastructure.repositories.refresh_token_repository import (
    SqlAlchemyRefreshTokenRepository,
)
from src.modules.identity.infrastructure.repositories.user_repository import (
    SqlAlchemyUserRepository,
)
from src.modules.identity.infrastructure.security.password_hasher import (
    BcryptPasswordHasher,
)
from src.shared.infrastructure.clock import SystemClock
from src.shared.infrastructure.config import get_settings
from src.shared.infrastructure.database import create_engine_and_session_factory
from src.shared.infrastructure.event_loop import chay_async


async def dat_lai_mat_khau(email: str, mat_khau: str, must_change: bool) -> int:
    """Đặt lại mật khẩu; trả về mã thoát (0 = thành công)."""
    settings = get_settings()
    engine, session_factory = create_engine_and_session_factory(settings.database_url)

    try:
        async with session_factory() as session:
            user_repo = SqlAlchemyUserRepository(session)
            user = await user_repo.get_by_email(Email(email))
            if user is None:
                print(f"Không tìm thấy tài khoản với email {email}.")
                return 1

            bay_gio = SystemClock().now()
            hasher = BcryptPasswordHasher()
            user.set_password(
                PasswordHash(hasher.hash(mat_khau)),
                must_change=must_change,
                now=bay_gio,
            )
            await user_repo.update(user)

            # Đổi mật khẩu phải đá mọi phiên đang mở ra — nếu mật khẩu cũ đã bị
            # lộ, refresh token cấp trước đó không được tiếp tục dùng. Giữ đúng
            # hành vi của use case ChangePassword.
            await SqlAlchemyRefreshTokenRepository(session).revoke_all_for_user(
                user.id, now=bay_gio
            )

            # Ghi nhật ký: đây là thao tác quản trị, phải truy vết được.
            # actor_id=None vì chạy từ dòng lệnh, không qua phiên đăng nhập nào.
            await SqlAlchemyAuditLogRepository(session).add(
                AuditLog.record(
                    action=AuditAction.USER_PASSWORD_RESET,
                    actor_id=None,
                    resource_type="user",
                    resource_id=str(user.id),
                    now=bay_gio,
                    changes={"qua": "scripts.reset_password"},
                )
            )

            await session.commit()

        print(f"Đã đặt lại mật khẩu cho {user.email.value}.")
        print("Mọi phiên đăng nhập cũ đã bị thu hồi.")
        if must_change:
            print("Người dùng sẽ phải đổi mật khẩu ở lần đăng nhập tới.")
        if not user.is_active:
            # Đặt lại mật khẩu vẫn hợp lệ, nhưng nói trước để khỏi mất công:
            # tài khoản bị vô hiệu hoá sẽ nhận INACTIVE_ACCOUNT, không phải
            # INVALID_CREDENTIALS.
            print(
                "LƯU Ý: tài khoản này đang bị vô hiệu hoá (is_active = false) "
                "nên vẫn chưa đăng nhập được. Kích hoạt lại trước đã."
            )
        return 0
    finally:
        await engine.dispose()


def _cho_phep_tieng_viet() -> None:
    """Cho console Windows in được tiếng Việt.

    Console Windows mặc định dùng cp1252, không mã hoá nổi chữ có dấu nên mọi
    lệnh ``print`` tiếng Việt sẽ ném ``UnicodeEncodeError`` và script chết giữa
    chừng. Chuyển stdout/stderr sang UTF-8, thay ký tự không in được thay vì
    ném lỗi.
    """
    for luong in (sys.stdout, sys.stderr):
        if hasattr(luong, "reconfigure"):
            luong.reconfigure(encoding="utf-8", errors="replace")


def main() -> int:
    _cho_phep_tieng_viet()
    bo_doc = argparse.ArgumentParser(
        description="Đặt lại mật khẩu cho một tài khoản OmniChat đã tồn tại."
    )
    bo_doc.add_argument("--email", help="Email của tài khoản; bỏ trống sẽ được hỏi.")
    bo_doc.add_argument(
        "--must-change",
        action="store_true",
        help="Bắt người dùng đổi mật khẩu ở lần đăng nhập tới (cấp mật khẩu tạm).",
    )
    tham_so = bo_doc.parse_args()

    print("Đặt lại mật khẩu OmniChat\n")

    email = tham_so.email or input("Email: ").strip()
    if not email:
        print("Email không được để trống.")
        return 1

    try:
        Email(email)
    except InvalidEmailError as loi:
        print(loi.message)
        return 1

    # getpass để mật khẩu không hiện trên màn hình và không vào lịch sử shell.
    mat_khau = getpass.getpass("Mật khẩu mới: ")
    xac_nhan = getpass.getpass("Nhập lại mật khẩu mới: ")

    if mat_khau != xac_nhan:
        print("Hai lần nhập mật khẩu không khớp.")
        return 1

    try:
        kiem_tra_do_manh(mat_khau)
    except WeakPasswordError as loi:
        print(loi.message)
        return 1

    return chay_async(dat_lai_mat_khau(email, mat_khau, tham_so.must_change))


if __name__ == "__main__":
    raise SystemExit(main())
