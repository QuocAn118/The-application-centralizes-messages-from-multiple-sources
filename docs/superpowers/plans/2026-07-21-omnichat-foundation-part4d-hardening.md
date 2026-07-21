# OmniChat Foundation — Phần 4d: Hoàn thiện (Task 19–20)

> Tiếp nối [phần 4c](2026-07-21-omnichat-foundation-part4c-http.md). Global Constraints ở [phần 1](2026-07-21-omnichat-foundation.md) áp dụng cho mọi task tại đây.

---

## Task 19: Rate limit và seed script

**Files:**
- Create: `backend/src/shared/infrastructure/rate_limiter.py`
- Modify: `backend/src/modules/identity/presentation/routers/auth_router.py` — thêm rate limit vào endpoint đăng nhập
- Create: `backend/scripts/__init__.py`
- Create: `backend/scripts/seed_admin.py`
- Test: `backend/tests/unit/shared/test_rate_limiter.py`
- Test: `backend/tests/e2e/test_rate_limit.py`

**Interfaces:**
- Consumes: `IClock` (Task 2), `Settings` (Task 3).
- Produces:
  - `InMemoryRateLimiter(max_attempts: int, window_seconds: int, clock: IClock)` — `check(key: str) -> None` ném `RateLimitExceededError` khi vượt ngưỡng; `reset(key: str) -> None` xoá bộ đếm sau khi đăng nhập thành công.
  - `RateLimitExceededError` — kế thừa `ApplicationError`, có `retry_after_seconds: int`.
  - `scripts/seed_admin.py` — script tạo quản trị viên đầu tiên.

**Giới hạn đã biết:** bộ đếm nằm trong bộ nhớ tiến trình. Chạy nhiều bản sao thì mỗi bản có bộ đếm riêng, nên ngưỡng thực tế nhân lên theo số bản sao. Đây là nợ kỹ thuật đã ghi trong mục 9 của spec; khi mở rộng phải chuyển sang Redis.

- [ ] **Step 1: Viết test cho rate limiter**

File `backend/tests/unit/shared/test_rate_limiter.py`:

```python
from datetime import UTC, datetime

import pytest

from src.shared.infrastructure.rate_limiter import (
    InMemoryRateLimiter,
    RateLimitExceededError,
)
from tests.unit.identity.fakes import FakeClock

BAY_GIO = datetime(2026, 7, 21, 10, 0, tzinfo=UTC)


def _tao(max_attempts: int = 3, window_seconds: int = 300) -> tuple:
    dong_ho = FakeClock(BAY_GIO)
    return InMemoryRateLimiter(max_attempts, window_seconds, dong_ho), dong_ho


class TestNguongThuLai:
    def test_cho_phep_trong_gioi_han(self) -> None:
        gioi_han, _ = _tao(max_attempts=3)

        for _ in range(3):
            gioi_han.check("a@congty.vn")

    def test_vuot_gioi_han_thi_chan(self) -> None:
        gioi_han, _ = _tao(max_attempts=3)
        for _ in range(3):
            gioi_han.check("a@congty.vn")

        with pytest.raises(RateLimitExceededError):
            gioi_han.check("a@congty.vn")

    def test_cac_khoa_khac_nhau_dem_rieng(self) -> None:
        gioi_han, _ = _tao(max_attempts=2)
        gioi_han.check("a@congty.vn")
        gioi_han.check("a@congty.vn")

        gioi_han.check("b@congty.vn")

    def test_bo_dem_duoc_xoa_sau_khi_het_cua_so(self) -> None:
        gioi_han, dong_ho = _tao(max_attempts=2, window_seconds=300)
        gioi_han.check("a@congty.vn")
        gioi_han.check("a@congty.vn")

        dong_ho.advance(seconds=301)

        gioi_han.check("a@congty.vn")

    def test_van_chan_khi_chua_het_cua_so(self) -> None:
        gioi_han, dong_ho = _tao(max_attempts=2, window_seconds=300)
        gioi_han.check("a@congty.vn")
        gioi_han.check("a@congty.vn")

        dong_ho.advance(seconds=299)

        with pytest.raises(RateLimitExceededError):
            gioi_han.check("a@congty.vn")

    def test_bao_so_giay_can_cho(self) -> None:
        gioi_han, _ = _tao(max_attempts=1, window_seconds=300)
        gioi_han.check("a@congty.vn")

        with pytest.raises(RateLimitExceededError) as loi:
            gioi_han.check("a@congty.vn")

        assert loi.value.retry_after_seconds > 0
        assert loi.value.retry_after_seconds <= 300


class TestXoaBoDem:
    def test_dang_nhap_thanh_cong_xoa_bo_dem(self) -> None:
        """Người dùng gõ nhầm vài lần rồi đăng nhập được không nên bị phạt tiếp."""
        gioi_han, _ = _tao(max_attempts=3)
        gioi_han.check("a@congty.vn")
        gioi_han.check("a@congty.vn")

        gioi_han.reset("a@congty.vn")

        for _ in range(3):
            gioi_han.check("a@congty.vn")

    def test_xoa_khoa_khong_ton_tai_khong_gay_loi(self) -> None:
        gioi_han, _ = _tao()

        gioi_han.reset("chua-bao-gio-goi@congty.vn")


class TestDonRac:
    def test_khong_giu_mai_cac_khoa_da_het_han(self) -> None:
        """Bộ đếm phải được dọn, nếu không bộ nhớ sẽ phình theo số email bị dò."""
        gioi_han, dong_ho = _tao(max_attempts=5, window_seconds=60)
        for i in range(100):
            gioi_han.check(f"dothu{i}@congty.vn")

        dong_ho.advance(seconds=61)
        gioi_han.check("kich-hoat-don-rac@congty.vn")

        assert gioi_han.so_khoa_dang_giu() <= 2
```

