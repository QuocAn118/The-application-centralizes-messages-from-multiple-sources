"""Repository giả lập trong bộ nhớ, dùng cho unit test use case.

Fake phản ánh hành vi thật của repository; thư viện mock chỉ phản ánh giả định
của người viết test. Khi hành vi thật thay đổi, fake sai sẽ làm test đỏ — mock
thì không.
"""

from datetime import UTC, datetime
from uuid import UUID

from src.modules.identity.domain.entities.audit_log import AuditAction, AuditLog
from src.modules.identity.domain.entities.department import Department
from src.modules.identity.domain.entities.refresh_token import RefreshToken
from src.modules.identity.domain.entities.user import User
from src.modules.identity.domain.value_objects.email import Email
from src.modules.identity.domain.value_objects.role import Role


class FakeClock:
    """Đồng hồ do test điều khiển."""

    def __init__(self, now: datetime | None = None) -> None:
        self._now = now or datetime(2026, 7, 21, 10, 0, tzinfo=UTC)

    def now(self) -> datetime:
        return self._now

    def advance(self, **khoang_thoi_gian: float) -> None:
        from datetime import timedelta

        self._now += timedelta(**khoang_thoi_gian)


class FakeUserRepository:
    """Lưu người dùng trong một dict."""

    def __init__(self, users: list[User] | None = None) -> None:
        self._users: dict[UUID, User] = {u.id: u for u in (users or [])}

    async def get_by_id(self, user_id: UUID) -> User | None:
        return self._users.get(user_id)

    async def get_by_email(self, email: Email) -> User | None:
        for user in self._users.values():
            if user.email == email:
                return user
        return None

    async def add(self, user: User) -> None:
        self._users[user.id] = user

    async def update(self, user: User) -> None:
        self._users[user.id] = user

    def _loc(
        self,
        department_id: UUID | None,
        role: Role | None,
        is_active: bool | None,
        search: str | None,
    ) -> list[User]:
        ket_qua = list(self._users.values())
        if department_id is not None:
            ket_qua = [u for u in ket_qua if u.department_id == department_id]
        if role is not None:
            ket_qua = [u for u in ket_qua if u.role is role]
        if is_active is not None:
            ket_qua = [u for u in ket_qua if u.is_active is is_active]
        if search:
            tu_khoa = search.lower()
            ket_qua = [
                u
                for u in ket_qua
                if tu_khoa in u.full_name.lower() or tu_khoa in u.email.value
            ]
        return sorted(ket_qua, key=lambda u: u.created_at)

    async def list_users(
        self,
        department_id: UUID | None = None,
        role: Role | None = None,
        is_active: bool | None = None,
        search: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[User]:
        return self._loc(department_id, role, is_active, search)[offset : offset + limit]

    async def count_users(
        self,
        department_id: UUID | None = None,
        role: Role | None = None,
        is_active: bool | None = None,
        search: str | None = None,
    ) -> int:
        return len(self._loc(department_id, role, is_active, search))

    async def count_active_in_department(self, department_id: UUID) -> int:
        return len(
            [
                u
                for u in self._users.values()
                if u.department_id == department_id and u.is_active
            ]
        )

    async def has_active_manager(
        self, department_id: UUID, exclude_user_id: UUID | None = None
    ) -> bool:
        return any(
            u.department_id == department_id
            and u.role is Role.MANAGER
            and u.is_active
            and u.id != exclude_user_id
            for u in self._users.values()
        )

    async def count_active_admins(self) -> int:
        return len(
            [u for u in self._users.values() if u.role is Role.ADMIN and u.is_active]
        )


class FakeDepartmentRepository:
    """Lưu phòng ban trong một dict."""

    def __init__(self, departments: list[Department] | None = None) -> None:
        self._departments: dict[UUID, Department] = {
            d.id: d for d in (departments or [])
        }

    async def get_by_id(self, department_id: UUID) -> Department | None:
        return self._departments.get(department_id)

    async def get_by_name(self, name: str) -> Department | None:
        for phong in self._departments.values():
            if phong.name.lower() == name.strip().lower() and phong.is_active:
                return phong
        return None

    async def add(self, department: Department) -> None:
        self._departments[department.id] = department

    async def update(self, department: Department) -> None:
        self._departments[department.id] = department

    async def list_departments(
        self,
        is_active: bool | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[Department]:
        ket_qua = list(self._departments.values())
        if is_active is not None:
            ket_qua = [d for d in ket_qua if d.is_active is is_active]
        ket_qua.sort(key=lambda d: d.name)
        return ket_qua[offset : offset + limit]

    async def count_departments(self, is_active: bool | None = None) -> int:
        ket_qua = list(self._departments.values())
        if is_active is not None:
            ket_qua = [d for d in ket_qua if d.is_active is is_active]
        return len(ket_qua)


class FakeRefreshTokenRepository:
    """Lưu refresh token trong một dict."""

    def __init__(self) -> None:
        self._tokens: dict[UUID, RefreshToken] = {}

    async def get_by_hash(self, token_hash: str) -> RefreshToken | None:
        for token in self._tokens.values():
            if token.token_hash == token_hash:
                return token
        return None

    async def add(self, token: RefreshToken) -> None:
        self._tokens[token.id] = token

    async def update(self, token: RefreshToken) -> None:
        self._tokens[token.id] = token

    async def revoke_all_for_user(self, user_id: UUID, now: datetime) -> None:
        for token in self._tokens.values():
            if token.user_id == user_id and not token.is_revoked():
                token.revoke(now)

    async def revoke_chain(self, token: RefreshToken, now: datetime) -> None:
        hien_tai: RefreshToken | None = token
        da_duyet: set[UUID] = set()
        while hien_tai is not None and hien_tai.id not in da_duyet:
            da_duyet.add(hien_tai.id)
            hien_tai.revoke(now)
            ke_tiep_id = hien_tai.replaced_by_id
            hien_tai = self._tokens.get(ke_tiep_id) if ke_tiep_id else None


class FakeAuditLogRepository:
    """Lưu bản ghi nhật ký trong một danh sách."""

    def __init__(self) -> None:
        self.entries: list[AuditLog] = []

    async def add(self, entry: AuditLog) -> None:
        self.entries.append(entry)

    def _loc(
        self,
        actor_id: UUID | None,
        action: AuditAction | None,
        resource_type: str | None,
        from_time: datetime | None,
        to_time: datetime | None,
    ) -> list[AuditLog]:
        ket_qua = list(self.entries)
        if actor_id is not None:
            ket_qua = [e for e in ket_qua if e.actor_id == actor_id]
        if action is not None:
            ket_qua = [e for e in ket_qua if e.action is action]
        if resource_type is not None:
            ket_qua = [e for e in ket_qua if e.resource_type == resource_type]
        if from_time is not None:
            ket_qua = [e for e in ket_qua if e.created_at >= from_time]
        if to_time is not None:
            ket_qua = [e for e in ket_qua if e.created_at <= to_time]
        return sorted(ket_qua, key=lambda e: e.created_at, reverse=True)

    async def list_entries(
        self,
        actor_id: UUID | None = None,
        action: AuditAction | None = None,
        resource_type: str | None = None,
        from_time: datetime | None = None,
        to_time: datetime | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[AuditLog]:
        ket_qua = self._loc(actor_id, action, resource_type, from_time, to_time)
        return ket_qua[offset : offset + limit]

    async def count_entries(
        self,
        actor_id: UUID | None = None,
        action: AuditAction | None = None,
        resource_type: str | None = None,
        from_time: datetime | None = None,
        to_time: datetime | None = None,
    ) -> int:
        return len(self._loc(actor_id, action, resource_type, from_time, to_time))
