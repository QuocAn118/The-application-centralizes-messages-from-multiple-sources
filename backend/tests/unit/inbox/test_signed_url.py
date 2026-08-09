"""Test ký URL tệp đính kèm.

Đây là code bảo mật: nếu chữ ký giả mạo được, hoặc hạn sửa được, thì ảnh trong
tin nhắn của khách hàng lộ ra ngoài phạm vi quyền.
"""

from uuid import uuid4

import pytest

from src.modules.inbox.infrastructure.attachments.signed_url import (
    AttachmentUrlSigner,
    SignedUrlError,
)

KHOA = "khoa-bi-mat-de-test"


def test_chu_ky_vua_ky_thi_xac_minh_duoc() -> None:
    signer = AttachmentUrlSigner(KHOA, ttl_seconds=300)
    dinh_kem, hoi_thoai = uuid4(), uuid4()

    het_han, chu_ky = signer.ky(dinh_kem, hoi_thoai, now=1000)

    signer.xac_minh(dinh_kem, hoi_thoai, het_han, chu_ky, now=1000)


def test_het_han_thi_tu_choi() -> None:
    signer = AttachmentUrlSigner(KHOA, ttl_seconds=300)
    dinh_kem, hoi_thoai = uuid4(), uuid4()
    het_han, chu_ky = signer.ky(dinh_kem, hoi_thoai, now=1000)

    # Một giây sau khi hết hạn.
    with pytest.raises(SignedUrlError, match="hết hạn"):
        signer.xac_minh(dinh_kem, hoi_thoai, het_han, chu_ky, now=het_han + 1)


def test_sua_han_lam_chu_ky_sai() -> None:
    """Không được phép tự nới hạn — hạn nằm trong phần được ký."""
    signer = AttachmentUrlSigner(KHOA, ttl_seconds=300)
    dinh_kem, hoi_thoai = uuid4(), uuid4()
    het_han, chu_ky = signer.ky(dinh_kem, hoi_thoai, now=1000)

    with pytest.raises(SignedUrlError, match="không hợp lệ"):
        signer.xac_minh(dinh_kem, hoi_thoai, het_han + 10_000, chu_ky, now=1000)


def test_chu_ky_cua_tep_khac_khong_dung_lai_duoc() -> None:
    """Chữ ký gắn với đúng một tệp: không tái sử dụng cho tệp khác."""
    signer = AttachmentUrlSigner(KHOA, ttl_seconds=300)
    hoi_thoai = uuid4()
    het_han, chu_ky = signer.ky(uuid4(), hoi_thoai, now=1000)

    with pytest.raises(SignedUrlError, match="không hợp lệ"):
        signer.xac_minh(uuid4(), hoi_thoai, het_han, chu_ky, now=1000)


def test_chu_ky_cua_hoi_thoai_khac_khong_dung_lai_duoc() -> None:
    signer = AttachmentUrlSigner(KHOA, ttl_seconds=300)
    dinh_kem = uuid4()
    het_han, chu_ky = signer.ky(dinh_kem, uuid4(), now=1000)

    with pytest.raises(SignedUrlError, match="không hợp lệ"):
        signer.xac_minh(dinh_kem, uuid4(), het_han, chu_ky, now=1000)


def test_khoa_khac_thi_chu_ky_khong_hop_le() -> None:
    """Kẻ tấn công không có khoá thì không ký được."""
    dinh_kem, hoi_thoai = uuid4(), uuid4()
    het_han, chu_ky = AttachmentUrlSigner(KHOA).ky(dinh_kem, hoi_thoai, now=1000)

    with pytest.raises(SignedUrlError, match="không hợp lệ"):
        AttachmentUrlSigner("khoa-khac").xac_minh(dinh_kem, hoi_thoai, het_han, chu_ky, now=1000)


def test_chu_ky_rong_hoac_rac_bi_tu_choi() -> None:
    signer = AttachmentUrlSigner(KHOA)
    dinh_kem, hoi_thoai = uuid4(), uuid4()
    het_han, _ = signer.ky(dinh_kem, hoi_thoai, now=1000)

    for xau in ("", "rac", "0" * 64):
        with pytest.raises(SignedUrlError):
            signer.xac_minh(dinh_kem, hoi_thoai, het_han, xau, now=1000)


def test_khoa_rong_bi_tu_choi_ngay_khi_khoi_tao() -> None:
    """Thà hỏng lúc khởi động còn hơn ký bằng khoá rỗng."""
    with pytest.raises(ValueError):
        AttachmentUrlSigner("")