- [ ] **Step 2: Chạy test để xác nhận thất bại**

```bash
cd backend
uv run pytest tests/unit/shared/test_rate_limiter.py -v
```

Expected: FAIL với `ModuleNotFoundError`.

- [ ] **Step 3: Viết `rate_limiter.py`**

```python
"""Giới hạn tần suất gọi, lưu trong bộ nhớ tiến trình."""

from collections import defaultdict
from datetime import datetime, timedelta

from src.shared.application.exceptions import ApplicationError
from src.shared.application.ports import IClock


class RateLimitExceededError(ApplicationError):
    """Vượt quá số lần cho phép trong khoảng thời gian quy định."""

    def __init__(self, retry_after_seconds: int) -> None:
        super().__init__(
            f"Bạn đã thử quá nhiều lần. Vui lòng thử lại sau "
            f"{retry_after_seconds} giây.",
            code="RATE_LIMIT_EXCEEDED",
        )
        self.retry_after_seconds = retry_after_seconds


class InMemoryRateLimiter:
    """Đếm số lần gọi theo cửa sổ trượt, giữ trong bộ nhớ.

    **Giới hạn quan trọng:** bộ đếm nằm trong bộ nhớ của một tiến trình. Khi
    chạy nhiều bản sao, mỗi bản giữ bộ đếm riêng nên ngưỡng thực tế bị nhân lên
    theo số bản sao. Với mục tiêu 1000 người dùng đồng thời, hệ thống gần như
    chắc chắn phải chạy nhiều bản sao — lúc đó cần chuyển bộ đếm sang Redis.
    Xem mục 9 của spec.
    """

    def __init__(
        self, max_attempts: int, window_seconds: int, clock: IClock
    ) -> None:
        self._max_attempts = max_attempts
        self._window = timedelta(seconds=window_seconds)
        self._clock = clock
        self._lan_goi: dict[str, list[datetime]] = defaultdict(list)

    def _don_rac(self, bay_gio: datetime) -> None:
        """Xoá các khoá không còn lần gọi nào trong cửa sổ.

        Không dọn thì mỗi email bị kẻ tấn công thử sẽ chiếm bộ nhớ vĩnh viễn.
        """
        moc = bay_gio - self._window
        khoa_can_xoa = [
            khoa
            for khoa, danh_sach in self._lan_goi.items()
            if not any(t > moc for t in danh_sach)
        ]
        for khoa in khoa_can_xoa:
            del self._lan_goi[khoa]

    def check(self, key: str) -> None:
        """Ghi nhận một lần gọi và chặn nếu vượt ngưỡng."""
        bay_gio = self._clock.now()
        self._don_rac(bay_gio)

        moc = bay_gio - self._window
        con_hieu_luc = [t for t in self._lan_goi[key] if t > moc]

        if len(con_hieu_luc) >= self._max_attempts:
            som_nhat = min(con_hieu_luc)
            con_lai = (som_nhat + self._window - bay_gio).total_seconds()
            # Làm tròn lên để không báo "thử lại sau 0 giây", nhưng kẹp trần ở
            # độ dài cửa sổ: thời gian chờ không bao giờ vượt quá nó.
            cho_them = min(int(con_lai) + 1, int(self._window.total_seconds()))
            self._lan_goi[key] = con_hieu_luc
            raise RateLimitExceededError(retry_after_seconds=max(cho_them, 1))

        con_hieu_luc.append(bay_gio)
        self._lan_goi[key] = con_hieu_luc

    def reset(self, key: str) -> None:
        """Xoá bộ đếm của một khoá, gọi sau khi đăng nhập thành công."""
        self._lan_goi.pop(key, None)

    def so_khoa_dang_giu(self) -> int:
        """Số khoá đang lưu — dùng để kiểm chứng việc dọn rác trong test."""
        return len(self._lan_goi)
```

