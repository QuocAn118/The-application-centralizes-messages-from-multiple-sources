# OmniChat #4 HRM — Implementation Plan

> **For agentic workers:** dùng subagent-driven-development, thực hiện task-by-task. Steps dùng checkbox (`- [ ]`). Mỗi task xong: test xanh + ruff/format/mypy/import-linter sạch, commit.

**Goal:** Cung cấp lớp quản lý nhân sự vận hành: ca làm việc + phân ca, KPI (mục tiêu do Manager đặt + thực đạt lấy từ Inbox qua port), và đơn từ nội bộ với phê duyệt một cấp. Module `hrm` độc lập, không import `identity` lẫn `inbox`.

**Spec:** [2026-07-26-omnichat-hrm-design.md](../specs/2026-07-26-omnichat-hrm-design.md)

**Tech Stack:** kế thừa Foundation + Inbox (Python 3.13 · FastAPI · SQLAlchemy 2.0 async · psycopg 3 · PostgreSQL 17 · Alembic · Pydantic v2 · uv · pytest · ruff · mypy · import-linter). **Không** thêm dependency mới — HRM thuần nội bộ, không adapter nền tảng ngoài, không crypto mới.

## Global Constraints

Kế thừa toàn bộ Global Constraints của [Foundation](2026-07-21-omnichat-foundation.md) và [Inbox](2026-07-24-omnichat-inbox.md) (event loop Windows qua `cau_hinh_event_loop()`, UUID v7 qua `new_id()`, `timestamptz` UTC, tên test tiếng Việt không dấu, mọi lệnh qua `uv run` trong `backend/`, coverage domain+application ≥ 90%). Bổ sung riêng cho #4:

