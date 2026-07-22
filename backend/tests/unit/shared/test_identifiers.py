from uuid import UUID

from src.shared.domain.identifiers import new_id


def test_new_id_tra_ve_uuid_phien_ban_7() -> None:
    ma = new_id()

    assert isinstance(ma, UUID)
    assert ma.version == 7


def test_hai_lan_goi_cho_hai_gia_tri_khac_nhau() -> None:
    assert new_id() != new_id()


def test_id_sinh_sau_lon_hon_id_sinh_truoc() -> None:
    """UUID v7 sắp xếp được theo thời gian — đây là lý do chọn v7 thay vì v4."""
    danh_sach = [new_id() for _ in range(100)]

    assert danh_sach == sorted(danh_sach)