- [ ] **Step 4: Gắn rate limit vào endpoint đăng nhập**

Sửa `backend/src/modules/identity/presentation/routers/auth_router.py`.

Thêm import:

```python
from src.shared.infrastructure.rate_limiter import InMemoryRateLimiter
```

Thêm ngay dưới dòng `router = APIRouter(...)`:

```python
def _lay_rate_limiter(request: Request) -> InMemoryRateLimiter:
    """Lấy bộ giới hạn dùng chung cho toàn ứng dụng.

    Đặt trong ``app.state`` để mọi request chia sẻ cùng một bộ đếm; tạo mới
    theo từng request sẽ khiến giới hạn không có tác dụng.
    """
    limiter: InMemoryRateLimiter = request.app.state.login_rate_limiter
    return limiter
```

Sửa thân hàm `dang_nhap`, thêm ngay đầu hàm:

```python
    limiter = _lay_rate_limiter(request)
    ip = _dia_chi_goi(request)
    # Giới hạn theo cả email và địa chỉ IP: theo email để bảo vệ một tài khoản
    # cụ thể, theo IP để chặn việc dò hàng loạt tài khoản khác nhau.
    limiter.check(f"email:{du_lieu.email.lower()}")
    if ip:
        limiter.check(f"ip:{ip}")
```

và ngay trước dòng `return TokenResponse(...)`:

```python
    limiter.reset(f"email:{du_lieu.email.lower()}")
    if ip:
        limiter.reset(f"ip:{ip}")
```

- [ ] **Step 5: Khởi tạo rate limiter trong `create_app`**

Sửa `backend/src/main.py`, thêm vào hàm `lifespan` ngay sau khi gán `session_factory`:

```python
    from src.shared.infrastructure.clock import SystemClock
    from src.shared.infrastructure.rate_limiter import InMemoryRateLimiter

    app.state.login_rate_limiter = InMemoryRateLimiter(
        max_attempts=settings.login_rate_limit_attempts,
        window_seconds=settings.login_rate_limit_window_seconds,
        clock=SystemClock(),
    )
```

Thêm `RateLimitExceededError` vào bảng ánh xạ mã HTTP trong `_MA_HTTP`, đặt **trước** dòng `(ApplicationError, 400)`:

```python
    (RateLimitExceededError, 429),
```

kèm import:

```python
from src.shared.infrastructure.rate_limiter import RateLimitExceededError
```

- [ ] **Step 6: Viết test đầu-cuối cho rate limit**

File `backend/tests/e2e/test_rate_limit.py`:

