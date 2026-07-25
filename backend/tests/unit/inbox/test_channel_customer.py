from datetime import UTC, datetime

import pytest

from src.modules.inbox.domain.entities.channel import (
    Channel,
    EmptyExternalChannelIdError,
)
from src.modules.inbox.domain.entities.customer import (
    Customer,
    EmptyExternalIdError,
)
from src.modules.inbox.domain.value_objects.platform import Platform
from src.shared.domain.identifiers import new_id

BAY_GIO = datetime(2026, 7, 24, 10, 0, tzinfo=UTC)


class TestChannel:
    def test_tao_kenh_gan_phong_ban(self) -> None:
        phong = new_id()
        kenh = Channel.connect(
            platform=Platform.ZALO,
            external_channel_id="oa_12345",
            name="OA Chăm sóc khách hàng",
            department_id=phong,
            encrypted_credential="enc::abc",
            now=BAY_GIO,
        )

        assert kenh.platform is Platform.ZALO
        assert kenh.external_channel_id == "oa_12345"
        assert kenh.department_id == phong
        assert kenh.is_active is True

    def test_kenh_khong_bat_buoc_gan_phong(self) -> None:
        """Kênh chưa gắn phòng thì hội thoại từ nó vào mục chờ-phân."""
        kenh = Channel.connect(
            platform=Platform.FACEBOOK,
            external_channel_id="page_999",
            name="Fanpage",
            department_id=None,
            encrypted_credential="enc::x",
            now=BAY_GIO,
        )

        assert kenh.department_id is None

    def test_external_id_rong_bi_tu_choi(self) -> None:
        with pytest.raises(EmptyExternalChannelIdError):
            Channel.connect(
                platform=Platform.ZALO,
                external_channel_id="   ",
                name="OA",
                department_id=None,
                encrypted_credential="enc::x",
                now=BAY_GIO,
            )

    def test_gan_phong_ban(self) -> None:
        kenh = Channel.connect(
            platform=Platform.INSTAGRAM,
            external_channel_id="ig_1",
            name="IG",
            department_id=None,
            encrypted_credential="enc::x",
            now=BAY_GIO,
        )
        phong = new_id()

        kenh.assign_department(phong, now=BAY_GIO)

        assert kenh.department_id == phong

    def test_doi_credential(self) -> None:
        kenh = Channel.connect(
            platform=Platform.ZALO,
            external_channel_id="oa_1",
            name="OA",
            department_id=None,
            encrypted_credential="enc::cu",
            now=BAY_GIO,
        )

        kenh.update_credential("enc::moi", now=BAY_GIO)

        assert kenh.encrypted_credential == "enc::moi"

    def test_vo_hieu_hoa(self) -> None:
        kenh = Channel.connect(
            platform=Platform.ZALO,
            external_channel_id="oa_1",
            name="OA",
            department_id=None,
            encrypted_credential="enc::x",
            now=BAY_GIO,
        )

        kenh.deactivate(now=BAY_GIO)

        assert kenh.is_active is False


class TestCustomer:
    def test_tao_khach(self) -> None:
        kenh_id = new_id()
        khach = Customer.register(
            channel_id=kenh_id,
            platform=Platform.ZALO,
            external_id="zalo_user_abc",
            display_name="Nguyễn Văn A",
            now=BAY_GIO,
        )

        assert khach.channel_id == kenh_id
        assert khach.platform is Platform.ZALO
        assert khach.external_id == "zalo_user_abc"
        assert khach.display_name == "Nguyễn Văn A"

    def test_external_id_rong_bi_tu_choi(self) -> None:
        with pytest.raises(EmptyExternalIdError):
            Customer.register(
                channel_id=new_id(),
                platform=Platform.ZALO,
                external_id="",
                display_name=None,
                now=BAY_GIO,
            )

    def test_khach_khong_bat_buoc_co_ten(self) -> None:
        """Webhook nhiều khi không kèm tên; vẫn phải tạo được khách."""
        khach = Customer.register(
            channel_id=new_id(),
            platform=Platform.FACEBOOK,
            external_id="fb_1",
            display_name=None,
            now=BAY_GIO,
        )

        assert khach.display_name is None

    def test_cap_nhat_ten_khi_biet_sau(self) -> None:
        khach = Customer.register(
            channel_id=new_id(),
            platform=Platform.FACEBOOK,
            external_id="fb_1",
            display_name=None,
            now=BAY_GIO,
        )

        khach.update_profile(display_name="Trần B", avatar_url=None, now=BAY_GIO)

        assert khach.display_name == "Trần B"

    def test_ten_rong_khong_ghi_de_ten_cu(self) -> None:
        """Webhook trả name='' không được xoá tên khách đang có."""
        khach = Customer.register(
            channel_id=new_id(),
            platform=Platform.FACEBOOK,
            external_id="fb_1",
            display_name="Trần B",
            now=BAY_GIO,
        )

        khach.update_profile(display_name="   ", avatar_url=None, now=BAY_GIO)

        assert khach.display_name == "Trần B"

    def test_register_ten_rong_thanh_none(self) -> None:
        khach = Customer.register(
            channel_id=new_id(),
            platform=Platform.ZALO,
            external_id="z_1",
            display_name="   ",
            now=BAY_GIO,
        )

        assert khach.display_name is None

    def test_cap_nhat_anh_dai_dien(self) -> None:
        khach = Customer.register(
            channel_id=new_id(),
            platform=Platform.ZALO,
            external_id="z_2",
            display_name="A",
            now=BAY_GIO,
        )

        khach.update_profile(
            display_name=None, avatar_url="https://cdn/a.jpg", now=BAY_GIO
        )

        assert khach.avatar_url == "https://cdn/a.jpg"
