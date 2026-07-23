from datetime import UTC, datetime, timedelta

import pytest

from src.modules.identity.application.ports import (
    ExpiredTokenError,
    InvalidTokenError,
)
from src.modules.identity.domain.value_objects.role import Role
from src.modules.identity.infrastructure.security.password_hasher import (
    BcryptPasswordHasher,
)
from src.modules.identity.infrastructure.security.token_service import JwtTokenService
from src.shared.domain.identifiers import new_id
from tests.unit.identity.fakes import FakeClock

KHOA_BI_MAT = "khoa-bi-mat-chi-dung-cho-test-khong-dung-that"
BAY_GIO = datetime(2026, 7, 21, 10, 0, tzinfo=UTC)


class TestBamMatKhau:
    def test_bam_roi_kiem_tra_lai_dung(self) -> None:
        hasher = BcryptPasswordHasher()
        chuoi_hash = hasher.hash("MatKhauCuaToi123")

        assert hasher.verify("MatKhauCuaToi123", chuoi_hash) is True

    def test_mat_khau_sai_bi_tu_choi(self) -> None:
        hasher = BcryptPasswordHasher()
        chuoi_hash = hasher.hash("MatKhauDung123")

        assert hasher.verify("MatKhauSai123", chuoi_hash) is False

    def test_hai_lan_bam_cung_mat_khau_cho_hai_hash_khac_nhau(self) -> None:
        """Bcrypt tự sinh salt ngẫu nhiên, nên hash khác nhau là đúng."""
        hasher = BcryptPasswordHasher()

        assert hasher.hash("GiongNhau123") != hasher.hash("GiongNhau123")

    def test_hash_khong_chua_mat_khau_goc(self) -> None:
        hasher = BcryptPasswordHasher()

        assert "MatKhauLoRa" not in hasher.hash("MatKhauLoRa")

    def test_hash_sai_dinh_dang_thi_tra_ve_false_chu_khong_no(self) -> None:
        """Chuỗi hash hỏng trong cơ sở dữ liệu không được làm sập đăng nhập."""
        hasher = BcryptPasswordHasher()

        assert hasher.verify("bat_ky", "khong-phai-hash-bcrypt") is False

    def test_mat_khau_dai_hon_72_byte_van_bam_duoc(self) -> None:
        """Bcrypt ném ValueError với đầu vào quá 72 byte nếu không rút gọn trước."""
        hasher = BcryptPasswordHasher()
        rat_dai = "a" * 200

        assert hasher.verify(rat_dai, hasher.hash(rat_dai)) is True

    def test_mat_khau_tieng_viet_co_dau_bam_duoc(self) -> None:
        """Ký tự tiếng Việt chiếm nhiều byte — 140 ký tự có thể thành 195 byte."""
        hasher = BcryptPasswordHasher()
        tieng_viet = "Mật khẩu tiếng Việt rất dài " * 5

        assert hasher.verify(tieng_viet, hasher.hash(tieng_viet)) is True

    def test_hai_mat_khau_dai_khac_nhau_khong_bi_coi_la_giong_nhau(self) -> None:
        """Nếu cắt thô ở 72 byte, hai mật khẩu này sẽ trùng nhau — lỗ hổng thật."""
        hasher = BcryptPasswordHasher()
        chung = "x" * 80
        chuoi_hash = hasher.hash(chung + "phan_duoi_A")

        assert hasher.verify(chung + "phan_duoi_B", chuoi_hash) is False


