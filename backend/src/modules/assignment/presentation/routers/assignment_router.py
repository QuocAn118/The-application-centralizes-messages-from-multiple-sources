"""Endpoint điều phối thủ công: ``POST /departments/{id}/auto-assign``.

Manager (phòng mình) / Admin kéo hàng đợi một phòng — gán các hội thoại ``DANG_MO``
chưa có người cho các nhân viên đang trong ca, theo chuỗi tiêu chí của bộ chọn.
Chạy song song với các trigger tự động (webhook → phân phòng → auto-assign; đóng
hội thoại → kéo hàng đợi). Staff bị 403; Manager phòng khác bị 403.
"""

from uuid import UUID

from fastapi import APIRouter, Request

from src.modules.assignment.application.authorization import (
    bao_dam_dieu_phoi_duoc_phong,
)
from src.modules.assignment.presentation.dependencies import (
    Actor,
    DbSession,
    build_pull_department_queue,
)
from src.modules.assignment.presentation.schemas.assignment_schemas import (
    PullQueueResponse,
)

router = APIRouter(tags=["assignment"])


@router.post("/departments/{department_id}/auto-assign", response_model=PullQueueResponse)
async def keo_hang_doi_phong(
    department_id: UUID,
    actor: Actor,
    session: DbSession,
    request: Request,
) -> PullQueueResponse:
    """Kéo hàng đợi một phòng cho các nhân viên đang trong ca.

    Trả số hội thoại vừa gán được. Không ai trong ca → gán 0, không lỗi (hội thoại
    vẫn nằm trong hàng đợi, chờ người vào ca/rảnh).
    """
    bao_dam_dieu_phoi_duoc_phong(actor, department_id)
    use_case = build_pull_department_queue(request, session)
    so_gan = await use_case.execute(department_id)
    return PullQueueResponse(assigned=so_gan)