```python
import pytest
from httpx import AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine

pytestmark = [pytest.mark.e2e, pytest.mark.integration]

MAT_KHAU = "MatKhauDung123"


async def _tao_admin(engine: AsyncEngine) -> None:
    from src.modules.identity.infrastructure.security.password_hasher import (
        BcryptPasswordHasher,
    )
    from src.shared.domain.identifiers import new_id

    async with engine.begin() as conn:
        await conn.execute(
            text(
                "INSERT INTO users (id, email, password_hash, full_name, phone, role, "
                "department_id, is_active, must_change_password, last_login_at, "
                "created_at, updated_at) VALUES (:id, 'admin@congty.vn', :hash, "
                "'Quản trị viên', NULL, 'ADMIN', NULL, true, false, NULL, now(), now())"
            ),
            {"id": new_id(), "hash": BcryptPasswordHasher(rounds=4).hash(MAT_KHAU)},
        )


async def test_thu_sai_nhieu_lan_bi_chan(
    client: AsyncClient, engine: AsyncEngine, app_test
) -> None:
    """Chống dò mật khẩu bằng cách thử liên tục."""
    await _tao_admin(engine)
    from src.shared.infrastructure.clock import SystemClock
    from src.shared.infrastructure.rate_limiter import InMemoryRateLimiter

    app_test.state.login_rate_limiter = InMemoryRateLimiter(
        max_attempts=3, window_seconds=300, clock=SystemClock()
    )

    for _ in range(3):
        await client.post(
            "/api/v1/auth/login",
            json={"email": "admin@congty.vn", "password": "SaiRoi123"},
        )

    phan_hoi = await client.post(
        "/api/v1/auth/login",
        json={"email": "admin@congty.vn", "password": "SaiRoi123"},
    )

    assert phan_hoi.status_code == 429
    assert phan_hoi.json()["error"]["code"] == "RATE_LIMIT_EXCEEDED"


async def test_dang_nhap_dung_xoa_bo_dem(
    client: AsyncClient, engine: AsyncEngine, app_test
) -> None:
    """Gõ nhầm vài lần rồi đăng nhập được thì không bị phạt tiếp."""
    await _tao_admin(engine)
    from src.shared.infrastructure.clock import SystemClock
    from src.shared.infrastructure.rate_limiter import InMemoryRateLimiter

    app_test.state.login_rate_limiter = InMemoryRateLimiter(
        max_attempts=3, window_seconds=300, clock=SystemClock()
    )

    for _ in range(2):
        await client.post(
            "/api/v1/auth/login",
            json={"email": "admin@congty.vn", "password": "SaiRoi123"},
        )
    await client.post(
        "/api/v1/auth/login",
        json={"email": "admin@congty.vn", "password": MAT_KHAU},
    )

    phan_hoi = await client.post(
        "/api/v1/auth/login",
        json={"email": "admin@congty.vn", "password": "SaiRoi123"},
    )

    assert phan_hoi.status_code == 400
```

- [ ] **Step 7: Viết `scripts/seed_admin.py`**

```python
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


async def tao_quan_tri_vien(email: str, ho_ten: str, mat_khau: str) -> None:
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
```

**Vì sao dùng `getpass` chứ không phải `input`:** mật khẩu gõ qua `input()` hiện rõ trên màn hình và có thể lọt vào lịch sử shell.

- [ ] **Step 8: Chạy test**

```bash
cd backend
mkdir -p scripts
touch scripts/__init__.py
uv run pytest tests/unit/shared/test_rate_limiter.py tests/e2e/test_rate_limit.py -v
```

Expected: `11 passed`.

- [ ] **Step 9: Thử seed script**

```bash
uv run python -m scripts.seed_admin
```

Nhập email, họ tên, mật khẩu. Expected: `Đã tạo quản trị viên: <email>`.

Chạy lại lần hai — Expected: `Hệ thống đã có quản trị viên đang hoạt động.`

- [ ] **Step 10: Commit**

```bash
git add backend/src/shared/infrastructure/rate_limiter.py backend/src/main.py \
        backend/src/modules/identity/presentation/routers/auth_router.py \
        backend/scripts backend/tests/unit/shared/test_rate_limiter.py \
        backend/tests/e2e/test_rate_limit.py
git commit -m "feat: add login rate limiting and admin seed script"
```

---

## Task 20: CI pipeline và hoàn thiện

