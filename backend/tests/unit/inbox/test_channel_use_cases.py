from datetime import UTC, datetime

import pytest

from src.modules.inbox.application.actor import ActorRole, InboxActor
from src.modules.inbox.application.use_cases.connect_channel import ConnectChannel
from src.modules.inbox.application.use_cases.deactivate_channel import DeactivateChannel
from src.modules.inbox.application.use_cases.list_channels import ListChannels
from src.modules.inbox.application.use_cases.update_channel import UpdateChannel
from src.modules.inbox.domain.value_objects.platform import Platform
from src.shared.application.exceptions import (
    ConflictError,
    NotFoundError,
    PermissionDeniedError,
)
from src.shared.domain.identifiers import new_id
from tests.unit.inbox.fakes import (
    FakeChannelRepository,
    FakeClock,
    FakeCredentialCipher,
    FakeWorkforceDirectory,
)

BAY_GIO = datetime(2026, 7, 24, 10, 0, tzinfo=UTC)
PHONG_A = new_id()
ADMIN = InboxActor(user_id=new_id(), role=ActorRole.ADMIN, department_id=None)
STAFF = InboxActor(user_id=new_id(), role=ActorRole.STAFF, department_id=PHONG_A)


class _BoiCanh:
    def __init__(self) -> None:
        self.clock = FakeClock(BAY_GIO)
        self.repo = FakeChannelRepository()
        self.cipher = FakeCredentialCipher()
        self.directory = FakeWorkforceDirectory()
        self.directory.active_departments.add(PHONG_A)
        self.connect = ConnectChannel(self.repo, self.directory, self.cipher, self.clock)
        self.update = UpdateChannel(self.repo, self.directory, self.cipher, self.clock)
        self.deactivate = DeactivateChannel(self.repo, self.clock)
        self.list = ListChannels(self.repo)


class TestKetNoi:
    async def test_admin_ket_noi_va_credential_duoc_ma_hoa(self) -> None:
        bc = _BoiCanh()

        channel = await bc.connect.execute(
            ADMIN,
            platform=Platform.ZALO,
            external_channel_id="oa_1",
            name="OA",
            credential="token-tho",
            department_id=PHONG_A,
        )

        # Không lưu token thô: đã bọc qua cipher.
        assert channel.encrypted_credential == "enc::token-tho"
        assert channel.encrypted_credential != "token-tho"

    async def test_staff_khong_duoc_ket_noi(self) -> None:
        bc = _BoiCanh()

        with pytest.raises(PermissionDeniedError):
            await bc.connect.execute(
                STAFF,
                platform=Platform.ZALO,
                external_channel_id="oa_1",
                name="OA",
                credential="t",
            )

    async def test_ket_noi_trung_kenh_bi_chan(self) -> None:
        bc = _BoiCanh()
        await bc.connect.execute(
            ADMIN, platform=Platform.ZALO, external_channel_id="oa_1", name="OA", credential="t"
        )

        with pytest.raises(ConflictError):
            await bc.connect.execute(
                ADMIN,
                platform=Platform.ZALO,
                external_channel_id="oa_1",
                name="OA khac",
                credential="t2",
            )

    async def test_phong_khong_hoat_dong_bi_tu_choi(self) -> None:
        bc = _BoiCanh()

        with pytest.raises(NotFoundError):
            await bc.connect.execute(
                ADMIN,
                platform=Platform.ZALO,
                external_channel_id="oa_1",
                name="OA",
                credential="t",
                department_id=new_id(),
            )


class TestCapNhat:
    async def test_doi_credential_thi_ma_hoa_lai(self) -> None:
        bc = _BoiCanh()
        ch = await bc.connect.execute(
            ADMIN, platform=Platform.ZALO, external_channel_id="oa_1", name="OA", credential="cu"
        )

        moi = await bc.update.execute(ADMIN, ch.id, credential="moi")

        assert moi.encrypted_credential == "enc::moi"

    async def test_doi_ten(self) -> None:
        bc = _BoiCanh()
        ch = await bc.connect.execute(
            ADMIN, platform=Platform.ZALO, external_channel_id="oa_1", name="OA", credential="c"
        )

        moi = await bc.update.execute(ADMIN, ch.id, name="OA moi")

        assert moi.name == "OA moi"

    async def test_go_phong(self) -> None:
        bc = _BoiCanh()
        ch = await bc.connect.execute(
            ADMIN,
            platform=Platform.ZALO,
            external_channel_id="oa_1",
            name="OA",
            credential="c",
            department_id=PHONG_A,
        )

        moi = await bc.update.execute(ADMIN, ch.id, clear_department=True)

        assert moi.department_id is None

    async def test_staff_khong_duoc_cap_nhat(self) -> None:
        bc = _BoiCanh()
        ch = await bc.connect.execute(
            ADMIN, platform=Platform.ZALO, external_channel_id="oa_1", name="OA", credential="c"
        )

        with pytest.raises(PermissionDeniedError):
            await bc.update.execute(STAFF, ch.id, name="x")

    async def test_doi_phong_moi(self) -> None:
        bc = _BoiCanh()
        ch = await bc.connect.execute(
            ADMIN, platform=Platform.ZALO, external_channel_id="oa_1", name="OA", credential="c"
        )

        moi = await bc.update.execute(ADMIN, ch.id, department_id=PHONG_A)

        assert moi.department_id == PHONG_A

    async def test_doi_sang_phong_khong_hoat_dong_bi_tu_choi(self) -> None:
        bc = _BoiCanh()
        ch = await bc.connect.execute(
            ADMIN, platform=Platform.ZALO, external_channel_id="oa_1", name="OA", credential="c"
        )

        with pytest.raises(NotFoundError):
            await bc.update.execute(ADMIN, ch.id, department_id=new_id())

    async def test_cap_nhat_kenh_khong_ton_tai(self) -> None:
        bc = _BoiCanh()

        with pytest.raises(NotFoundError):
            await bc.update.execute(ADMIN, new_id(), name="x")


class TestNgatVaLietKe:
    async def test_ngat_kenh(self) -> None:
        bc = _BoiCanh()
        ch = await bc.connect.execute(
            ADMIN, platform=Platform.ZALO, external_channel_id="oa_1", name="OA", credential="c"
        )

        moi = await bc.deactivate.execute(ADMIN, ch.id)

        assert moi.is_active is False

    async def test_liet_ke_chi_admin(self) -> None:
        bc = _BoiCanh()
        await bc.connect.execute(
            ADMIN, platform=Platform.ZALO, external_channel_id="oa_1", name="OA", credential="c"
        )

        ds = await bc.list.execute(ADMIN)
        assert len(ds) == 1

        with pytest.raises(PermissionDeniedError):
            await bc.list.execute(STAFF)

    async def test_kenh_khong_ton_tai(self) -> None:
        bc = _BoiCanh()

        with pytest.raises(NotFoundError):
            await bc.deactivate.execute(ADMIN, new_id())