class TestAccessToken:
    def _dich_vu(self, clock: FakeClock | None = None) -> JwtTokenService:
        return JwtTokenService(
            secret_key=KHOA_BI_MAT,
            algorithm="HS256",
            access_token_expire_minutes=15,
            clock=clock or FakeClock(BAY_GIO),
        )

    def test_tao_roi_giai_ma_lay_lai_dung_thong_tin(self) -> None:
        dich_vu = self._dich_vu()
        user_id = new_id()
        phong_id = new_id()

        token = dich_vu.create_access_token(user_id, Role.MANAGER, phong_id)
        payload = dich_vu.decode_access_token(token)

        assert payload.user_id == user_id
        assert payload.role is Role.MANAGER
        assert payload.department_id == phong_id

    def test_admin_khong_co_phong_ban_trong_token(self) -> None:
        dich_vu = self._dich_vu()

        token = dich_vu.create_access_token(new_id(), Role.ADMIN, None)

        assert dich_vu.decode_access_token(token).department_id is None

    def test_token_het_han_bi_tu_choi(self) -> None:
        dong_ho = FakeClock(BAY_GIO)
        dich_vu = self._dich_vu(dong_ho)
        token = dich_vu.create_access_token(new_id(), Role.STAFF, new_id())

        dong_ho.advance(minutes=16)

        with pytest.raises(ExpiredTokenError):
            dich_vu.decode_access_token(token)

    def test_token_con_han_thi_chap_nhan(self) -> None:
        dong_ho = FakeClock(BAY_GIO)
        dich_vu = self._dich_vu(dong_ho)
        token = dich_vu.create_access_token(new_id(), Role.STAFF, new_id())

        dong_ho.advance(minutes=14)

        assert dich_vu.decode_access_token(token) is not None

    def test_token_bi_sua_doi_bi_tu_choi(self) -> None:
        dich_vu = self._dich_vu()
        token = dich_vu.create_access_token(new_id(), Role.STAFF, new_id())

        bi_sua = token[:-4] + "xxxx"

        with pytest.raises(InvalidTokenError):
            dich_vu.decode_access_token(bi_sua)

    def test_token_ky_bang_khoa_khac_bi_tu_choi(self) -> None:
        """Đây là điều ngăn kẻ tấn công tự cấp token cho mình."""
        ke_tan_cong = JwtTokenService(
            secret_key="khoa-khac-hoan-toan",
            algorithm="HS256",
            access_token_expire_minutes=15,
            clock=FakeClock(BAY_GIO),
        )
        token_gia = ke_tan_cong.create_access_token(new_id(), Role.ADMIN, None)

        with pytest.raises(InvalidTokenError):
            self._dich_vu().decode_access_token(token_gia)

    @pytest.mark.parametrize("rac", ["", "khong-phai-jwt", "a.b.c", "..."])
    def test_chuoi_rac_bi_tu_choi(self, rac: str) -> None:
        with pytest.raises(InvalidTokenError):
            self._dich_vu().decode_access_token(rac)

    def test_token_dung_chu_ky_nhung_sai_cau_truc_bi_tu_choi(self) -> None:
        """Token ký đúng khoá nhưng ``sub`` không phải UUID hợp lệ. Đây là
        đường phòng thủ cuối: kẻ có được khoá bí mật, hoặc một dịch vụ lệch
        phiên bản, có thể sinh token ký đúng nhưng payload sai cấu trúc — phải
        trả về ``InvalidTokenError`` chứ không để lỗi 500 lọt ra ngoài."""
        import jwt

        het_han = int((BAY_GIO + timedelta(minutes=15)).timestamp())
        token = jwt.encode(
            {
                "sub": "khong-phai-uuid",
                "role": "STAFF",
                "dept": None,
                "iat": int(BAY_GIO.timestamp()),
                "exp": het_han,
            },
            KHOA_BI_MAT,
            algorithm="HS256",
        )

        with pytest.raises(InvalidTokenError):
            self._dich_vu().decode_access_token(token)

    def test_thoi_diem_het_han_dung_bang_15_phut(self) -> None:
        dich_vu = self._dich_vu()

        token = dich_vu.create_access_token(new_id(), Role.STAFF, new_id())

        payload = dich_vu.decode_access_token(token)
        assert payload.expires_at == BAY_GIO + timedelta(minutes=15)


class TestRefreshToken:
    def _dich_vu(self) -> JwtTokenService:
        return JwtTokenService(
            secret_key=KHOA_BI_MAT,
            algorithm="HS256",
            access_token_expire_minutes=15,
            clock=FakeClock(BAY_GIO),
        )

    def test_moi_lan_tao_cho_mot_token_khac_nhau(self) -> None:
        dich_vu = self._dich_vu()

        tho_1, _ = dich_vu.create_refresh_token()
        tho_2, _ = dich_vu.create_refresh_token()

        assert tho_1 != tho_2

    def test_hash_tra_ve_khop_voi_ham_bam(self) -> None:
        dich_vu = self._dich_vu()

        tho, chuoi_hash = dich_vu.create_refresh_token()

        assert dich_vu.hash_refresh_token(tho) == chuoi_hash

    def test_hash_khong_chua_token_goc(self) -> None:
        """Cơ sở dữ liệu chỉ lưu hash — đọc được bảng cũng không mạo danh được."""
        dich_vu = self._dich_vu()

        tho, chuoi_hash = dich_vu.create_refresh_token()

        assert tho not in chuoi_hash

    def test_bam_cung_mot_token_luon_cho_cung_ket_qua(self) -> None:
        dich_vu = self._dich_vu()
        tho, _ = dich_vu.create_refresh_token()

        assert dich_vu.hash_refresh_token(tho) == dich_vu.hash_refresh_token(tho)

    def test_token_du_dai_de_khong_the_doan(self) -> None:
        tho, _ = self._dich_vu().create_refresh_token()

        assert len(tho) >= 32
