"""Xác nhận repository thật khớp đúng Protocol domain.

Nếu một repository lệch chữ ký so với interface, mypy sẽ đỏ ngay ở đây — bắt lỗi
hợp đồng trước khi use case thật dùng tới. Không cần DB nên không đánh dấu
integration; chỉ là kiểm kiểu tĩnh.
"""

from src.modules.inbox.domain.repositories.channel_repository import IChannelRepository
from src.modules.inbox.domain.repositories.conversation_repository import (
    IConversationRepository,
)
from src.modules.inbox.domain.repositories.customer_repository import (
    ICustomerRepository,
)
from src.modules.inbox.domain.repositories.message_repository import IMessageRepository
from src.modules.inbox.infrastructure.repositories.channel_repository import (
    SqlAlchemyChannelRepository,
)
from src.modules.inbox.infrastructure.repositories.conversation_repository import (
    SqlAlchemyConversationRepository,
)
from src.modules.inbox.infrastructure.repositories.customer_repository import (
    SqlAlchemyCustomerRepository,
)
from src.modules.inbox.infrastructure.repositories.message_repository import (
    SqlAlchemyMessageRepository,
)


def test_repository_that_khop_protocol() -> None:
    # Gán None làm session: chỉ kiểm kiểu, không gọi phương thức nào.
    _chan: IChannelRepository = SqlAlchemyChannelRepository(None)  # type: ignore[arg-type]
    _cust: ICustomerRepository = SqlAlchemyCustomerRepository(None)  # type: ignore[arg-type]
    _conv: IConversationRepository = SqlAlchemyConversationRepository(None)  # type: ignore[arg-type]
    _msg: IMessageRepository = SqlAlchemyMessageRepository(None)  # type: ignore[arg-type]

    assert all(obj is not None for obj in (_chan, _cust, _conv, _msg))