**Files:**
- Create: `.github/workflows/backend-ci.yml`
- Create: `backend/Dockerfile`
- Create: `backend/.dockerignore`
- Modify: `backend/README.md` — bổ sung hướng dẫn vận hành
- Test: `backend/tests/e2e/test_luong_hoan_chinh.py`

**Interfaces:**
- Consumes: toàn bộ Task 1–19.
- Produces: CI chạy đủ ba tầng test, ảnh Docker, và một test đầu-cuối đi hết vòng đời hệ thống.

- [ ] **Step 1: Viết test luồng hoàn chỉnh**

File `backend/tests/e2e/test_luong_hoan_chinh.py`:

```python
"""Một kịch bản duy nhất đi qua toàn bộ vòng đời của hệ thống.

Test này tồn tại để bắt lỗi tích hợp giữa các thành phần — thứ mà test đơn lẻ
không thấy được.
"""

import pytest
from httpx import AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine

pytestmark = [pytest.mark.e2e, pytest.mark.integration]

MAT_KHAU_ADMIN = "MatKhauAdmin123"
MAT_KHAU_TAM = "MatKhauTam123"


def _bearer(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


async def _tao_admin(engine: AsyncEngine) -> None:
    from src.modules.identity.infrastructure.security.password_hasher import (
        BcryptPasswordHasher,
    )
    from src.shared.domain.identifiers import new_id

    async with engine.begin() as conn:
        await conn.execute(
            text(
                "INSERT INTO users (id, email, password_hash, full_name, phone, role, "
                "department_id, is_active, must_change_password, last_login_at, "
                "created_at, updated_at) VALUES (:id, 'admin@congty.vn', :hash, "
                "'Quản trị viên', NULL, 'ADMIN', NULL, true, false, NULL, now(), now())"
            ),
            {
                "id": new_id(),
                "hash": BcryptPasswordHasher(rounds=4).hash(MAT_KHAU_ADMIN),
            },
        )


async def test_vong_doi_day_du_cua_he_thong(
    client: AsyncClient, engine: AsyncEngine
) -> None:
    await _tao_admin(engine)

    # 1. Quản trị viên đăng nhập
    dn = await client.post(
        "/api/v1/auth/login",
        json={"email": "admin@congty.vn", "password": MAT_KHAU_ADMIN},
    )
    assert dn.status_code == 200
    admin_token = dn.json()["access_token"]

    # 2. Tạo phòng ban
    phong = await client.post(
        "/api/v1/departments",
        json={"name": "Tư vấn sản phẩm A", "description": "Phòng tư vấn"},
        headers=_bearer(admin_token),
    )
    assert phong.status_code == 201
    phong_id = phong.json()["id"]

    # 3. Tạo quản lý cho phòng
    ql = await client.post(
        "/api/v1/users",
        json={
            "email": "quanly@congty.vn",
            "full_name": "Trần Quản Lý",
            "role": "MANAGER",
            "department_id": phong_id,
            "password": MAT_KHAU_TAM,
        },
        headers=_bearer(admin_token),
    )
    assert ql.status_code == 201

    # 4. Tạo nhân viên
    nv = await client.post(
        "/api/v1/users",
        json={
            "email": "nhanvien@congty.vn",
            "full_name": "Lê Nhân Viên",
            "role": "STAFF",
            "department_id": phong_id,
            "password": MAT_KHAU_TAM,
        },
        headers=_bearer(admin_token),
    )
    assert nv.status_code == 201
    nv_id = nv.json()["id"]

    # 5. Nhân viên đăng nhập lần đầu, được báo phải đổi mật khẩu
    nv_dn = await client.post(
        "/api/v1/auth/login",
        json={"email": "nhanvien@congty.vn", "password": MAT_KHAU_TAM},
    )
    assert nv_dn.json()["must_change_password"] is True
    nv_token = nv_dn.json()["access_token"]

    # 6. Nhân viên đổi mật khẩu
    doi = await client.post(
        "/api/v1/auth/change-password",
        json={"current_password": MAT_KHAU_TAM, "new_password": "MatKhauRieng456"},
        headers=_bearer(nv_token),
    )
    assert doi.status_code == 204

    # 7. Đăng nhập bằng mật khẩu mới, không còn bị bắt đổi
    nv_dn2 = await client.post(
        "/api/v1/auth/login",
        json={"email": "nhanvien@congty.vn", "password": "MatKhauRieng456"},
    )
    assert nv_dn2.json()["must_change_password"] is False
    nv_token = nv_dn2.json()["access_token"]

    # 8. Nhân viên không gọi được endpoint quản trị
    cam = await client.post(
        "/api/v1/users",
        json={
            "email": "tuy_tien@congty.vn",
            "full_name": "Tự tạo",
            "role": "STAFF",
            "department_id": phong_id,
            "password": MAT_KHAU_TAM,
        },
        headers=_bearer(nv_token),
    )
    assert cam.status_code == 403

    # 9. Quản lý thấy được nhân viên phòng mình
    ql_dn = await client.post(
        "/api/v1/auth/login",
        json={"email": "quanly@congty.vn", "password": MAT_KHAU_TAM},
    )
    ql_token = ql_dn.json()["access_token"]
    ds = await client.get("/api/v1/users", headers=_bearer(ql_token))
    assert "nhanvien@congty.vn" in {u["email"] for u in ds.json()["items"]}

    # 10. Quản trị viên nâng nhân viên lên quản lý — bị chặn vì phòng đã có
    nang = await client.patch(
        f"/api/v1/users/{nv_id}/role",
        json={"role": "MANAGER", "department_id": phong_id},
        headers=_bearer(admin_token),
    )
    assert nang.status_code == 422
    assert nang.json()["error"]["code"] == "DEPARTMENT_ALREADY_HAS_MANAGER"

    # 11. Vô hiệu hoá nhân viên
    vhh = await client.post(
        f"/api/v1/users/{nv_id}/deactivate", headers=_bearer(admin_token)
    )
    assert vhh.status_code == 200
    assert vhh.json()["is_active"] is False

    # 12. Nhân viên đã nghỉ không đăng nhập được nữa
    thu_lai = await client.post(
        "/api/v1/auth/login",
        json={"email": "nhanvien@congty.vn", "password": "MatKhauRieng456"},
    )
    assert thu_lai.status_code == 400
    assert thu_lai.json()["error"]["code"] == "INACTIVE_ACCOUNT"

    # 13. Kích hoạt lại
    kh = await client.post(
        f"/api/v1/users/{nv_id}/reactivate", headers=_bearer(admin_token)
    )
    assert kh.status_code == 200
    assert kh.json()["is_active"] is True

    # 14. Nhật ký ghi nhận đủ mọi thao tác
    nk = await client.get("/api/v1/audit-logs", headers=_bearer(admin_token))
    hanh_dong = {e["action"] for e in nk.json()["items"]}
    assert {
        "department.created",
        "user.created",
        "user.deactivated",
        "user.reactivated",
        "auth.login_succeeded",
        "user.password_changed",
    } <= hanh_dong


async def test_khong_bao_gio_lo_hash_mat_khau_qua_api(
    client: AsyncClient, engine: AsyncEngine
) -> None:
    """Quét mọi phản hồi để chắc chắn không có chuỗi hash nào lọt ra."""
    await _tao_admin(engine)
    dn = await client.post(
        "/api/v1/auth/login",
        json={"email": "admin@congty.vn", "password": MAT_KHAU_ADMIN},
    )
    token = dn.json()["access_token"]

    phong = await client.post(
        "/api/v1/departments", json={"name": "Phòng A"}, headers=_bearer(token)
    )
    tao = await client.post(
        "/api/v1/users",
        json={
            "email": "x@congty.vn",
            "full_name": "Người X",
            "role": "STAFF",
            "department_id": phong.json()["id"],
            "password": MAT_KHAU_TAM,
        },
        headers=_bearer(token),
    )

    cac_phan_hoi = [
        dn.text,
        phong.text,
        tao.text,
        (await client.get("/api/v1/auth/me", headers=_bearer(token))).text,
        (await client.get("/api/v1/users", headers=_bearer(token))).text,
        (await client.get("/api/v1/audit-logs", headers=_bearer(token))).text,
    ]

    for noi_dung in cac_phan_hoi:
        assert "$2b$" not in noi_dung
        assert "password_hash" not in noi_dung
        assert MAT_KHAU_TAM not in noi_dung
        assert MAT_KHAU_ADMIN not in noi_dung
```

