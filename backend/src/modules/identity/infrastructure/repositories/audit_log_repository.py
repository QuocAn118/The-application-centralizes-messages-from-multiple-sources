"""Repository nhật ký kiểm toán dùng SQLAlchemy."""

from datetime import datetime
from typing import Any, TypeVar
from uuid import UUID

from sqlalchemy import Select, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.modules.identity.domain.entities.audit_log import AuditAction, AuditLog
from src.modules.identity.infrastructure.mappers.audit_log_mapper import AuditLogMapper
from src.modules.identity.infrastructure.models.audit_log_model import AuditLogModel

_SelectT = TypeVar("_SelectT", bound=Select[Any])

class SqlAlchemyAuditLogRepository:
    """Ghi và tra cứu nhật ký kiểm toán trong PostgreSQL."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(self, entry: AuditLog) -> None:
        self._session.add(AuditLogMapper.to_model(entry))

    def _ap_dung_bo_loc(
        self,
        cau_truy_van: _SelectT,
        actor_id: UUID | None,
        action: AuditAction | None,
        resource_type: str | None,
        from_time: datetime | None,
        to_time: datetime | None,
    ) -> _SelectT:
        if actor_id is not None:
            cau_truy_van = cau_truy_van.where(AuditLogModel.actor_id == actor_id)
        if action is not None:
            cau_truy_van = cau_truy_van.where(AuditLogModel.action == action.value)
        if resource_type is not None:
            cau_truy_van = cau_truy_van.where(
                AuditLogModel.resource_type == resource_type
            )
        if from_time is not None:
            cau_truy_van = cau_truy_van.where(AuditLogModel.created_at >= from_time)
        if to_time is not None:
            cau_truy_van = cau_truy_van.where(AuditLogModel.created_at <= to_time)
        return cau_truy_van

    async def list_entries(
        self,
        actor_id: UUID | None = None,
        action: AuditAction | None = None,
        resource_type: str | None = None,
        from_time: datetime | None = None,
        to_time: datetime | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[AuditLog]:
        cau_truy_van = self._ap_dung_bo_loc(
            select(AuditLogModel), actor_id, action, resource_type, from_time, to_time
        )
        cau_truy_van = (
            cau_truy_van.order_by(AuditLogModel.created_at.desc()).limit(limit).offset(offset)
        )
        ket_qua = await self._session.execute(cau_truy_van)
        return [AuditLogMapper.to_domain(m) for m in ket_qua.scalars()]

    async def count_entries(
        self,
        actor_id: UUID | None = None,
        action: AuditAction | None = None,
        resource_type: str | None = None,
        from_time: datetime | None = None,
        to_time: datetime | None = None,
    ) -> int:
        cau_truy_van = self._ap_dung_bo_loc(
            select(func.count()).select_from(AuditLogModel),
            actor_id,
            action,
            resource_type,
            from_time,
            to_time,
        )
        ket_qua = await self._session.execute(cau_truy_van)
        return int(ket_qua.scalar_one())
