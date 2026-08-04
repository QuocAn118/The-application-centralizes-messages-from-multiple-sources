"""ORM model cho bảng ``assignment_log`` — lịch sử mỗi lần gán thành công (#3).

Chứa UUID thuần tham chiếu inbox/identity — KHÔNG khoá ngoại (giữ #3 độc lập với
#1/#4, chỉ tham chiếu qua UUID như mọi module khác). Mỗi dòng là một lần gán thực
sự được inbox chấp nhận (``AssignResult.ASSIGNED``); một hội thoại có thể có nhiều
dòng nếu được gán lại. Đây là nguồn sự thật cho ``assigned_count`` của #5 — khác
``conversations.assigned_user_id`` chỉ giữ người cuối.

``assigned_at`` lưu kèm timezone (``timestamptz``): #5 tự quy đổi về giờ nghiệp vụ
địa phương khi gom theo ngày, giống các nguồn khác.
"""

from datetime import datetime
from uuid import UUID

from sqlalchemy import DateTime
from sqlalchemy.dialects.postgresql import UUID as PgUUID  # noqa: N811
from sqlalchemy.orm import Mapped, mapped_column

from src.shared.infrastructure.database import Base


class AssignmentLogModel(Base):
    """Bảng ``assignment_log`` — một dòng cho mỗi lần gán thành công.

    ``id`` là khoá chính thay thế (UUID v7, sinh khi ghi). Không có ràng buộc duy
    nhất theo hội thoại: gán lại nhiều lần là hợp lệ và cần được đếm đủ.
    """

    __tablename__ = "assignment_log"

    id: Mapped[UUID] = mapped_column(PgUUID(as_uuid=True), primary_key=True)
    conversation_id: Mapped[UUID] = mapped_column(PgUUID(as_uuid=True), nullable=False)
    user_id: Mapped[UUID] = mapped_column(PgUUID(as_uuid=True), nullable=False)
    department_id: Mapped[UUID | None] = mapped_column(PgUUID(as_uuid=True), nullable=True)
    assigned_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
