"""Use case đơn từ — gửi, thu hồi, duyệt/từ chối (một cấp), liệt kê/xem.

Phê duyệt một cấp: đơn của Staff về Manager phòng đó; đơn của Manager về Admin.
Người duyệt được xác định qua ``IWorkforceDirectory`` — hrm không biết identity.
Máy trạng thái (không quyết lại đơn đã xử lý, từ chối cần lý do) nằm trong entity
``LeaveRequest``; use case chỉ lo phân quyền và định tuyến.
"""

from datetime import date
from uuid import UUID

from src.modules.hrm.application.actor import ActorRole, HrmActor
from src.modules.hrm.application.dto.hrm_dto import Page, RequestView
from src.modules.hrm.domain.entities.leave_request import LeaveRequest
from src.modules.hrm.domain.ports import (
    CHANGE_REQUEST_DECIDED,
    CHANGE_REQUEST_SUBMITTED,
    INotifier,
    IWorkforceDirectory,
)
from src.modules.hrm.domain.repositories.request_repository import IRequestRepository
from src.modules.hrm.domain.value_objects.request_kind import (
    RequestStatus,
    RequestType,
)
from src.shared.application.exceptions import (
    NotFoundError,
    PermissionDeniedError,
)
from src.shared.application.ports import IClock


def _view(r: LeaveRequest) -> RequestView:
    return RequestView(
        id=r.id,
        requester_id=r.requester_id,
        department_id=r.department_id,
        request_type=r.request_type,
        reason=r.reason,
        status=r.status,
        created_at=r.created_at,
        leave_start=r.leave_start,
        leave_end=r.leave_end,
        decided_by=r.decided_by,
        decided_at=r.decided_at,
        decision_reason=r.decision_reason,
    )


def _khong_thay() -> NotFoundError:
    return NotFoundError("Không tìm thấy đơn.", code="REQUEST_NOT_FOUND")


class SubmitRequest:
    """Nhân viên gửi một đơn từ. Phòng ban chụp từ danh bạ để định tuyến duyệt."""

    def __init__(
        self,
        request_repo: IRequestRepository,
        directory: IWorkforceDirectory,
        notifier: INotifier,
        clock: IClock,
    ) -> None:
        self._request_repo = request_repo
        self._directory = directory
        self._notifier = notifier
        self._clock = clock

    async def execute(
        self,
        actor: HrmActor,
        request_type: RequestType,
        reason: str,
        leave_start: date | None = None,
        leave_end: date | None = None,
    ) -> RequestView:
        # Người gửi phải thuộc một phòng (Admin không thuộc phòng nên không gửi
        # đơn nội bộ — không có Manager cấp trên để duyệt).
        agent = await self._directory.get_agent(actor.user_id)
        if agent is None or not agent.is_active or agent.department_id is None:
            raise PermissionDeniedError(
                "Chỉ nhân viên thuộc một phòng ban mới gửi được đơn.",
                code="REQUESTER_HAS_NO_DEPARTMENT",
            )

        now = self._clock.now()
        request = LeaveRequest.submit(
            requester_id=actor.user_id,
            department_id=agent.department_id,
            request_type=request_type,
            reason=reason,
            leave_start=leave_start,
            leave_end=leave_end,
            now=now,
        )
        await self._request_repo.add(request)

        approver = await self._nguoi_duyet(agent.department_id, actor.role)
        if approver is not None:
            await self._notifier.notify_request_changed(
                request.id, approver, CHANGE_REQUEST_SUBMITTED
            )
        return _view(request)

    async def _nguoi_duyet(self, department_id: UUID, requester_role: ActorRole) -> UUID | None:
        """Ai duyệt đơn này: Manager phòng đó (đơn Staff) — đơn Manager thì Admin.

        Trả ``None`` khi không tìm được người duyệt cụ thể để báo (ví dụ đơn của
        Manager: Admin không gắn phòng nên không tra qua danh bạ phòng). Đơn vẫn
        được lưu; Admin thấy nó qua danh sách.
        """
        if requester_role is ActorRole.MANAGER:
            return None
        manager = await self._directory.get_manager_of_department(department_id)
        return manager.user_id if manager is not None else None


class CancelRequest:
    """Người gửi thu hồi đơn của chính mình khi còn chờ duyệt."""

    def __init__(self, request_repo: IRequestRepository, clock: IClock) -> None:
        self._request_repo = request_repo
        self._clock = clock

    async def execute(self, actor: HrmActor, request_id: UUID) -> RequestView:
        request = await self._request_repo.get_by_id(request_id)
        if request is None:
            raise _khong_thay()
        if request.requester_id != actor.user_id:
            raise PermissionDeniedError(
                "Bạn chỉ được thu hồi đơn của chính mình.", code="NOT_REQUEST_OWNER"
            )

        request.cancel(self._clock.now())
        await self._request_repo.update(request)
        return _view(request)


