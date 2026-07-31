# OmniChat #5 Analytics & Dashboard — Implementation Plan

> **For agentic workers:** task-by-task. Mỗi task xong: test xanh + ruff/format/mypy/import-linter sạch, commit. Mỗi giai đoạn review trước khi sang tiếp (nhịp #0–#4).

**Goal:** JSON API báo cáo đa chiều (khối lượng tin/hội thoại, hiệu suất nhân viên, ca/KPI, đơn từ) cho Manager/Admin. Read model: 2 bảng rollup ngày cho #1 (conversation + agent), cập nhật incremental qua hook + backfill; ca/KPI/đơn đọc thẳng #4 khi query. Module `analytics` độc lập hai chiều với mọi module.

**Spec:** [2026-07-30-omnichat-analytics-design.md](../specs/2026-07-30-omnichat-analytics-design.md)

**Tech Stack:** kế thừa #0–#4 (Python 3.13 · FastAPI · SQLAlchemy 2.0 async · psycopg 3 · PostgreSQL 17 · Alembic · Pydantic v2 · uv · pytest · ruff · mypy · import-linter). Không thêm dependency ngoài.

## Quyết định chốt (với user)

- **Kiến trúc đọc:** read model riêng + bảng rollup (daily). Chỉ rollup #1 (conversation + agent). Ca/KPI/đơn (#4) **đọc thẳng** #4 qua port khi query.
- **Phạm vi:** 4 chiều — khối lượng tin/hội thoại, hiệu suất nhân viên, ca & KPI, đơn theo loại.
- **Đầu ra:** JSON API. Không CSV bản đầu.
- **Hook incremental:** **nhiều list riêng** theo pattern #2/#3 (`post_reply_hooks`, `post_assign_agent_hooks` MỚI + `post_ingest`/`post_close` sẵn có). Không gom một list chung.

## Global Constraints

Kế thừa toàn bộ #0–#4 (event loop Windows, UUID v7 `new_id()`, `timestamptz` UTC, tên test tiếng Việt không dấu, mọi lệnh qua `uv run` trong `backend/`, coverage domain+application ≥ 90%). Bổ sung cho #5:

- **Module `analytics` độc lập hai chiều.** `analytics.{domain,application,presentation}` KHÔNG import inbox/hrm/identity/keyword/assignment. VÀ không module nào import analytics (#5 là hạ nguồn của tất cả). import-linter thêm: analytics.domain vào "Domain…"; analytics.application vào "Application…"; layer analytics một chiều; forbidden `analytics.{domain,application,presentation} → (inbox,hrm,identity,keyword,assignment)`; forbidden chiều ngược `(inbox,hrm,identity,keyword,assignment) → analytics`.
- **Chỉ đọc nguồn, ghi rollup riêng** (RB-3). #5 KHÔNG ghi bảng module khác.
- **Tách lỗi** (RB-1): hook rollup lỗi KHÔNG làm hỏng luồng chính — nuốt lỗi, `RebuildDailyRollup` sửa lệch.
- **`work_date` theo `app_timezone`** (RB-5): quy đổi UTC→local trước khi lấy ngày (kế thừa nợ F1 #3).

## Bản đồ file (module analytics)

| Đường dẫn | Trách nhiệm |
|---|---|
| `src/modules/analytics/domain/value_objects/metrics.py` | VO số liệu: `DailyConversationMetric`, `DailyAgentMetric`, `AgentPerformance`, `ConversationVolume`… (trung lập, không I/O) |
| `src/modules/analytics/domain/services/aggregation.py` | Gộp/không-đổi thuần: cộng delta, tính trung bình `sum/samples`, gộp nhiều ngày |
| `src/modules/analytics/domain/ports.py` | `IConversationStatsSource`, `IWorkforceStatsSource`, `IRequestStatsSource`, `IRollupRepository` |
| `src/modules/analytics/application/actor.py` | `AnalyticsActor` trung lập + `pham_vi_phong_doc` |
| `src/modules/analytics/application/authorization.py` | Manager/Admin đọc; Manager ép phòng mình; Staff chặn |
| `src/modules/analytics/application/use_cases/get_conversation_report.py` | Đọc rollup conversation theo khoảng ngày/phòng/kênh |
| `src/modules/analytics/application/use_cases/get_agent_report.py` | Đọc rollup agent (hiệu suất) |
| `src/modules/analytics/application/use_cases/get_workforce_report.py` | Đọc thẳng #4 (ca+KPI) qua port |
| `src/modules/analytics/application/use_cases/get_request_report.py` | Đọc thẳng #4 (đơn) qua port |
| `src/modules/analytics/application/use_cases/rebuild_daily_rollup.py` | Backfill: quét nguồn #1 → ghi đè rollup một khoảng ngày |
| `src/modules/analytics/application/use_cases/apply_event_delta.py` | Incremental: cộng delta vào rollup ngày (dùng bởi hook) |
| `src/modules/analytics/infrastructure/models/rollup_models.py` | `AnalyticsDailyConversationModel`, `AnalyticsDailyAgentModel` |
| `src/modules/analytics/infrastructure/repositories/rollup_repository.py` | `IRollupRepository` — UPSERT cộng-delta + ghi-đè + đọc |
| `src/modules/analytics/infrastructure/sources/inbox_stats_source.py` | `IConversationStatsSource` — quét #1 cho backfill |
| `src/modules/analytics/infrastructure/sources/hrm_stats_source.py` | `IWorkforceStatsSource` + `IRequestStatsSource` — đọc thẳng #4 |
| `src/modules/analytics/infrastructure/hooks/*.py` | Hook incremental (post_ingest/close/reply/assign) → `ApplyEventDelta` |
| `src/modules/analytics/presentation/routers/analytics_router.py` | 5 endpoint JSON + rebuild |
| `src/modules/analytics/presentation/{schemas,dependencies}.py` | Pydantic + DI |
| `migrations/versions/*_tao_bang_analytics_rollup.py` | 2 bảng rollup |
| `src/modules/inbox/presentation/routers/inbox_router.py` | Thêm `post_reply_hooks` (reply) + `post_assign_agent_hooks` (nếu nối được) — chỉ gọi callable app.state |

## Danh sách Task

### Giai đoạn 1 — Domain analytics (thuần, không I/O) ✅ XONG

| Task | Nội dung | Deliverable |
|---|---|---|
| 1 ✅ | VO metrics (`DailyConversationMetric`, `DailyAgentMetric`, `ConversationVolume`, `AgentPerformance`) + `DateRange` (from ≤ to) | Unit test bất biến |
| 2 ✅ | `aggregation`: gộp nhiều ngày, trung bình `sum/samples` (chia 0 → None) | Unit: gộp đúng; mẫu 0 → không lỗi |
| 3 ✅ | Ports (`IConversationStatsSource`, `IWorkforceStatsSource`, `IRequestStatsSource`, `IRollupRepository`) + `EventKind` + DTO trung lập + fakes; import-linter cấm analytics→(mọi module) + chiều ngược | Fake dùng được; 16 kept |

**Review GĐ1 (1 fix — F-A):** rollup agent khoá `(work_date, user_id)` KHÔNG mang `department_id` nhưng `doc_agent(khoang, department_ids)` lại nhận tham số lọc phòng (fake âm thầm bỏ qua) → Manager sẽ thấy nhân viên MỌI phòng (rò quyền RB-4) hoặc GĐ3 phải join identity (phá thiết kế "rollup chỉ #1"). **Chốt: thêm `department_id` vào `DailyAgentMetric` + khoá bảng agent** (chụp lúc xử lý, giống rollup conversation) → `doc_agent` lọc phòng THẬT, không join identity. Đã sửa VO + fake (`bump_agent`/`ghi_de_agent_ngay` khoá 3 phần, `doc_agent` lọc phòng thật) + test. **GĐ3: bảng `analytics_daily_agent` PHẢI có cột `department_id` trong PK; GĐ4 hook CLOSED/ASSIGNED phải điền department_id của hội thoại.**

### Giai đoạn 2 — Use case (application, dùng fake) ✅ XONG

| Task | Nội dung | Deliverable |
|---|---|---|
| 4 ✅ | `ApplyEventDelta` (nhận `EventKind` + `EventContext`; dựng delta conversation/agent theo loại; OUTBOUND chỉ tính mẫu first_response khi có `seconds`=tin đầu; CLOSED +handled, +resolution nếu có seconds; ASSIGNED +assigned) + `RebuildDailyRollup` (lặp từng ngày, ghi đè tuyệt đối kể cả nguồn rỗng) | Unit: cộng đúng từng loại; rebuild ghi đè idempotent, nguồn rỗng xoá số cũ |
| 5 ✅ | `GetConversationReport` (nhóm theo phòng/kênh rồi `gop_khoi_luong`), `GetAgentReport` (`gop_hieu_suat_nhan_vien`) đọc rollup; `GetWorkforceReport`, `GetRequestReport` đọc thẳng #4; `actor.py` + `authorization` (`bao_dam_xem_bao_cao`, `pham_vi_phong_bao_cao` — Manager ép phòng mình, Admin lọc tuỳ chọn, Staff/Manager-không-phòng chặn) | Unit: Admin thấy mọi phòng; Manager ép phòng mình dù truyền phòng khác; Staff `PermissionDeniedError` |

44 unit test analytics; 817 passed/1 skipped; ruff/format/mypy strict; import-linter 16 kept.

### Giai đoạn 3 — Hạ tầng: bảng rollup + source + migration

| Task | Nội dung | Deliverable |
|---|---|---|
| 6 | 2 model rollup + migration alembic (chạy `upgrade head` trên DB test) | Migration lên/xuống sạch |
| 7 | `SqlAlchemyRollupRepository` (UPSERT cộng-delta qua `ON CONFLICT DO UPDATE SET col = col + :delta`; ghi-đè; đọc theo range) | Integration trên PostgreSQL thật: cộng-delta + ghi-đè đúng |
| 8 | `InboxStatsSource` (quét #1 cho backfill: đếm tin/hội thoại/mốc theo ngày local) + `HrmStatsSource` (đọc thẳng ShiftAssignment/KpiTarget/Request, GROUP BY) | Integration: backfill khớp; đọc #4 đúng |

### Giai đoạn 4 — HTTP + wiring + trigger

| Task | Nội dung | Deliverable |
|---|---|---|
| 9 | `analytics_router` 5 endpoint (`/analytics/conversations|agents|workforce|requests`, `POST /analytics/rollups/rebuild`) + schemas + dependencies (actor trung lập, factory) | e2e: Manager phòng mình xem được; Staff 403; Manager phòng khác bị ép phạm vi |
| 10 | **Wiring + trigger**: `_wire_analytics` (đọc `settings.app_timezone`); đăng ký hook incremental vào `post_ingest`/`post_close`/`post_reply`(MỚI)/`post_assign_agent`(MỚI) — #1 KHÔNG import #5; thêm 2 list hook mới + điểm gọi ở inbox router (reply/gán). import-linter contract. | e2e: khách nhắn → rollup inbound +1; nhân viên trả lời → outbound +1; đóng → closed/handled +1; rebuild khớp incremental |

## Ghi chú thực hiện

- **Điểm móc trigger (rủi ro nhất, như #2/#3 GĐ4):** `post_reply_hooks` + `post_assign_agent_hooks` là điểm mới ở inbox router; theo đúng pattern `post_close_hooks` (GĐ4 #3): router gọi callable app.state trong try/except, KHÔNG import analytics. Nếu `post_assign_agent` khó nối sạch (gán xảy ra ở nhiều đường: TakeConversation, AssignConversationToAgent), cân nhắc chỉ rollup `assigned_count` qua backfill (suy từ `assigned_user_id`) và HOÃN hook gán — ghi nợ. Chốt khi làm GĐ4.
- **work_date theo tz** (RB-5): `ApplyEventDelta` và `InboxStatsSource` đều quy đổi UTC→`app_timezone` trước khi lấy ngày — nhất quán để incremental & backfill khớp nhau. Regression test đối chiếu.
- **RB-1 tách lỗi:** mọi hook nuốt lỗi + log; router bọc try/except (đã có thói quen từ #3 F-C).
- **RB-2 không double-count:** hook chỉ chạy cho sự kiện THẬT mới (kế thừa guard `ket_qua is not None` của #1 như #2/#3). Backfill ghi-đè tuyệt đối (không cộng dồn lên số cũ).
- **Nợ (ghi sẵn):** (a) `assignment_log` chưa có → hiệu suất "được gán" chỉ thấy người cuối; (b) rollup chạy đồng bộ trong request (nợ hàng đợi nền); (c) "hôm nay" đọc thẳng rollup, cần `RebuildDailyRollup` định kỳ (nợ độ trễ); (d) không CSV.
- Chi tiết từng task (Files/Interfaces/Steps + code) viết khi bắt đầu từng giai đoạn, theo cách #0–#4.