- [ ] **Step 2: Chạy test luồng hoàn chỉnh**

```bash
cd backend
uv run pytest tests/e2e/test_luong_hoan_chinh.py -v
```

Expected: `2 passed`.

- [ ] **Step 3: Viết `.github/workflows/backend-ci.yml`**

```yaml
name: Backend CI

on:
  push:
    branches: [main]
    paths: ["backend/**", ".github/workflows/backend-ci.yml"]
  pull_request:
    paths: ["backend/**", ".github/workflows/backend-ci.yml"]

jobs:
  kiem-tra:
    runs-on: ubuntu-latest

    services:
      postgres:
        image: postgres:17
        env:
          POSTGRES_USER: postgres
          POSTGRES_PASSWORD: postgres
          POSTGRES_DB: omnichat_test
        ports: ["5432:5432"]
        options: >-
          --health-cmd pg_isready
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5

    env:
      DATABASE_URL: postgresql+psycopg://postgres:postgres@localhost:5432/omnichat_test
      TEST_DATABASE_URL: postgresql+psycopg://postgres:postgres@localhost:5432/omnichat_test
      JWT_SECRET_KEY: khoa-chi-dung-trong-ci-khong-phai-khoa-that
      APP_ENV: ci

    defaults:
      run:
        working-directory: backend

    steps:
      - uses: actions/checkout@v4

      - name: Cài uv
        uses: astral-sh/setup-uv@v5
        with:
          enable-cache: true

      - name: Cài dependency
        run: uv sync --locked

      - name: Kiểm tra định dạng mã
        run: uv run ruff format --check .

      - name: Kiểm tra lỗi tĩnh
        run: uv run ruff check .

      - name: Kiểm tra kiểu dữ liệu
        run: uv run mypy src

      - name: Kiểm tra dependency rule của clean architecture
        run: uv run lint-imports

      - name: Áp migration
        run: uv run alembic upgrade head

      - name: Test đơn vị
        run: uv run pytest tests/unit -v

      - name: Test tích hợp
        run: uv run pytest tests/integration -v

      - name: Test đầu-cuối
        run: uv run pytest tests/e2e -v

      - name: Đo độ phủ tầng nghiệp vụ
        run: |
          uv run pytest tests/unit \
            --cov=src/modules/identity/domain \
            --cov=src/modules/identity/application \
            --cov=src/shared/domain \
            --cov-report=term-missing \
            --cov-fail-under=90
```

