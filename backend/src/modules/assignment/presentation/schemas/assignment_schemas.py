"""Schema HTTP cho assignment: phản hồi kéo hàng đợi một phòng."""

from pydantic import BaseModel, Field


class PullQueueResponse(BaseModel):
    """Kết quả kéo hàng đợi một phòng: số hội thoại vừa gán được."""

    assigned: int = Field(..., ge=0, description="Số hội thoại vừa được gán cho nhân viên.")
