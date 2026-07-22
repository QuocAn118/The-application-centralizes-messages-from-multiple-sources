"""Lớp cơ sở cho value object trong tầng domain."""

from dataclasses import dataclass


@dataclass(frozen=True)
class ValueObject:
    """Value object được định danh bằng giá trị, không có ``id``.

    Lớp con phải khai báo ``@dataclass(frozen=True)`` để giữ tính bất biến.
    """