**Vì sao đo độ phủ riêng cho tầng nghiệp vụ:** đo trên toàn bộ mã nguồn sẽ trộn lẫn logic nghiệp vụ với mã ghép nối. Đặt ngưỡng 90% cho `domain` và `application` là đặt ngưỡng đúng chỗ cần.

- [ ] **Step 4: Viết `backend/Dockerfile`**

```dockerfile
# syntax=docker/dockerfile:1

FROM python:3.13-slim AS builder

COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

WORKDIR /app

# Cài dependency trước, tách khỏi mã nguồn để tận dụng cache của Docker.
COPY pyproject.toml uv.lock ./
RUN uv sync --locked --no-dev --no-install-project

COPY . .
RUN uv sync --locked --no-dev

FROM python:3.13-slim AS runtime

# Chạy bằng người dùng thường, không phải root.
RUN useradd --create-home --uid 1000 omnichat

WORKDIR /app
COPY --from=builder --chown=omnichat:omnichat /app /app

ENV PATH="/app/.venv/bin:$PATH" \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

USER omnichat
EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')"

CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

**Lưu ý:** máy phát triển không có Docker. Dockerfile này phục vụ triển khai lên cloud sau này, không bắt buộc chạy được ở môi trường cục bộ. Nếu chưa có Docker thì bỏ qua bước dựng ảnh.

- [ ] **Step 5: Viết `backend/.dockerignore`**

```
.venv/
__pycache__/
*.py[cod]
.pytest_cache/
.mypy_cache/
.ruff_cache/
.coverage
htmlcov/
.env
tests/
.git/
```

- [ ] **Step 6: Bổ sung `backend/README.md`**

Thêm vào cuối file:

````markdown
## Tạo quản trị viên đầu tiên

Hệ thống không có đăng ký công khai. Sau khi áp migration, chạy:

```bash
uv run python -m scripts.seed_admin
```

## Chạy ứng dụng

```bash
uv run uvicorn src.main:app --reload
```

Tài liệu API: http://localhost:8000/docs

## Migration

```bash
uv run alembic upgrade head                      # áp migration mới nhất
uv run alembic revision --autogenerate -m "mô tả"  # sinh migration mới
uv run alembic downgrade -1                      # lùi một bước
```

## Kiến trúc

Clean Architecture tổ chức theo module dọc. Quy tắc phụ thuộc:

```
presentation → application → domain
                    ↑            ↑
                    └ infrastructure ┘
