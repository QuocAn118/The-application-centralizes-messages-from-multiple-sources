"""Endpoint mẫu trả lời nhanh (BE-7)."""

from uuid import UUID

from fastapi import APIRouter, Response
from sqlalchemy.ext.asyncio import AsyncSession

from src.modules.inbox.application.use_cases.reply_templates import ReplyTemplates
from src.modules.inbox.domain.entities.reply_template import ReplyTemplate
from src.modules.inbox.infrastructure.repositories.reply_template_repository import (
    SqlAlchemyReplyTemplateRepository,
)
from src.modules.inbox.presentation.dependencies import Actor, Clock, DbSession
from src.modules.inbox.presentation.schemas.customer_schemas import (
    TemplateCreateRequest,
    TemplateResponse,
    TemplateUpdateRequest,
)
from src.shared.application.ports import IClock

router = APIRouter(tags=["inbox"])


def _uc(session: AsyncSession, clock: IClock) -> ReplyTemplates:
    return ReplyTemplates(SqlAlchemyReplyTemplateRepository(session), clock)


def _ra(m: ReplyTemplate) -> TemplateResponse:
    return TemplateResponse(
        id=m.id, department_id=m.department_id, title=m.title, body=m.body, updated_at=m.updated_at
    )


@router.get("/reply-templates", response_model=list[TemplateResponse])
async def danh_sach_mau(actor: Actor, session: DbSession, clock: Clock) -> list[TemplateResponse]:
    return [_ra(m) for m in await _uc(session, clock).danh_sach(actor)]


@router.post("/reply-templates", response_model=TemplateResponse, status_code=201)
async def tao_mau(
    du_lieu: TemplateCreateRequest, actor: Actor, session: DbSession, clock: Clock
) -> TemplateResponse:
    mau = await _uc(session, clock).tao(actor, du_lieu.department_id, du_lieu.title, du_lieu.body)
    return _ra(mau)


@router.patch("/reply-templates/{template_id}", response_model=TemplateResponse)
async def sua_mau(
    template_id: UUID,
    du_lieu: TemplateUpdateRequest,
    actor: Actor,
    session: DbSession,
    clock: Clock,
) -> TemplateResponse:
    return _ra(await _uc(session, clock).sua(actor, template_id, du_lieu.title, du_lieu.body))


@router.delete("/reply-templates/{template_id}", status_code=204)
async def xoa_mau(template_id: UUID, actor: Actor, session: DbSession, clock: Clock) -> Response:
    await _uc(session, clock).xoa(actor, template_id)
    return Response(status_code=204)
