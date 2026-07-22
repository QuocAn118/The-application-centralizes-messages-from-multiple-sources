"""Port Unit of Work."""

from types import TracebackType
from typing import Protocol, Self


class IUnitOfWork(Protocol):
    """Gom nhiều thao tác ghi vào một giao dịch nguyên tử.

    Khi thoát context mà chưa gọi ``commit()``, mọi thay đổi bị rollback.
    """

    async def __aenter__(self) -> Self: ...

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> None: ...

    async def commit(self) -> None: ...

    async def rollback(self) -> None: ...