- **Module mới `hrm` độc lập `identity` VÀ `inbox`.** `src/modules/hrm/**` **không được import** `src/modules/identity/**` lẫn `src/modules/inbox/**`. Tham chiếu User/Department chỉ qua `UUID` thuần. `import-linter` thêm 3 contract: hrm.domain vào contract "Domain khong duoc phu thuoc tang ngoai"; hrm.application vào "Application..."; layer hrm một chiều; và một **forbidden mới** cấm `hrm.{domain,application,presentation} → identity` và `→ inbox`.
- **KPI thực đạt vào qua port, không import inbox.** `hrm.domain` (hoặc application) định nghĩa `IPerformanceSource`; implementation ở `hrm/infrastructure` mới truy vấn dữ liệu inbox. Đổi nguồn (#2/#5) sau không đụng use case.
- **Thời gian là business rule ở domain.** Chồng ca, `end_time > start_time`, `leave_end >= leave_start`, ngày phân ca không ở quá khứ — đều kiểm trong domain entity, không ở router.
- **Đơn từ là máy trạng thái bất biến khi đã quyết.** `CHO_DUYET → DA_DUYET/TU_CHOI/DA_HUY`. Không duyệt lại đơn đã có quyết định. Từ chối bắt buộc kèm lý do.
- **Phê duyệt một cấp.** Đơn Staff → Manager phòng đó; đơn Manager → Admin. Định tuyến người duyệt qua `IWorkforceDirectory`.

## Bản đồ file (module hrm)

| Đường dẫn | Trách nhiệm |
|---|---|
| `src/modules/hrm/domain/value_objects/kpi.py` | `KpiMetricType`, `KpiSubjectType`, `KpiPeriod` (year+month) |
| `src/modules/hrm/domain/value_objects/request_kind.py` | `RequestType`, `RequestStatus` |
| `src/modules/hrm/domain/entities/shift.py` | `Shift` (mẫu ca, `end_time > start_time`) |
| `src/modules/hrm/domain/entities/shift_assignment.py` | `ShiftAssignment` (buổi làm theo ngày) + kiểm chồng ca |
| `src/modules/hrm/domain/entities/kpi_target.py` | `KpiTarget` |
| `src/modules/hrm/domain/entities/leave_request.py` | `LeaveRequest` (dùng cho mọi RequestType) + máy trạng thái |
| `src/modules/hrm/domain/repositories/` | Interface repo (Shift/ShiftAssignment/KpiTarget/Request) |
| `src/modules/hrm/domain/ports.py` | `IWorkforceDirectory`, `IPerformanceSource`, `IClock`, `INotifier` |
| `src/modules/hrm/application/actor.py` | `HrmActor` trung lập (user_id + role + department_id) — mẫu như `InboxActor` |
| `src/modules/hrm/application/authorization.py` | Quy tắc "ai xem/thao tác được gì" |
| `src/modules/hrm/application/use_cases/` | Một file một use case |
| `src/modules/hrm/application/dto/` | DTO (ShiftView, KpiProgressView, RequestView...) |
| `src/modules/hrm/infrastructure/models/` | SQLAlchemy ORM model (4 bảng) |
| `src/modules/hrm/infrastructure/mappers/` | ORM ↔ domain |
| `src/modules/hrm/infrastructure/repositories/` | Repository implementation |
| `src/modules/hrm/infrastructure/directory/workforce_directory.py` | `IdentityWorkforceDirectory` (chỗ duy nhất chạm identity) |
| `src/modules/hrm/infrastructure/performance/inbox_performance_source.py` | `InboxPerformanceSource` (chỗ duy nhất chạm inbox) |
| `src/modules/hrm/presentation/routers/shift_router.py` | REST ca + phân ca |
| `src/modules/hrm/presentation/routers/kpi_router.py` | REST KPI |
| `src/modules/hrm/presentation/routers/request_router.py` | REST đơn từ |
| `src/modules/hrm/presentation/schemas/` | Pydantic request/response |
| `src/modules/hrm/presentation/dependencies.py` | DI wiring, `get_actor` từ JWT |

## Danh sách Task

Thực hiện tuần tự. Mỗi giai đoạn review trước khi sang giai đoạn sau (theo cách #0/#1 đã làm).

### Giai đoạn 1 — Domain hrm (thuần, không I/O)

| Task | Nội dung | Deliverable kiểm chứng được |
|---|---|---|
| 1 | Value objects: `KpiMetricType`/`KpiSubjectType`/`KpiPeriod`, `RequestType`/`RequestStatus` | Unit test; import-linter thấy package hrm |
| 2 | Entity `Shift` (`end_time > start_time`, thuộc phòng) + `ShiftAssignment` (ngày không quá khứ, biết cách phát hiện chồng khung giờ) | Unit test: từ chối ca ngược giờ; phát hiện overlap hai assignment |
| 3 | Entity `KpiTarget` (subject + metric + kỳ + target_value ≥ 0) | Unit test bất biến |
| 4 | Entity `LeaveRequest` + máy trạng thái (CHO_DUYET→DA_DUYET/TU_CHOI/DA_HUY; NGHI_PHEP cần khoảng thời gian hợp lệ; từ chối cần lý do; không quyết lại) | Unit test toàn bộ chuyển trạng thái hợp lệ/không hợp lệ |
| 5 | Repository interfaces + ports (`IWorkforceDirectory`, `IPerformanceSource`, `IClock`, `INotifier`) + fakes in-memory | Fake dùng được trong test use case; import-linter cấm hrm→identity, hrm→inbox |

### Giai đoạn 2 — Use case (application, dùng fake)

| Task | Nội dung | Deliverable |
|---|---|---|
| 6 | `HrmActor` + `authorization` + Shift use cases: `CreateShift`/`UpdateShift`/`DeactivateShift`/`ListShifts` | Unit test: Manager chỉ phòng mình; Staff bị từ chối |
| 7 | `AssignShift` (chặn chồng ca + ngày quá khứ, kiểm nhân viên thuộc phòng qua directory) + `CancelShiftAssignment` + `ListShiftAssignments` | Unit test: chồng ca nổ; phân cho người khác phòng bị từ chối; phạm vi xem đúng |
| 8 | KPI use cases: `SetKpiTarget` + `ListKpiTargets` + `GetKpiProgress` (thực đạt qua `IPerformanceSource`, tính %) | Unit test: đặt/sửa mục tiêu; progress ghép target + actual từ fake source |
| 9 | Đơn từ: `SubmitRequest` (validate theo loại) + `CancelRequest` (chỉ khi CHO_DUYET, chỉ chủ đơn) | Unit test: NGHI_PHEP thiếu khoảng thời gian nổ; huỷ đơn đã quyết bị từ chối |
| 10 | Đơn từ: `ApproveRequest`/`RejectRequest` (định tuyến người duyệt qua directory, một cấp) + `ListRequests`/`GetRequest` + phát tín hiệu qua `INotifier` | Unit test: Manager duyệt đơn Staff phòng mình; Manager không duyệt đơn mình; đơn Manager do Admin duyệt; từ chối cần lý do |

### Giai đoạn 3 — Hạ tầng lưu trữ + nguồn ngoài

| Task | Nội dung | Deliverable |
|---|---|---|
| 11 | ORM models 4 bảng (`shifts`, `shift_assignments`, `kpi_targets`, `requests`) + Alembic migration | Integration test schema trên PostgreSQL thật (unique kpi, CHECK status, timestamptz, FK nội bộ shift_assignments→shifts) |
| 12 | Mappers + repository implementations | Integration test round-trip từng repository; truy vấn chồng ca theo (user_id, work_date) |
| 13 | `IdentityWorkforceDirectory` (chỗ duy nhất chạm identity; thêm `get_manager_of_department` để định tuyến duyệt) | Integration test: đọc phòng/nhân viên/Manager qua identity repo |
| 14 | `InboxPerformanceSource` (chỗ duy nhất chạm inbox; đếm hội thoại đóng / thời gian phản hồi theo user+kỳ) | Integration test: seed dữ liệu inbox → trả đúng metric |

### Giai đoạn 4 — HTTP + hoàn thiện

| Task | Nội dung | Deliverable |
|---|---|---|
| 15 | Shift router (CRUD ca + phân ca + xem lịch) + schemas + dependencies | e2e: Manager tạo ca/phân ca phòng mình; chồng ca 422; Staff xem lịch của mình |
| 16 | KPI router (đặt mục tiêu + xem progress) | e2e: Manager đặt target; GET progress trả target + actual + % |
| 17 | Request router (gửi/duyệt/từ chối/huỷ/xem) | e2e: Staff gửi → Manager duyệt/từ chối; đơn Manager → Admin duyệt; phân quyền theo phòng |
| 18 | Đăng ký router vào `create_app`, wiring DI (directory factory + performance source + notifier qua `app.state`), thêm import-linter contract, cập nhật CI/README | Toàn bộ test xanh; import-linter contract mới kept; e2e luồng đầy đủ |

## Ghi chú thực hiện

- **Ranh giới module (điểm rủi ro nhất, như #1 đã gặp):** `hrm.presentation` **không** import `IdentityWorkforceDirectory`/`InboxPerformanceSource` trực tiếp — wiring qua factory trong `app.state` ở composition root (`main.py`), presentation chỉ type theo port. Đây chính là bài học Phase 4 của #1 (import-linter bắt vi phạm khi presentation import implementation). Làm đúng ngay từ đầu.
- **`IPerformanceSource` — trade-off đã ghi (spec §10):** truy vấn theo yêu cầu, không cache. Nếu nặng, nợ materialized view/#5. Không vì thế mà cho hrm import inbox.
- **Nợ kỹ thuật chấp nhận (spec §10):** không chấm công thật; ca không qua nửa đêm; phê duyệt một cấp; loại đơn cố định; chồng ca chặn ở use case (nợ exclusion constraint DB); KPI không realtime.
- **Chỗ móc cho #3 (auto-assignment):** `ShiftAssignment` (ai trong ca hôm nay) + `KpiTarget`/progress (phòng nào còn dư năng lực) chính là dữ liệu #3 sẽ đọc để định tuyến. Giữ query "ai đang trong ca ngày X" dễ lấy.
- **Realtime đơn từ (spec §9):** làm tối thiểu — phát tín hiệu qua `INotifier` (port trung lập), wiring ở composition root có thể tái dùng bộ WS của #1 mà không import inbox. Nếu phức tạp, nợ realtime, trả trạng thái qua REST.

Chi tiết từng task (Files/Interfaces/Steps + code) sẽ viết khi bắt đầu từng giai đoạn, theo đúng cách #0/#1 đã làm.
