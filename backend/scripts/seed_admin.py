"""Tạo quản trị viên đầu tiên.

Hệ thống không có đăng ký công khai và mọi tài khoản đều do quản trị viên cấp,
nên phải có một cách để tạo quản trị viên ban đầu. Đây chính là cách đó.

Chạy: uv run python -m scripts.seed_admin
"""

import asyncio
import getpass
import sys

from src.modules.identity.application.use_cases.change_password import (
    WeakPasswordError,
    kiem_tra_do_manh,
)
from src.modules.identity.domain.entities.user import User
from src.modules.identity.domain.value_objects.email import Email, InvalidEmailError
from src.modules.identity.domain.value_objects.password_hash import PasswordHash
from src.modules.identity.domain.value_objects.role import Role
from src.modules.identity.infrastructure.repositories.user_repository import (
    SqlAlchemyUserRepository,
)
from src.modules.identity.infrastructure.security.password_hasher import (
    BcryptPasswordHasher,
)
from src.shared.infrastructure.clock import SystemClock
from src.shared.infrastructure.config import get_settings
from src.shared.infrastructure.database import create_engine_and_session_factory
from src.shared.infrastructure.event_loop import cau_hinh_event_loop


async def tao_quan_tri_vien(email: str, ho_ten: str, mat_khau: str) -> None:
    cau_hinh_event_loop()
    settings = get_settings()
    engine, session_factory = create_engine_and_session_factory(settings.database_url)

    try:
        async with session_factory() as session:
            repo = SqlAlchemyUserRepository(session)

            if await repo.count_active_admins() > 0:
                print(
                    "Hệ thống đã có quản trị viên đang hoạt động. "
                    "Hãy dùng tài khoản đó để tạo thêm người dùng."
                )
                return

            dia_chi = Email(email)
            if await repo.get_by_email(dia_chi) is not None:
                print(f"Email {dia_chi.value} đã được sử dụng.")
                return

            admin = User.create(
                email=dia_chi,
                password_hash=PasswordHash(BcryptPasswordHasher().hash(mat_khau)),
                full_name=ho_ten,
                role=Role.ADMIN,
                department_id=None,
                now=SystemClock().now(),
                must_change_password=False,
            )
            await repo.add(admin)
            await session.commit()

            print(f"Đã tạo quản trị viên: {dia_chi.value}")
    finally:
        await engine.dispose()


def main() -> int:
    print("Tạo quản trị viên đầu tiên cho OmniChat\n")

    email = input("Email: ").strip()
    ho_ten = input("Họ và tên: ").strip()
    mat_khau = getpass.getpass("Mật khẩu: ")
    xac_nhan = getpass.getpass("Nhập lại mật khẩu: ")

    if mat_khau != xac_nhan:
        print("Hai lần nhập mật khẩu không khớp.")
        return 1

    try:
        Email(email)
        kiem_tra_do_manh(mat_khau)
    except (InvalidEmailError, WeakPasswordError) as loi:
        print(loi.message)
        return 1

    if not ho_ten:
        print("Họ và tên không được để trống.")
        return 1

    asyncio.run(tao_quan_tri_vien(email, ho_ten, mat_khau))
    return 0


if __name__ == "__main__":
    sys.exit(main())