class _DecideRequest:
    """Nền chung cho duyệt và từ chối: kiểm quyền người quyết định.

    Một cấp: Manager quyết đơn của Staff trong phòng mình; Admin quyết đơn của
    Manager. Không ai tự quyết đơn của chính mình.
    """

    def __init__(
        self,
        request_repo: IRequestRepository,
        directory: IWorkforceDirectory,
        notifier: INotifier,
        clock: IClock,
    ) -> None:
        self._request_repo = request_repo
        self._directory = directory
        self._notifier = notifier
        self._clock = clock

    async def _lay_don_va_kiem_quyen(self, actor: HrmActor, request_id: UUID) -> LeaveRequest:
        request = await self._request_repo.get_by_id(request_id)
        if request is None:
            raise _khong_thay()
        if request.requester_id == actor.user_id:
            raise PermissionDeniedError(
                "Không thể tự quyết định đơn của chính mình.", code="CANNOT_DECIDE_OWN_REQUEST"
            )

        requester = await self._directory.get_agent(request.requester_id)
        requester_is_manager = requester is not None and requester.role == "MANAGER"

        if requester_is_manager:
            # Đơn của Manager -> chỉ Admin quyết.
            if actor.role is not ActorRole.ADMIN:
                raise self._tu_choi()
        else:
            # Đơn của Staff -> Admin, hoặc Manager đúng phòng của đơn.
            if actor.role is ActorRole.ADMIN or (
                actor.role is ActorRole.MANAGER and request.department_id == actor.department_id
            ):
                pass
            else:
                raise self._tu_choi()
        return request

    @staticmethod
    def _tu_choi() -> PermissionDeniedError:
        return PermissionDeniedError("Bạn không có quyền duyệt đơn này.", code="APPROVE_FORBIDDEN")


class ApproveRequest(_DecideRequest):
    """Duyệt một đơn đang chờ."""

    async def execute(self, actor: HrmActor, request_id: UUID) -> RequestView:
        request = await self._lay_don_va_kiem_quyen(actor, request_id)
        request.approve(actor.user_id, self._clock.now())
        await self._request_repo.update(request)
        await self._notifier.notify_request_changed(
            request.id, request.requester_id, CHANGE_REQUEST_DECIDED
        )
        return _view(request)


class RejectRequest(_DecideRequest):
    """Từ chối một đơn đang chờ, kèm lý do."""

    async def execute(self, actor: HrmActor, request_id: UUID, reason: str) -> RequestView:
        request = await self._lay_don_va_kiem_quyen(actor, request_id)
        request.reject(actor.user_id, reason, self._clock.now())
        await self._request_repo.update(request)
        await self._notifier.notify_request_changed(
            request.id, request.requester_id, CHANGE_REQUEST_DECIDED
        )
        return _view(request)


class ListRequests:
    """Liệt kê đơn theo phạm vi.

    Staff: đơn của mình. Manager: đơn phòng mình (gồm đơn mình gửi). Admin: tất cả.
    """

    def __init__(self, request_repo: IRequestRepository) -> None:
        self._request_repo = request_repo

    async def execute(
        self,
        actor: HrmActor,
        status: RequestStatus | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> Page[RequestView]:
        if actor.role is ActorRole.STAFF:
            requester_id: UUID | None = actor.user_id
            department_ids: list[UUID] | None = None
        elif actor.role is ActorRole.MANAGER:
            requester_id = actor.user_id
            department_ids = [actor.department_id] if actor.department_id else []
        else:
            requester_id = None
            department_ids = None

        items = await self._request_repo.list_for_scope(
            requester_id, department_ids, status, limit, offset
        )
        total = await self._request_repo.count_for_scope(requester_id, department_ids, status)
        return Page(items=[_view(r) for r in items], total=total, limit=limit, offset=offset)


class GetRequest:
    """Xem chi tiết một đơn nếu người gọi được phép."""

    def __init__(self, request_repo: IRequestRepository) -> None:
        self._request_repo = request_repo

    async def execute(self, actor: HrmActor, request_id: UUID) -> RequestView:
        request = await self._request_repo.get_by_id(request_id)
        if request is None:
            raise _khong_thay()

        if actor.role is ActorRole.ADMIN:
            return _view(request)
        if actor.role is ActorRole.MANAGER:
            if (
                request.department_id == actor.department_id
                or request.requester_id == actor.user_id
            ):
                return _view(request)
        elif request.requester_id == actor.user_id:
            return _view(request)

        raise PermissionDeniedError("Bạn không có quyền xem đơn này.", code="REQUEST_FORBIDDEN")
