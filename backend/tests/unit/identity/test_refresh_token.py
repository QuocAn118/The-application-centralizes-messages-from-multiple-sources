from datetime import UTC, datetime, timedelta

from src.modules.identity.domain.entities.refresh_token import RefreshToken
from src.shared.domain.identifiers import new_id

BAY_GIO = datetime(2026, 7, 21, 10, 0, tzinfo=UTC)
USER_ID = new_id()


def _cap_token(het_han_sau: timedelta = timedelta(days=7)) -> RefreshToken:
    return RefreshToken.issue(
        user_id=USER_ID,
        token_hash="hash_gia_lap",
        expires_at=BAY_GIO + het_han_sau,
        now=BAY_GIO,
    )


class TestCapToken:
    def test_token_moi_con_hieu_luc(self) -> None:
        token = _cap_token()

        assert token.is_valid(now=BAY_GIO) is True
        assert token.is_revoked() is False
        assert token.revoked_at is None
        assert token.replaced_by_id is None


class TestHetHan:
    def test_token_het_han_thi_khong_con_hieu_luc(self) -> None:
        token = _cap_token(het_han_sau=timedelta(days=7))
        sau_khi_het_han = BAY_GIO + timedelta(days=8)

        assert token.is_expired(now=sau_khi_het_han) is True
        assert token.is_valid(now=sau_khi_het_han) is False

    def test_dung_thoi_diem_het_han_thi_coi_la_het_han(self) -> None:
        token = _cap_token(het_han_sau=timedelta(days=7))
        dung_luc_het_han = BAY_GIO + timedelta(days=7)

        assert token.is_expired(now=dung_luc_het_han) is True


class TestThuHoi:
    def test_thu_hoi_lam_token_mat_hieu_luc(self) -> None:
        token = _cap_token()
        luc_thu_hoi = BAY_GIO + timedelta(hours=1)

        token.revoke(now=luc_thu_hoi)

        assert token.is_revoked() is True
        assert token.is_valid(now=luc_thu_hoi) is False
        assert token.revoked_at == luc_thu_hoi

    def test_thu_hoi_lan_hai_khong_doi_moc_thoi_gian(self) -> None:
        token = _cap_token()
        lan_dau = BAY_GIO + timedelta(hours=1)
        lan_hai = BAY_GIO + timedelta(hours=2)

        token.revoke(now=lan_dau)
        token.revoke(now=lan_hai)

        assert token.revoked_at == lan_dau


class TestXoayToken:
    def test_xoay_token_thu_hoi_ban_cu_va_ghi_lai_ban_moi(self) -> None:
        token = _cap_token()
        token_moi_id = new_id()
        luc_xoay = BAY_GIO + timedelta(hours=1)

        token.rotate_to(new_token_id=token_moi_id, now=luc_xoay)

        assert token.is_revoked() is True
        assert token.replaced_by_id == token_moi_id
        assert token.revoked_at == luc_xoay

    def test_token_da_xoay_thi_khong_con_hieu_luc(self) -> None:
        token = _cap_token()

        token.rotate_to(new_token_id=new_id(), now=BAY_GIO)

        assert token.is_valid(now=BAY_GIO) is False
