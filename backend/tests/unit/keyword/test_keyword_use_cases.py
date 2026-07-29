from datetime import UTC, datetime

import pytest

from src.modules.keyword.application.actor import ActorRole, KeywordActor
from src.modules.keyword.application.use_cases.keyword_use_cases import (
    CreateKeyword,
    DeleteKeyword,
    ListKeywords,
    UpdateKeyword,
)
from src.modules.keyword.domain.entities.keyword import Keyword
from src.shared.application.exceptions import (
    ConflictError,
    NotFoundError,
    PermissionDeniedError,
)
from src.shared.domain.identifiers import new_id
from tests.unit.keyword.fakes import (
    FakeClock,
    FakeKeywordRepository,
    FakeWorkforceDirectory,
)

BAY_GIO = datetime(2026, 8, 1, 9, 0, tzinfo=UTC)
PHONG_A = new_id()
PHONG_B = new_id()


def _manager(department_id=PHONG_A) -> KeywordActor:
    return KeywordActor(user_id=new_id(), role=ActorRole.MANAGER, department_id=department_id)


def _admin() -> KeywordActor:
    return KeywordActor(user_id=new_id(), role=ActorRole.ADMIN, department_id=None)


def _staff() -> KeywordActor:
    return KeywordActor(user_id=new_id(), role=ActorRole.STAFF, department_id=PHONG_A)


class _Boi:
    def __init__(self) -> None:
        self.clock = FakeClock(BAY_GIO)
        self.repo = FakeKeywordRepository()
        self.directory = FakeWorkforceDirectory()
        self.directory.active_departments = {PHONG_A, PHONG_B}
        self.create = CreateKeyword(self.repo, self.directory, self.clock)
        self.update = UpdateKeyword(self.repo, self.clock)
        self.delete = DeleteKeyword(self.repo)
        self.list = ListKeywords(self.repo)


class TestCreateKeyword:
    async def test_manager_tao_keyword_phong_minh(self) -> None:
        bc = _Boi()
        v = await bc.create.execute(_manager(), PHONG_A, "Bảo Hành")

        assert v.text == "Bảo Hành"
        assert v.normalized == "bao hanh"
        assert v.department_id == PHONG_A

    async def test_admin_tao_moi_phong(self) -> None:
        bc = _Boi()
        v = await bc.create.execute(_admin(), PHONG_B, "Báo giá")
        assert v.department_id == PHONG_B

    async def test_staff_bi_tu_choi(self) -> None:
        bc = _Boi()
        with pytest.raises(PermissionDeniedError):
            await bc.create.execute(_staff(), PHONG_A, "x")

    async def test_manager_phong_khac_bi_tu_choi(self) -> None:
        bc = _Boi()
        with pytest.raises(PermissionDeniedError):
            await bc.create.execute(_manager(PHONG_A), PHONG_B, "x")

    async def test_trung_normalized_bi_chan(self) -> None:
        # "Bảo Hành" và "bao hanh" chuẩn hoá giống nhau -> trùng.
        bc = _Boi()
        await bc.create.execute(_manager(), PHONG_A, "Bảo Hành")

        with pytest.raises(ConflictError):
            await bc.create.execute(_manager(), PHONG_A, "bao hanh")

    async def test_cung_text_khac_phong_khong_trung(self) -> None:
        bc = _Boi()
        await bc.create.execute(_admin(), PHONG_A, "Bảo hành")
        # Phòng khác dùng cùng từ khoá vẫn được.
        v = await bc.create.execute(_admin(), PHONG_B, "Bảo hành")
        assert v.department_id == PHONG_B

    async def test_phong_khong_ton_tai(self) -> None:
        bc = _Boi()
        with pytest.raises(NotFoundError):
            await bc.create.execute(_admin(), new_id(), "x")


class TestUpdateKeyword:
    async def test_doi_noi_dung(self) -> None:
        bc = _Boi()
        kw = Keyword.create(department_id=PHONG_A, text="Bảo hành", now=BAY_GIO)
        await bc.repo.add(kw)

        v = await bc.update.execute(_manager(), kw.id, "Đổi trả")
        assert v.normalized == "doi tra"

    async def test_doi_thanh_trung_bi_chan(self) -> None:
        bc = _Boi()
        await bc.repo.add(Keyword.create(department_id=PHONG_A, text="Bảo hành", now=BAY_GIO))
        kw2 = Keyword.create(department_id=PHONG_A, text="Đổi trả", now=BAY_GIO)
        await bc.repo.add(kw2)

        with pytest.raises(ConflictError):
            await bc.update.execute(_manager(), kw2.id, "bao hanh")

    async def test_khong_ton_tai(self) -> None:
        bc = _Boi()
        with pytest.raises(NotFoundError):
            await bc.update.execute(_manager(), new_id(), "x")


class TestDeleteKeyword:
    async def test_xoa(self) -> None:
        bc = _Boi()
        kw = Keyword.create(department_id=PHONG_A, text="Bảo hành", now=BAY_GIO)
        await bc.repo.add(kw)

        await bc.delete.execute(_manager(), kw.id)
        assert await bc.repo.get_by_id(kw.id) is None

    async def test_manager_phong_khac_khong_xoa(self) -> None:
        bc = _Boi()
        kw = Keyword.create(department_id=PHONG_A, text="Bảo hành", now=BAY_GIO)
        await bc.repo.add(kw)

        with pytest.raises(PermissionDeniedError):
            await bc.delete.execute(_manager(PHONG_B), kw.id)


class TestListKeywords:
    async def test_manager_chi_thay_phong_minh(self) -> None:
        bc = _Boi()
        await bc.repo.add(Keyword.create(department_id=PHONG_A, text="A", now=BAY_GIO))
        await bc.repo.add(Keyword.create(department_id=PHONG_B, text="B", now=BAY_GIO))

        views = await bc.list.execute(_manager(PHONG_A))
        assert {v.department_id for v in views} == {PHONG_A}

    async def test_admin_thay_tat_ca(self) -> None:
        bc = _Boi()
        await bc.repo.add(Keyword.create(department_id=PHONG_A, text="A", now=BAY_GIO))
        await bc.repo.add(Keyword.create(department_id=PHONG_B, text="B", now=BAY_GIO))

        views = await bc.list.execute(_admin())
        assert len(views) == 2
