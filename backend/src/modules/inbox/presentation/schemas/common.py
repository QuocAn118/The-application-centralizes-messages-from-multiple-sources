"""Schema dùng chung cho phản hồi inbox."""

from pydantic import BaseModel


class PageResponse[T](BaseModel):
    """Một trang kết quả."""

    items: list[T]
    total: int
    limit: int
    offset: int
