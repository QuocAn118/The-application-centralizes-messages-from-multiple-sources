"""Xác nhận fake khớp đúng hợp đồng port/repository của hrm.

Nếu một port đổi chữ ký mà fake không theo, các phép gán dưới đây sẽ làm mypy
đỏ — bắt lệch hợp đồng ngay ở tầng test thay vì để lộ ra lúc chạy use case.
"""

from src.modules.hrm.domain.ports import (
    INotifier,
    IPerformanceSource,
    IWorkforceDirectory,
)
from src.modules.hrm.domain.repositories.kpi_target_repository import (
    IKpiTargetRepository,
)
from src.modules.hrm.domain.repositories.request_repository import IRequestRepository
from src.modules.hrm.domain.repositories.shift_assignment_repository import (
    IShiftAssignmentRepository,
)
from src.modules.hrm.domain.repositories.shift_repository import IShiftRepository
from tests.unit.hrm.fakes import (
    FakeKpiTargetRepository,
    FakeNotifier,
    FakePerformanceSource,
    FakeRequestRepository,
    FakeShiftAssignmentRepository,
    FakeShiftRepository,
    FakeWorkforceDirectory,
)


def test_fake_khop_hop_dong_port() -> None:
    _shift_repo: IShiftRepository = FakeShiftRepository()
    _assign_repo: IShiftAssignmentRepository = FakeShiftAssignmentRepository()
    _kpi_repo: IKpiTargetRepository = FakeKpiTargetRepository()
    _req_repo: IRequestRepository = FakeRequestRepository()
    _directory: IWorkforceDirectory = FakeWorkforceDirectory()
    _perf: IPerformanceSource = FakePerformanceSource()
    _notifier: INotifier = FakeNotifier()

    assert all(
        obj is not None
        for obj in (
            _shift_repo,
            _assign_repo,
            _kpi_repo,
            _req_repo,
            _directory,
            _perf,
            _notifier,
        )
    )
