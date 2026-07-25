from pathlib import Path

import pytest
from cryptography.fernet import Fernet

from src.modules.inbox.domain.ports import IAttachmentStore, ICredentialCipher
from src.modules.inbox.infrastructure.attachments.local_store import (
    LocalAttachmentStore,
    _lam_sach_ten,
)
from src.modules.inbox.infrastructure.security.fernet_cipher import (
    FernetCredentialCipher,
    InvalidCipherKeyError,
)


def test_khop_hop_dong_port() -> None:
    _cipher: ICredentialCipher = FernetCredentialCipher(Fernet.generate_key().decode())
    _store: IAttachmentStore = LocalAttachmentStore("var/x")
    assert _cipher is not None
    assert _store is not None


class TestFernetCipher:
    def test_ma_hoa_roi_giai_ma_ra_lai_goc(self) -> None:
        cipher = FernetCredentialCipher(Fernet.generate_key().decode())
        goc = "zalo-oa-token-bi-mat-123"

        ma = cipher.encrypt(goc)
        assert ma != goc
        assert cipher.decrypt(ma) == goc

    def test_ban_ma_khac_nhau_moi_lan(self) -> None:
        """Fernet nhúng IV ngẫu nhiên nên cùng plaintext ra ciphertext khác nhau."""
        cipher = FernetCredentialCipher(Fernet.generate_key().decode())

        assert cipher.encrypt("x") != cipher.encrypt("x")

    def test_khoa_sai_dinh_dang_bi_tu_choi(self) -> None:
        with pytest.raises(InvalidCipherKeyError):
            FernetCredentialCipher("khong-phai-khoa-fernet")

    def test_giai_ma_bang_khoa_khac_that_bai(self) -> None:
        ma = FernetCredentialCipher(Fernet.generate_key().decode()).encrypt("x")
        khac = FernetCredentialCipher(Fernet.generate_key().decode())

        with pytest.raises(Exception):  # noqa: B017  InvalidToken
            khac.decrypt(ma)


class TestLenSachTen:
    def test_loai_ky_tu_nguy_hiem(self) -> None:
        assert _lam_sach_ten("../../etc/passwd") == "etc_passwd"

    def test_ten_rong_thanh_mac_dinh(self) -> None:
        assert _lam_sach_ten("///") == "attachment"


class TestLocalAttachmentStore:
    async def test_luu_roi_doc_lai_duoc(self, tmp_path: Path) -> None:
        store = LocalAttachmentStore(str(tmp_path))

        info = await store.save(b"noi-dung-anh", "anh.jpg", "image/jpeg")

        assert info.size == len("noi-dung-anh")
        assert info.content_type == "image/jpeg"
        # File thật tồn tại và đọc lại đúng nội dung.
        duong_dan = store.resolve(info.stored_path)
        assert duong_dan.read_bytes() == b"noi-dung-anh"

    async def test_ten_duy_nhat_khong_de_nhau(self, tmp_path: Path) -> None:
        store = LocalAttachmentStore(str(tmp_path))

        a = await store.save(b"1", "same.jpg", None)
        b = await store.save(b"2", "same.jpg", None)

        assert a.stored_path != b.stored_path
        assert store.resolve(a.stored_path).read_bytes() == b"1"
        assert store.resolve(b.stored_path).read_bytes() == b"2"

    async def test_resolve_chan_thoat_khoi_thu_muc(self, tmp_path: Path) -> None:
        store = LocalAttachmentStore(str(tmp_path))

        with pytest.raises(ValueError):
            store.resolve("../ngoai.txt")
