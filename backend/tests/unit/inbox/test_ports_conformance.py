"""Xác nhận fake khớp đúng hợp đồng port/repository.

Nếu một port đổi chữ ký mà fake không theo, các phép gán dưới đây sẽ làm mypy
đỏ — bắt lệch hợp đồng ngay ở tầng test thay vì để lộ ra lúc chạy use case.
"""

from src.modules.inbox.domain.ports import (
    IAttachmentStore,
    IChannelAdapter,
    IChannelAdapterRegistry,
    ICredentialCipher,
    IRealtimeNotifier,
    IWorkforceDirectory,
)
from src.modules.inbox.domain.repositories.channel_repository import (
    IChannelRepository,
)
from src.modules.inbox.domain.repositories.conversation_repository import (
    IConversationRepository,
)
from src.modules.inbox.domain.repositories.customer_repository import (
    ICustomerRepository,
)
from src.modules.inbox.domain.repositories.message_repository import (
    IMessageRepository,
)
from src.modules.inbox.domain.value_objects.platform import Platform
from tests.unit.inbox.fakes import (
    FakeAttachmentStore,
    FakeChannelAdapter,
    FakeChannelAdapterRegistry,
    FakeChannelRepository,
    FakeConversationRepository,
    FakeCredentialCipher,
    FakeCustomerRepository,
    FakeMessageRepository,
    FakeRealtimeNotifier,
    FakeWorkforceDirectory,
)


def test_fake_khop_hop_dong_port() -> None:
    _chan_repo: IChannelRepository = FakeChannelRepository()
    _cust_repo: ICustomerRepository = FakeCustomerRepository()
    _conv_repo: IConversationRepository = FakeConversationRepository()
    _msg_repo: IMessageRepository = FakeMessageRepository()
    _cipher: ICredentialCipher = FakeCredentialCipher()
    _store: IAttachmentStore = FakeAttachmentStore()
    _adapter: IChannelAdapter = FakeChannelAdapter(Platform.ZALO)
    _registry: IChannelAdapterRegistry = FakeChannelAdapterRegistry([])
    _directory: IWorkforceDirectory = FakeWorkforceDirectory()
    _notifier: IRealtimeNotifier = FakeRealtimeNotifier()

    # Chạm tới để linter không coi là biến thừa; giá trị không quan trọng.
    assert _adapter.platform is Platform.ZALO
    assert all(
        obj is not None
        for obj in (
            _chan_repo,
            _cust_repo,
            _conv_repo,
            _msg_repo,
            _cipher,
            _store,
            _registry,
            _directory,
            _notifier,
        )
    )
