"""Mapper phải giữ nguyên dữ liệu qua cả hai chiều chuyển đổi."""

from datetime import UTC, datetime

from src.modules.identity.domain.entities.audit_log import AuditAction, AuditLog
from src.modules.identity.domain.entities.department import Department
from src.modules.identity.domain.entities.refresh_token import RefreshToken
from src.modules.identity.domain.entities.user import User
from src.modules.identity.domain.value_objects.email import Email
from src.modules.identity.domain.value_objects.password_hash import PasswordHash
from src.modules.identity.domain.value_objects.role import Role
from src.modules.identity.infrastructure.mappers.audit_log_mapper import AuditLogMapper
from src.modules.identity.infrastructure.mappers.department_mapper import (
    DepartmentMapper,
)
from src.modules.identity.infrastructure.mappers.refresh_token_mapper import (
    RefreshTokenMapper,
)
from src.modules.identity.infrastructure.mappers.user_mapper import UserMapper
from src.shared.domain.identifiers import new_id

BAY_GIO = datetime(2026, 7, 21, 10, 0, tzinfo=UTC)
SAU_DO = datetime(2026, 7, 21, 11, 0, tzinfo=UTC)
PHONG_A = new_id()


class TestDepartmentMapper:
    def test_chuyen_hai_chieu_khong_mat_du_lieu(self) -> None:
        goc = Department.create(name="Kinh doanh", description="Mô tả", now=BAY_GIO)

        quay_lai = DepartmentMapper.to_domain(DepartmentMapper.to_model(goc))

        assert quay_lai.id == goc.id
        assert quay_lai.name == goc.name
        assert quay_lai.description == goc.description
        assert quay_lai.is_active == goc.is_active
        assert quay_lai.created_at == goc.created_at
        assert quay_lai.updated_at == goc.updated_at

    def test_update_model_ghi_de_len_model_dang_co(self) -> None:
        goc = Department.create(name="Cũ", description=None, now=BAY_GIO)
        model = DepartmentMapper.to_model(goc)
        goc.rename("Mới", now=SAU_DO)

        DepartmentMapper.update_model(model, goc)

        assert model.name == "Mới"
        assert model.updated_at == SAU_DO
        assert model.id == goc.id


class TestUserMapper:
    def _user(self, role: Role = Role.STAFF) -> User:
        return User.create(
            email=Email("nhanvien@congty.vn"),
            password_hash=PasswordHash("$2b$12$hash"),
            full_name="Nguyễn Văn A",
            role=role,
            department_id=PHONG_A if role.requires_department() else None,
            now=BAY_GIO,
            phone="0900000000",
        )

    def test_chuyen_hai_chieu_khong_mat_du_lieu(self) -> None:
        goc = self._user()

        quay_lai = UserMapper.to_domain(UserMapper.to_model(goc))

        assert quay_lai.id == goc.id
        assert quay_lai.email == goc.email
        assert quay_lai.password_hash == goc.password_hash
        assert quay_lai.full_name == goc.full_name
        assert quay_lai.phone == goc.phone
        assert quay_lai.role is goc.role
        assert quay_lai.department_id == goc.department_id
        assert quay_lai.is_active == goc.is_active
        assert quay_lai.must_change_password == goc.must_change_password
        assert quay_lai.last_login_at == goc.last_login_at

    def test_vai_tro_luu_thanh_chuoi_va_doc_lai_thanh_enum(self) -> None:
        model = UserMapper.to_model(self._user(Role.MANAGER))

        assert model.role == "MANAGER"
        assert isinstance(model.role, str)
        assert UserMapper.to_domain(model).role is Role.MANAGER

    def test_email_luu_duoi_dang_chuoi(self) -> None:
        model = UserMapper.to_model(self._user())

        assert model.email == "nhanvien@congty.vn"

    def test_admin_khong_co_phong_ban(self) -> None:
        model = UserMapper.to_model(self._user(Role.ADMIN))

        assert model.department_id is None
        assert UserMapper.to_domain(model).department_id is None

    def test_giu_nguyen_moc_dang_nhap_gan_nhat(self) -> None:
        goc = self._user()
        goc.record_login(now=SAU_DO)

        assert UserMapper.to_domain(UserMapper.to_model(goc)).last_login_at == SAU_DO


class TestRefreshTokenMapper:
    def test_chuyen_hai_chieu_khong_mat_du_lieu(self) -> None:
        goc = RefreshToken.issue(
            user_id=new_id(),
            token_hash="hash_gia_lap",
            expires_at=SAU_DO,
            now=BAY_GIO,
            user_agent="Chrome",
            ip_address="10.0.0.1",
        )

        quay_lai = RefreshTokenMapper.to_domain(RefreshTokenMapper.to_model(goc))

        assert quay_lai.id == goc.id
        assert quay_lai.user_id == goc.user_id
        assert quay_lai.token_hash == goc.token_hash
        assert quay_lai.expires_at == goc.expires_at
        assert quay_lai.user_agent == goc.user_agent
        assert quay_lai.ip_address == goc.ip_address

    def test_giu_nguyen_trang_thai_da_xoay(self) -> None:
        goc = RefreshToken.issue(new_id(), "h", SAU_DO, BAY_GIO)
        ma_moi = new_id()
        goc.rotate_to(ma_moi, now=SAU_DO)

        quay_lai = RefreshTokenMapper.to_domain(RefreshTokenMapper.to_model(goc))

        assert quay_lai.revoked_at == SAU_DO
        assert quay_lai.replaced_by_id == ma_moi
        assert quay_lai.is_revoked() is True


class TestAuditLogMapper:
    def test_chuyen_hai_chieu_khong_mat_du_lieu(self) -> None:
        goc = AuditLog.record(
            action=AuditAction.USER_ROLE_CHANGED,
            actor_id=new_id(),
            resource_type="user",
            resource_id="abc",
            now=BAY_GIO,
            changes={"role": {"truoc": "STAFF", "sau": "MANAGER"}},
            ip_address="10.0.0.1",
            user_agent="Chrome",
        )

        quay_lai = AuditLogMapper.to_domain(AuditLogMapper.to_model(goc))

        assert quay_lai.action is AuditAction.USER_ROLE_CHANGED
        assert quay_lai.actor_id == goc.actor_id
        assert quay_lai.resource_type == goc.resource_type
        assert quay_lai.resource_id == goc.resource_id
        assert quay_lai.changes == goc.changes
        assert quay_lai.created_at == goc.created_at

    def test_hanh_dong_luu_thanh_chuoi(self) -> None:
        goc = AuditLog.record(
            action=AuditAction.AUTH_LOGIN_FAILED,
            actor_id=None,
            resource_type="auth",
            resource_id=None,
            now=BAY_GIO,
        )

        assert AuditLogMapper.to_model(goc).action == "auth.login_failed"
