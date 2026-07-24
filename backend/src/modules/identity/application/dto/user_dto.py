"""DTO dùng chung cho các use case quản lý."""

from dataclasses import dataclass


@dataclass(frozen=True)
class Page[T]:
    """Một trang kết quả kèm tổng số bản ghi.

    ``total`` là tổng số bản ghi khớp bộ lọc, không phải số phần tử trong
    ``items`` — client cần nó để dựng thanh phân trang.
    """

    items: list[T]
    total: int
    limit: int
    offset: int
