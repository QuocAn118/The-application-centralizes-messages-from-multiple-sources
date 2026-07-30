# OmniChat #3 Auto-Assignment — Implementation Plan

> **For agentic workers:** subagent-driven-development, task-by-task. Steps dùng checkbox. Mỗi task xong: test xanh + ruff/format/mypy/import-linter sạch, commit. Mỗi giai đoạn review trước khi sang tiếp.

**Goal:** Sau khi hội thoại đã thuộc một phòng (#2 tự phân / Manager phân tay), tự chọn **một nhân viên** trong phòng theo chuỗi tiêu chí (đang trong ca → tải thấp nhất → chưa đủ KPI → round-robin) và gán qua use case của #1. Không ai hợp lệ → hội thoại nằm trong hàng đợi phòng, kéo lại khi có người rảnh/vào ca. Module `assignment` độc lập hai chiều với inbox/hrm/identity/keyword.

**Spec:** [2026-07-29-omnichat-autoassign-design.md](../specs/2026-07-29-omnichat-autoassign-design.md)

**Tech Stack:** kế thừa #0–#2, #4 (Python 3.13 · FastAPI · SQLAlchemy 2.0 async · psycopg 3 · PostgreSQL 17 · Alembic · Pydantic v2 · uv · pytest · ruff · mypy · import-linter). Không thêm dependency ngoài.

## Quyết định chốt (3 câu hỏi mở của spec)

- **Tên module:** `assignment`.
- **Endpoint HTTP:** CÓ — `POST /departments/{id}/auto-assign` cho Manager (phòng mình) / Admin chạy lại việc kéo hàng đợi một phòng thủ công. Ngoài ra vẫn chạy ngầm qua trigger.
- **Bảng `assignment_log`:** HOÃN. Bản đầu suy round-robin từ mốc gán trên hội thoại; không tạo bảng mới ở #3. Ghi nợ cho #5 nếu cần lịch sử phân việc chính xác.

## Global Constraints

Kế thừa toàn bộ Global Constraints #0–#4 (event loop Windows, UUID v7 `new_id()`, `timestamptz` UTC, tên test tiếng Việt không dấu, mọi lệnh qua `uv run` trong `backend/`, coverage domain+application ≥ 90%). Bổ sung cho #3:

- **Module `assignment` độc lập hai chiều.** `assignment.{domain,application,presentation}` KHÔNG import inbox/hrm/identity/keyword. VÀ inbox/hrm/identity/keyword KHÔNG import assignment (giữ #1/#2/#4 đóng băng; #3 là hạ nguồn). import-linter thêm: assignment.domain vào "Domain…"; assignment.application vào "Application…"; layer assignment một chiều; forbidden mới cấm `assignment.{domain,application,presentation} → inbox, hrm, identity, keyword`; và forbidden chiều ngược cấm `inbox, hrm, identity, keyword → assignment`.
- **Tự gán qua use case #1 với actor hệ thống** — không đụng máy trạng thái/realtime/phân quyền của #1. #3 chỉ "một Admin tự động chọn người".
- **Không cướp việc.** Chỉ gán hội thoại `DANG_MO` + `assigned_user_id IS NULL`; đã có người → bỏ qua (idempotent).
- **Tách lỗi.** Auto-assign lỗi (không ai trong ca, race) KHÔNG làm hỏng luồng gọi (webhook/đóng hội thoại) — nuốt lỗi, để hàng đợi. Nối trigger qua hook ở composition root (giống #2 với `post_ingest_hooks`).

## Bản đồ file (module assignment)

| Đường dẫn | Trách nhiệm |
|---|---|
| `src/modules/assignment/domain/value_objects/candidate.py` | `AgentCandidate` (user_id, on_shift, open_load, kpi_percent?, last_assigned_at?), `AssignmentOutcome` |
| `src/modules/assignment/domain/services/selector.py` | `chon_nhan_vien(candidates) -> UUID | None` — chuỗi tiêu chí thuần, không I/O |
| `src/modules/assignment/domain/ports.py` | `IAgentPool`, `IConversationAssigner`, `IWaitingQueue` + DTO cổng |
| `src/modules/assignment/application/actor.py` | `AssignmentActor` (trung lập) |
| `src/modules/assignment/application/use_cases/auto_assign_conversation.py` | Gán một hội thoại (trigger: vừa phân phòng) |
| `src/modules/assignment/application/use_cases/pull_department_queue.py` | Kéo hàng đợi một phòng cho (những) người rảnh |
| `src/modules/assignment/infrastructure/agent_pool/hrm_identity_pool.py` | `IAgentPool` — gom ca (#4) + tải (#1) + KPI (#4) + identity |
| `src/modules/assignment/infrastructure/inbox_bridge/conversation_assigner.py` | `IConversationAssigner` — gọi use case gán-agent của #1 |
| `src/modules/assignment/infrastructure/inbox_bridge/waiting_queue.py` | `IWaitingQueue` — đọc hàng đợi phòng |
| `src/modules/assignment/infrastructure/inbox_bridge/post_assign_hook.py` | Hook: sau khi phân phòng / đóng hội thoại → auto-assign |
| `src/modules/assignment/presentation/routers/assignment_router.py` | `POST /departments/{id}/auto-assign` |
| `src/modules/assignment/presentation/{schemas,dependencies}.py` | Pydantic + DI factory |
| `src/modules/inbox/application/use_cases/assign_conversation_to_agent.py` | **MỚI ở #1**: gán một hội thoại cho một nhân viên bất kỳ (actor Manager/Admin/hệ thống) |

## Danh sách Task

### Giai đoạn 1 — Domain assignment (thuần, không I/O)

| Task | Nội dung | Deliverable |
|---|---|---|
| 1 | `AgentCandidate` + `AssignmentOutcome` (value objects) | Unit test bất biến |
| 2 | `selector.chon_nhan_vien` — chuỗi tiêu chí: lọc on_shift → min open_load → min kpi_percent (None = thấp nhất, ưu tiên) → round-robin theo last_assigned_at (None/cũ nhất trước) | Unit test: mỗi tiêu chí phá hoà đúng thứ tự; rỗng → None; on_shift lọc trước tất cả |
| 3 | Ports (`IAgentPool`, `IConversationAssigner`, `IWaitingQueue`) + DTO cổng + fakes | Fake dùng được; import-linter cấm assignment→(inbox,hrm,identity,keyword) + chiều ngược |

### Giai đoạn 2 — Use case (application, dùng fake)

| Task | Nội dung | Deliverable |
|---|---|---|
| 4 | `AutoAssignConversation` (nhận conversation_id + department_id; RB-1 chỉ khi chưa gán; lấy candidates từ IAgentPool; selector chọn; gán qua IConversationAssigner; không ai → để hàng đợi; nuốt lỗi) | Unit: gán người hợp lệ; không ai trong ca → không gán, không lỗi; đã có người → bỏ qua; race gán-thất-bại → không ném |
| 5 | `PullDepartmentQueue` (cho một hoặc nhiều người rảnh: lấy hàng đợi phòng chờ lâu nhất, gán lần lượt tới khi hết người/hết việc) | Unit: kéo đúng thứ tự chờ; dừng khi hết ứng viên |

### Giai đoạn 3 — Hạ tầng: use case #1 mới + cầu nối ✅ XONG

| Task | Nội dung | Deliverable |
|---|---|---|
| 6 ✅ | **#1**: `AssignConversationToAgent` use case (Manager/Admin/hệ thống gán một nhân viên vào hội thoại `DANG_MO`; kiểm agent active + đúng phòng hội thoại qua directory; dùng `assign_to_agent`; notify) | 9 unit test #1: gán được; Staff 403; khác phòng chặn; nhân viên sai phòng/không active chặn; đã có người chặn |
| 7 ✅ | `HrmIdentityAgentPool` (`IAgentPool`): STAFF+MANAGER active của phòng (identity) → on_shift (shift #4 hôm nay bao giờ hiện tại), open_load (đếm DANG_MO gán họ — #1), last_assigned_at (max updated_at hội thoại đã gán họ — #1). **kpi_percent = None (NỢ)**: KPI đủ nghĩa cần chốt chỉ số/kỳ/nguồn (quyết định nghiệp vụ chưa có); selector xử None trung tính | Integration: gom đúng on_shift + tải trên PostgreSQL thật |
| 8 ✅ | `InboxConversationAssigner` (gọi `AssignConversationToAgent` #1 với actor hệ thống ADMIN, nuốt DomainError/ApplicationError→False) + `InboxWaitingQueue` (đọc DANG_MO chưa gán của phòng, sắp chờ-lâu-nhất-trước theo last_message_at) | Integration: gán được; khước từ khi đã có người→False; hàng đợi đúng thứ tự |

### Giai đoạn 4 — HTTP + wiring + trigger ✅ XONG

| Task | Nội dung | Deliverable |
|---|---|---|
| 9 ✅ | `assignment_router` `POST /departments/{id}/auto-assign` + schemas (`PullQueueResponse`) + dependencies (`get_actor` trung lập qua token_service + directory factory ở app.state; `build_pull_department_queue` qua factory) + authorization `bao_dam_dieu_phoi_duoc_phong` (Admin mọi phòng / Manager phòng mình / Staff 403) | e2e: Manager kéo hàng đợi phòng mình (200, assigned=1); Staff 403; Manager phòng khác 403 |
| 10 ✅ | **Wiring + trigger**: `_wire_assignment` trong main.py (truyền `settings.app_timezone` vào pool — nợ F1); hai builder ở `pull_queue_factory.py`; đăng ký hook vào `app.state`: (a) `post_ingest_hooks` — hook #3 đăng ký SAU hook #2 nên chạy sau, đọc hội thoại (DANG_MO + có phòng + chưa ai) → `AutoAssignConversation`; (b) `post_close_hooks` (list MỚI) — close router gọi với `department_id` → `PullDepartmentQueue`. #1/#2 KHÔNG import #3 (webhook/close router chỉ gọi callable ở app.state). import-linter 13 kept. | e2e: khách nhắn → #2 phân phòng → #3 tự gán nhân viên đang trong ca; không ai trong ca → hàng đợi (assigned_user_id NULL); nhân viên đóng việc → kéo việc kế |

**Cơ chế trigger đã chốt (task 10):**
- **(a) Phân phòng → tự gán:** KHÔNG thêm `post_assign_department_hooks` riêng. Tái dùng luồng `post_ingest_hooks` — đăng ký hook #3 *sau* hook #2 trong `create_app` (thứ tự list = thứ tự chạy). Hook #3 đọc trạng thái hội thoại hiện tại trên session riêng (sau khi #2 commit phân phòng): chỉ gán khi `DANG_MO` + có `department_id` + `assigned_user_id IS NULL`. Bắt luôn được cả đường #2-webhook lẫn bất kỳ tin mới nào rơi vào phòng chưa ai nhận, mà không sửa hợp đồng #1/#2. Manager phân/nhận tay qua HTTP là đường người-điều-khiển riêng (họ có thể tự chọn nhân viên); endpoint `POST /auto-assign` phủ trường hợp kéo thủ công.
- **(b) Đóng hội thoại → kéo hàng đợi:** thêm `app.state.post_close_hooks`; `dong_hoi_thoai` (inbox.presentation) commit thao tác đóng rồi gọi các hook với `department_id` của hội thoại vừa đóng (giống webhook router gọi `post_ingest_hooks`). Hook #3 (`assignment.infrastructure`) chạy `PullDepartmentQueue` trên session riêng, nuốt lỗi. inbox.presentation KHÔNG import assignment.

**Review GĐ4 (1 fix):** F-C — cả close router (post_close) lẫn webhook router (post_ingest) gọi hook "trần": tuy các hook #2/#3 đều tự nuốt lỗi, nhưng nếu về sau thêm một hook mới lỡ ném lỗi thì thao tác chính đã thành công (đã commit + notify) lại trả 500. Sửa: bọc `try/except Exception` (log rồi bỏ qua) quanh vòng lặp gọi hook ở CẢ HAI router — thao tác chính không bao giờ bị hook làm hỏng, không phụ thuộc ngầm "hook tự nuốt lỗi". Soi thêm và xác nhận AN TOÀN: thứ tự hook #3 sau #2 (list=thứ tự chạy, mỗi hook await tuần tự, session riêng sau commit); không cướp việc (guard DANG_MO+có phòng+chưa ai ở đọc-thời-điểm); reopen giữ assignee cũ nên #3 bỏ qua đúng; PullQueue một session atomic, bump tải trong bộ nhớ; `expire_on_commit=False` nên `phan_hoi` build trước commit vẫn đọc được; notify-trước-commit là nợ pre-existing chung toàn codebase (không phải lỗi GĐ4).

## Ghi chú thực hiện

- **Điểm móc trigger (rủi ro nhất, như #2 GĐ4):** #3 cần chạy sau hai sự kiện của #1: "hội thoại vừa được gán phòng" và "hội thoại vừa đóng". Cả hai phải nối qua hook ở composition root để #1 không import #3.
  - *Phân phòng:* #2 tự phân qua `InboxConversationRouter` (gọi `AssignConversationToDepartment`). Chèn hook sau bước đó — hoặc mở rộng `post_ingest_hooks` để hook #3 chạy tiếp sau hook #2, hoặc thêm một danh sách hook riêng `post_assign_department_hooks` mà cả #2-router-bridge lẫn #1-Manager-assign gọi. Quyết ở task 10; ưu tiên một cơ chế hook chung ở app.state, tránh sửa hợp đồng #1/#2.
  - *Đóng hội thoại:* thêm `post_close_hooks` mà `CloseConversation` (hoặc webhook/HTTP router gọi close) kích hoạt. Cân nhắc: có thể cần một điểm hook mỏng ở composition. Ghi rõ khi làm.
- **Actor hệ thống:** `InboxConversationAssigner` gọi use case #1 với `InboxActor` vai ADMIN (giống #2). Ghi rõ đây là hành động tự động của #3.
- **F1 nợ #2 GĐ4 (quyền định tuyến):** #3 auto-assign CHỈ trong phòng của hội thoại (RB-2). Endpoint kéo hàng đợi giới hạn Manager theo phòng mình / Admin toàn cục — thống nhất mô hình quyền, ghi rõ ở task 9.
- **Round-robin bản đầu:** suy `last_assigned_at` từ `max(updated_at)` hội thoại đã gán mỗi nhân viên (query #1). Không tạo `assignment_log`; nợ cho #5 nếu cần chính xác tuyệt đối.
- **NỢ KPI (chốt GĐ3):** `HrmIdentityAgentPool` để `kpi_percent = None`. Tính KPI đủ nghĩa cần chốt *một chỉ số định tuyến chuẩn* + kỳ + nguồn hiệu suất — quyết định nghiệp vụ chưa có, và `GetKpiProgress` #4 đòi metric_type/period/actor cụ thể (quá nặng cho một quyết định routing per-hội-thoại). KPI là tiêu chí phá hoà **thứ 3**; `None` được selector xử như thấp nhất (trung tính giữa các ứng viên hoà tải) nên bỏ trống vẫn giữ đúng thứ tự ưu tiên ca→tải→(kpi)→round-robin. Nối KPI thật khi nghiệp vụ chốt chỉ số chuẩn.
- **Tải (open_load):** đếm hội thoại `DANG_MO` có `assigned_user_id = agent` — cần một truy vấn đếm-theo-agent (bổ sung ở bridge hoặc repo #1 nếu thiếu; ưu tiên đọc qua repo có sẵn, không đổi hợp đồng #1 nếu tránh được).
- **Đồng bộ:** trigger chạy trong request (webhook/close) — kế thừa nợ "xử lý đồng bộ" của #2; tách hàng đợi nền để sau.
- **Chốt sau review GĐ3:**
  - *(F1 — BUG đã sửa)* Kiểm "đang trong ca" ban đầu so **giờ UTC** của `now()` với giờ ca — mà giờ ca (#4) nhập theo **giờ nghiệp vụ địa phương** (VN, UTC+7). Lệch đúng offset → gần như không ai được coi trong ca. Sửa: thêm config `APP_TIMEZONE` (mặc định `Asia/Ho_Chi_Minh`); `HrmIdentityAgentPool` nhận `timezone`, quy đổi `now().astimezone(tz)` trước khi so (lấy ngày+giờ sau khi đổi). Có regression test. **GĐ4 phải truyền `settings.app_timezone` vào pool khi wiring.**
  - *(F3 — ghi nợ)* `last_assigned_at` = `max(updated_at)` là **proxy thô** ("mốc hoạt động gần nhất", không phải "mốc gán" — `updated_at` bị bước bởi close/tin-mới/gán). Round-robin (tiebreaker thứ 4) lệch nhỏ; `assignment_log` (#5) mới chính xác. Đã sửa docstring cho đúng.
  - *(F2 — note)* `candidates_for_department` là N+1 (3 truy vấn/nhân viên). Chấp nhận bản đầu; gộp truy vấn tổng hợp theo phòng để sau.
- **Chốt sau review GĐ1+GĐ2:**
  - *(F-A — đã sửa)* `IConversationAssigner.assign_to_agent` cũ trả `bool`, gộp "vừa có người nhận (race)" và "bị từ chối" thành một → use case luôn trả `QUEUED`, báo sai hội thoại đã-có-chủ là đang-chờ; enum `SKIPPED` thành dead code. Sửa: port trả `AssignResult` (ASSIGNED/ALREADY_TAKEN/REJECTED); bridge bắt `AlreadyAssignedError`→ALREADY_TAKEN, lỗi khác→REJECTED; `AutoAssignConversation` map ALREADY_TAKEN→SKIPPED, REJECTED→QUEUED; `PullDepartmentQueue` chỉ tăng tải+đếm khi ASSIGNED.
  - *(F-B — đã sửa)* Selector khi hoà hoàn toàn (mọi tiêu chí bằng, kể cả `last_assigned_at=None`) phụ thuộc thứ tự caller. Thêm `user_id` làm khoá sắp xếp cuối → tất định, bỏ ràng buộc ngầm.

Chi tiết từng task (Files/Interfaces/Steps + code) viết khi bắt đầu từng giai đoạn, theo cách #0–#4 đã làm.
