import pytest

from src.modules.inbox.domain.value_objects.platform import Platform
from src.modules.inbox.infrastructure.channels.meta_adapter import MetaAdapter
from src.modules.inbox.infrastructure.channels.registry import (
    ChannelAdapterRegistry,
    UnknownPlatformError,
)
from src.modules.inbox.infrastructure.channels.zalo_adapter import ZaloAdapter


def _registry() -> ChannelAdapterRegistry:
    return ChannelAdapterRegistry(
        [
            ZaloAdapter("app", "secret"),
            MetaAdapter(Platform.FACEBOOK, "s"),
            MetaAdapter(Platform.INSTAGRAM, "s"),
        ]
    )


class TestRegistry:
    def test_tra_dung_adapter_theo_platform(self) -> None:
        reg = _registry()

        assert reg.for_platform(Platform.ZALO).platform is Platform.ZALO
        assert reg.for_platform(Platform.FACEBOOK).platform is Platform.FACEBOOK
        assert reg.for_platform(Platform.INSTAGRAM).platform is Platform.INSTAGRAM

    def test_fb_va_ig_la_hai_adapter_khac_nhau(self) -> None:
        reg = _registry()

        assert reg.for_platform(Platform.FACEBOOK) is not reg.for_platform(Platform.INSTAGRAM)

    def test_trung_adapter_bi_chan(self) -> None:
        with pytest.raises(ValueError):
            ChannelAdapterRegistry([ZaloAdapter("a", "b"), ZaloAdapter("c", "d")])

    def test_platform_chua_dang_ky(self) -> None:
        reg = ChannelAdapterRegistry([ZaloAdapter("a", "b")])

        with pytest.raises(UnknownPlatformError):
            reg.for_platform(Platform.FACEBOOK)
