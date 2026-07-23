from datetime import UTC, datetime

from src.modules.identity.domain.entities.audit_log import AuditAction, AuditLog
from src.shared.domain.identifiers import new_id

BAY_GIO = datetime(2026, 7, 21, 10, 0, tzinfo=UTC)


def test_ghi_nhan_hanh_dong_kem_day_du_thong_tin() -> None:
    actor_id = new_id()
    resource_id = new_id()

    ban_ghi = AuditLog.record(
        action=AuditAction.USER_CREATED,
        actor_id=actor_id,
        resource_type="user",
        resource_id=str(resource_id),
        now=BAY_GIO,
        changes={"email": "moi@congty.vn"},
        ip_address="10.0.0.1",
    )

    assert ban_ghi.action is AuditAction.USER_CREATED
    assert ban_ghi.actor_id == actor_id
    assert ban_ghi.resource_type == "user"
    assert ban_ghi.resource_id == str(resource_id)
    assert ban_ghi.changes == {"email": "moi@congty.vn"}
    assert ban_ghi.ip_address == "10.0.0.1"
    assert ban_ghi.created_at == BAY_GIO


def test_hanh_dong_cua_he_thong_khong_can_actor() -> None:
    ban_ghi = AuditLog.record(
        action=AuditAction.AUTH_LOGIN_FAILED,
        actor_id=None,
        resource_type="auth",
        resource_id=None,
        now=BAY_GIO,
    )

    assert ban_ghi.actor_id is None
    assert ban_ghi.resource_id is None


def test_audit_log_khong_co_phuong_thuc_sua_hay_xoa() -> None:
    """Nhật ký chỉ được ghi thêm — đó là điều làm nó đáng tin cậy."""
    ten_phuong_thuc = {t for t in dir(AuditLog) if not t.startswith("_")}

    assert not ten_phuong_thuc & {"update", "modify", "delete", "edit"}


def test_moi_hanh_dong_deu_co_ma_dang_chu_thuong_gach_cham() -> None:
    for hanh_dong in AuditAction:
        assert hanh_dong.value.islower()
        assert "." in hanh_dong.value
