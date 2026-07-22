from dataclasses import FrozenInstanceError, dataclass
from uuid import UUID

import pytest

from src.shared.domain.entity import Entity
from src.shared.domain.identifiers import new_id
from src.shared.domain.value_object import ValueObject


@dataclass(eq=False, kw_only=True)
class _EntityGiaLap(Entity):
    ten: str


@dataclass(frozen=True)
class _ValueObjectGiaLap(ValueObject):
    gia_tri: str


def test_hai_entity_cung_id_thi_bang_nhau() -> None:
    ma_dinh_danh: UUID = new_id()
    a = _EntityGiaLap(id=ma_dinh_danh, ten="A")
    b = _EntityGiaLap(id=ma_dinh_danh, ten="B khac hoan toan")

    assert a == b


def test_hai_entity_khac_id_thi_khac_nhau() -> None:
    a = _EntityGiaLap(id=new_id(), ten="Trung ten")
    b = _EntityGiaLap(id=new_id(), ten="Trung ten")

    assert a != b


def test_entity_dung_duoc_lam_khoa_cua_set() -> None:
    ma_dinh_danh = new_id()
    a = _EntityGiaLap(id=ma_dinh_danh, ten="A")
    b = _EntityGiaLap(id=ma_dinh_danh, ten="B")

    assert len({a, b}) == 1


def test_value_object_bang_nhau_khi_cung_gia_tri() -> None:
    assert _ValueObjectGiaLap(gia_tri="x") == _ValueObjectGiaLap(gia_tri="x")


def test_value_object_khong_the_thay_doi() -> None:
    vo = _ValueObjectGiaLap(gia_tri="x")
    with pytest.raises(FrozenInstanceError):
        vo.gia_tri = "y"  # type: ignore[misc]
