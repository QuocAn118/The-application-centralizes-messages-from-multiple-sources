"""Schema dùng chung cho phản hồi HTTP."""

from typing import Any

from pydantic import BaseModel, Field


class ErrorDetail(BaseModel):
    """Chi tiết một lỗi."""

    code: str = Field(description="Mã lỗi ổn định, dùng để đối chiếu ở client")
    message: str = Field(description="Thông điệp tiếng Việt hiển thị cho người dùng")
    details: dict[str, Any] | None = Field(default=None)


class ErrorResponse(BaseModel):
    """Định dạng lỗi thống nhất cho toàn bộ API."""

    error: ErrorDetail
    request_id: str


class PageResponse[T](BaseModel):
    """Một trang kết quả."""

    items: list[T]
    total: int
    limit: int
    offset: int