```

`domain/` chỉ import thư viện chuẩn. `import-linter` kiểm tra quy tắc này trong
CI — nếu vi phạm, pipeline sẽ đỏ.

## Giới hạn đã biết

- **Thu hồi quyền có độ trễ tối đa 15 phút.** Vô hiệu hoá tài khoản thu hồi
  refresh token ngay, nhưng access token đang lưu hành vẫn hợp lệ tới khi hết
  hạn.
- **Rate limit chỉ đúng khi chạy một bản sao.** Bộ đếm nằm trong bộ nhớ tiến
  trình; khi mở rộng nhiều bản sao phải chuyển sang Redis.
````

- [ ] **Step 7: Chạy toàn bộ kiểm tra lần cuối**

```bash
cd backend
uv run ruff format --check .
uv run ruff check .
uv run mypy src
uv run lint-imports
uv run pytest -v
```

Expected: toàn bộ xanh, `Contracts: 3 kept, 0 broken.`

- [ ] **Step 8: Đo độ phủ**

```bash
uv run pytest tests/unit \
  --cov=src/modules/identity/domain \
  --cov=src/modules/identity/application \
  --cov=src/shared/domain \
  --cov-report=term-missing
```

Expected: ≥ 90%.

- [ ] **Step 9: Commit**

```bash
git add .github/workflows/backend-ci.yml backend/Dockerfile backend/.dockerignore \
        backend/README.md backend/tests/e2e/test_luong_hoan_chinh.py
git commit -m "ci: add backend pipeline, dockerfile, and full lifecycle test"
```

---

## Hoàn tất Foundation

Sau Task 20, sub-project #0 đạt đủ tiêu chí thành công nêu trong spec:

1. Quản trị viên đăng nhập, tạo phòng ban, tạo quản lý và nhân viên — kiểm chứng bởi `test_vong_doi_day_du_cua_he_thong`.
2. Quản lý chỉ truy cập được dữ liệu phòng mình — kiểm chứng bởi `test_manager_chi_thay_nhan_vien_phong_minh`.
3. Nhân viên không gọi được endpoint quản trị — kiểm chứng bởi `test_staff_khong_goi_duoc_endpoint_quan_tri`.
4. Mọi thay đổi người dùng để lại bản ghi nhật ký — kiểm chứng bởi `test_moi_thao_tac_deu_de_lai_ban_ghi`.
5. `import-linter` xác nhận dependency rule — chạy trong CI.
6. Test ba tầng xanh trong CI.

**Chưa đạt và không thuộc phạm vi #0:** yêu cầu 1000 người dùng đồng thời chưa được kiểm chứng vì Foundation không có tải thực; yêu cầu uptime 99,5% phụ thuộc hạ tầng cloud chưa chọn.

**Bước tiếp theo:** brainstorm sub-project #1 Omnichannel Inbox. Trước khi bắt đầu, cần xác định rõ credential Zalo OA và Meta: loại ứng dụng đã đăng ký, các quyền đã được cấp, và trạng thái xác minh — xem phần rủi ro trong [roadmap](../specs/2026-07-21-omnichat-roadmap.md).
