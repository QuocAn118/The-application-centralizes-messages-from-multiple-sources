"""Registry tra adapter theo ``Platform`` — implementation ``IChannelAdapterRegistry``.

Router webhook dùng nó để chọn adapter đúng nền tảng. Thêm nền tảng mới = đăng
ký thêm một adapter ở đây, không sửa domain/use case (RB-1).
"""

from src.modules.inbox.domain.ports import IChannelAdapter
from src.modules.inbox.domain.value_objects.platform import Platform


class UnknownPlatformError(KeyError):
    """Chưa đăng ký adapter cho nền tảng này."""


class ChannelAdapterRegistry:
    """Bản đồ ``Platform`` → adapter tương ứng."""

    def __init__(self, adapters: list[IChannelAdapter]) -> None:
        self._by_platform: dict[Platform, IChannelAdapter] = {}
        for adapter in adapters:
            if adapter.platform in self._by_platform:
                raise ValueError(f"Trùng adapter cho nền tảng {adapter.platform}.")
            self._by_platform[adapter.platform] = adapter

    def for_platform(self, platform: Platform) -> IChannelAdapter:
        try:
            return self._by_platform[platform]
        except KeyError as exc:
            raise UnknownPlatformError(f"Chưa có adapter cho nền tảng {platform}.") from exc
