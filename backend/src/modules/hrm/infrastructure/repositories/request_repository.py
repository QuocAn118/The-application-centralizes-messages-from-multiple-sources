"""Repository đơn từ dùng SQLAlchemy."""

from typing import Any, TypeVar
from uuid import UUID

from sqlalchemy import ColumnElement, Select, false, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.modules.hrm.domain.entities.leave_request import LeaveRequest
from src.modules.hrm.domain.value_objects.request_kind import RequestStatus
from src.modules.hrm.infrastructure.mappers.request_mapper import RequestMapper
from src.modules.hrm.infrastructure.models.request_model import RequestModel

_SelectT = TypeVar("_SelectT", bound=Select[Any])


class SqlAlchemyRequestRepository:
    """Truy xuất đơn từ từ PostgreSQL."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def _lay_model(self, request_id: UUID) -> RequestModel | None:
        ket_qua = await self._session.execute(
            select(RequestModel).where(RequestModel.id == request_id)
        )
        return ket_qua.scalar_one_or_none()

    async def get_by_id(self, request_id: UUID) -> LeaveRequest | None:
        model = await self._lay_model(request_id)
        return RequestMapper.to_domain(model) if model else None

    async def add(self, request: LeaveRequest) -> None:
        self._session.add(RequestMapper.to_model(request))

    async def update(self, request: LeaveRequest) -> None:
        model = await self._lay_model(request.id)
        if model is None:
            raise ValueError(f"Không tìm thấy đơn {request.id} để cập nhật.")
        RequestMapper.update_model(model, request)

    def _dieu_kien_pham_vi(
        self, requester_id: UUID | None, department_ids: list[UUID] | None
    ) -> list[ColumnElement[bool]]:
        """Điều kiện WHERE cho phạm vi: hợp của 'đơn mình gửi' và 'đơn phòng mình'.

        Trả về danh sách điều kiện OR. ``None`` cả hai nghĩa là không giới hạn
        (Admin) — trả danh sách rỗng để không thêm WHERE.
        """
        dieu_kien: list[ColumnElement[bool]] = []
        if requester_id is not None:
            dieu_kien.append(RequestModel.requester_id == requester_id)
        if department_ids is not None:
            # Phòng rỗng: không khớp gì (điều kiện luôn sai) để không âm thầm
            # mở rộng phạm vi thành "tất cả".
            dieu_kien.append(
                RequestModel.department_id.in_(department_ids) if department_ids else false()
            )
        return dieu_kien

    def _ap_pham_vi(
        self,
        cau: _SelectT,
        requester_id: UUID | None,
        department_ids: list[UUID] | None,
        status: RequestStatus | None,
    ) -> _SelectT:
        dieu_kien = self._dieu_kien_pham_vi(requester_id, department_ids)
        if dieu_kien:
            cau = cau.where(or_(*dieu_kien))
        if status is not None:
            cau = cau.where(RequestModel.status == status.value)
        return cau

    async def list_for_scope(
        self,
        requester_id: UUID | None,
        department_ids: list[UUID] | None,
        status: RequestStatus | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[LeaveRequest]:
        cau = self._ap_pham_vi(select(RequestModel), requester_id, department_ids, status)
        cau = cau.order_by(RequestModel.created_at.desc()).limit(limit).offset(offset)
        ket_qua = await self._session.execute(cau)
        return [RequestMapper.to_domain(m) for m in ket_qua.scalars()]

    async def count_for_scope(
        self,
        requester_id: UUID | None,
        department_ids: list[UUID] | None,
        status: RequestStatus | None = None,
    ) -> int:
        cau = self._ap_pham_vi(
            select(func.count()).select_from(RequestModel), requester_id, department_ids, status
        )
        ket_qua = await self._session.execute(cau)
        return int(ket_qua.scalar_one())
