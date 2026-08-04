# OmniChat #5 Analytics & Dashboard — Thiết kế

**Trạng thái:** nháp để duyệt · **Ngày:** 2026-07-30 · **Phụ thuộc:** #1 Inbox, #2 Keyword, #3 Auto-Assignment, #4 HRM (đều đã merge `main`)

## 1. Mục tiêu

Cung cấp **báo cáo đa chiều** cho Manager/Admin: khối lượng tin nhắn & hội thoại, hiệu suất nhân viên, ca làm & KPI, đơn từ theo loại — cắt theo **phòng ban / nhân viên / loại / thời gian**. Đầu ra là **JSON API** trả số liệu tổng hợp; frontend Next.js vẽ biểu đồ sau (spec FE riêng). Đây là sub-project cuối của roadmap, đọc dữ liệu từ cả bốn module trước.

## 2. Phạm vi (đã chốt với user)

**Trong phạm vi — 4 chiều báo cáo:**
1. **Khối lượng tin/hội thoại** (#1): số tin inbound/outbound, số hội thoại mới/đóng — theo ngày, theo phòng, theo kênh (Zalo/Facebook/Instagram).
2. **Hiệu suất nhân viên** (#1 + #3): số hội thoại đã xử lý (đóng), thời gian phản hồi đầu tiên, thời gian tới khi đóng, tải trung bình — theo nhân viên.
3. **Ca làm & KPI** (#4): số ca làm, giờ công, tiến độ KPI (`achievement_percent`) — theo nhân viên/phòng.
4. **Đơn từ theo loại** (#4): số đơn theo `request_type` + trạng thái (chờ/duyệt/từ chối), thời gian duyệt trung bình.

**Kiến trúc đọc (đã chốt):** **read model riêng + bảng tổng hợp** — #5 có bảng rollup riêng (daily grain), cập nhật tăng dần (incremental) khi có sự kiện + có đường **backfill** để dựng lại từ dữ liệu nguồn.

**Đầu ra (đã chốt):** JSON API cho dashboard. **Không** xuất CSV ở bản đầu (nợ tương lai).

**Ngoài phạm vi (nợ/để sau):**
- Biểu đồ/dashboard UI (thuộc spec FE Next.js).
- Xuất CSV/Excel, báo cáo lịch gửi email.
- Real-time streaming metrics (bản đầu số liệu tươi tới *cuối ngày gần nhất* + phần hôm nay tính bù trực tiếp — xem §5).
- Phân tích dự báo/ML.

## 3. Kiến trúc & độc lập module

Module mới `analytics`, clean architecture 4 tầng như #2/#3. **Độc lập hai chiều** với inbox/hrm/identity/keyword/assignment:
- `analytics.{domain,application,presentation}` KHÔNG import module khác.
- Chỉ `analytics.infrastructure` chạm chúng qua **adapter port** (đọc dữ liệu nguồn để rollup).
- Chiều ngược: #0–#4 KHÔNG biết #5 tồn tại. import-linter thêm contract (giống #3): `analytics.{domain,application,presentation} → (inbox,hrm,identity,keyword,assignment)` cấm; `(inbox,hrm,identity,keyword,assignment) → analytics` cấm.

**#5 là hạ nguồn của tất cả** — nó đọc mọi module, không ai đọc nó.

**Cổng (port) chính (đọc nguồn để rollup):**
- `IConversationStatsSource` (đọc #1) — đếm tin/hội thoại theo ngày/phòng/kênh/nhân viên; mốc phản hồi & đóng.
- `IWorkforceStatsSource` (đọc #4) — ca làm, KPI theo nhân viên/phòng/kỳ.
- `IRequestStatsSource` (đọc #4) — đơn từ theo loại/trạng thái/thời gian duyệt.
- (identity chỉ để map tên phòng/nhân viên khi trình bày — qua directory sẵn có.)

## 4. Read model — bảng rollup riêng của #5

Bản đầu dùng **rollup theo ngày (daily grain)**, đủ cho mọi chiều báo cáo mà không phải quét bảng nguồn mỗi request.

**CHỐT với user:** chỉ **rollup #1** (conversation + agent) vào bảng riêng của #5; **ca/KPI (#4) và đơn từ (#4) đọc THẲNG bảng nguồn của #4 qua port khi query** (dữ liệu #4 vốn đã ở dạng tổng hợp — `KpiTarget`, `ShiftAssignment`, `Request` — không cần rollup lại). → chỉ **2 bảng rollup**:

- `analytics_daily_conversation` — khoá `(work_date, department_id, channel_platform)`: `inbound_count`, `outbound_count`, `opened_count`, `closed_count`.
- `analytics_daily_agent` — khoá `(work_date, user_id, department_id)`: `handled_count` (đóng), `sum_first_response_seconds`, `sum_resolution_seconds`, `response_samples` (để tính trung bình chuẩn xác), `assigned_count`. **`department_id` chụp lúc xử lý** (phòng của hội thoại) để lọc phòng thật cho báo cáo hiệu suất (RB-4) mà không phải join identity — chốt ở review GĐ1.

`GET /analytics/workforce` và `GET /analytics/requests` KHÔNG dùng bảng rollup — chúng gọi port đọc thẳng #4, tổng hợp (GROUP BY) tại query time.

**Trung bình tính từ tổng + đếm mẫu** (`sum/samples`) chứ không lưu sẵn "trung bình" — cộng dồn được qua nhiều ngày mà vẫn đúng.

## 5. Cập nhật read model — incremental + backfill

**Hai đường, một nguồn sự thật (bảng nguồn):**

1. **Incremental (tăng dần) qua hook composition-root** — tái dùng cơ chế `app.state.*_hooks` như #2/#3, KHÔNG để #1 import #5. **CHỐT với user:** dùng **nhiều list hook riêng** theo đúng pattern #2/#3 (không gom một list chung):
   - `post_ingest_hooks` (tin inbound mới, đã có) → cộng `inbound_count`.
   - `post_close_hooks` (đóng hội thoại, đã có) → cộng `closed_count`, `handled_count`, mốc `resolution`.
   - **`post_reply_hooks`** (MỚI — reply router phát khi gửi tin outbound) → cộng `outbound_count`, mốc `first_response`.
   - **`post_assign_agent_hooks`** (MỚI — khi hội thoại được gán một nhân viên) → cộng `assigned_count`. (Chỉ cần cho hiệu suất "số việc được gán"; đọc kỹ ở plan xem có nối được không mà không phá #1/#3.)
   - Vì ca/KPI/đơn đọc thẳng #4 (không rollup), KHÔNG cần hook cho #4.
   - Hook #5 cộng dồn vào bảng rollup của ngày tương ứng (UPSERT `+= delta`), trên **session riêng**, **nuốt lỗi** (rollup lỗi không được làm hỏng luồng chính — RB dưới).

2. **Backfill/recompute (dựng lại)** — use case `RebuildDailyRollup(work_date | range)` quét bảng nguồn qua port và **ghi đè** rollup ngày đó. Dùng khi: khởi tạo #5 trên dữ liệu cũ, hook lỡ sự kiện, hoặc số liệu lệch. Đây là **nguồn sự thật để đối chiếu**; incremental chỉ là tối ưu độ trễ.

**Quy tắc gắn ngày = event-time (chốt review GĐ2):** để incremental và backfill KHỚP nhau, mỗi số liệu gắn ngày của **hành động sinh ra nó**, không phải ngày mở hội thoại — `inbound` theo ngày tin khách; `outbound`/mẫu first_response theo ngày tin trả lời ĐẦU; `closed`/`handled`/mẫu resolution theo ngày ĐÓNG (đều đã quy đổi `app_timezone`). Ca qua nửa đêm: khách nhắn 23:00 ngày 1, trả lời 01:00 ngày 2 → first_response thuộc NGÀY 2. `InboxStatsSource` (GĐ3) phải group nguồn theo timestamp từng bản ghi, KHÔNG theo `conversations.created_at`.

**Quy tắc gán phòng (chốt review GĐ3):** mọi số liệu gán theo `conversations.department_id` **HIỆN TẠI** của hội thoại (cả incremental lẫn backfill), KHÔNG phải phòng lúc từng tin. Tin INBOUND đến khi hội thoại còn CHO_PHAN được tính cho phòng SAU KHI phân (dồn về phòng cuối) — nguồn #1 không lưu lịch sử phòng nên đây là mốc chung nhất quán. GĐ4 hook incremental đọc `conversation.department_id` hiện tại khi ghi, kể cả INBOUND.

**Số liệu "hôm nay":** rollup incremental cập nhật gần thời gian thực; nếu lo lệch, endpoint có thể tính phần **ngày hiện tại** trực tiếp từ nguồn và cộng với rollup các ngày đã đóng — chốt ở plan (đơn giản trước: đọc thẳng rollup, có `RebuildDailyRollup` chạy tay/định kỳ).

## 6. API (JSON, đọc-chỉ)

Tất cả dưới `/api/v1/analytics/*`, chỉ **Manager (phòng mình) / Admin (mọi phòng)** — Staff không xem báo cáo tổng hợp. Tham số chung: `from`, `to` (khoảng ngày), `department_id?` (Admin lọc; Manager ép về phòng mình).

- `GET /analytics/conversations` — khối lượng tin/hội thoại theo ngày, nhóm theo phòng/kênh.
- `GET /analytics/agents` — hiệu suất theo nhân viên (đóng, thời gian phản hồi/đóng, tải).
- `GET /analytics/workforce` — ca làm + KPI theo nhân viên/phòng.
- `GET /analytics/requests` — đơn theo loại/trạng thái + thời gian duyệt.
- `POST /analytics/rollups/rebuild` — Admin chạy backfill một khoảng ngày (vận hành).

Phân quyền thống nhất mô hình #2/#3: `pham_vi_phong_doc(actor)` (Admin = `None` không giới hạn; Manager/Staff = phòng mình) — nhưng #5 chặn Staff hẳn ở API tổng hợp.

## 7. Bất biến & quy tắc nghiệp vụ

- **RB-1 (tách lỗi):** cập nhật rollup incremental lỗi KHÔNG được làm hỏng luồng chính (nhận tin/đóng/duyệt). Hook nuốt lỗi, log; `RebuildDailyRollup` sửa lệch sau.
- **RB-2 (idempotent/cộng đúng):** rollup incremental là UPSERT cộng-delta; backfill là ghi-đè-tuyệt-đối. Không double-count: mỗi sự kiện chỉ cộng một lần (hook chỉ chạy cho sự kiện THẬT mới — kế thừa guard idempotency của #1 như #2 đã dùng: chỉ hook khi `ket_qua is not None`).
- **RB-3 (chỉ đọc nguồn):** #5 KHÔNG ghi vào bảng của module khác. Chỉ đọc + ghi bảng rollup riêng.
- **RB-4 (quyền):** báo cáo tổng hợp chỉ Manager/Admin; Manager bị ép phạm vi phòng mình (không xem phòng khác).
- **RB-5 (múi giờ):** `work_date` theo **giờ nghiệp vụ địa phương** (`app_timezone`, kế thừa nợ F1 của #3) — quy đổi UTC → local trước khi lấy ngày, để "ngày" của báo cáo khớp ngày làm việc VN.

## 8. Nợ chốt sẵn

- **Round-robin/`assignment_log` (#3 nợ):** hiệu suất "số việc được gán" của #5 suy từ `assigned_user_id` trên hội thoại — không có lịch sử gán chi tiết (một hội thoại đổi người nhiều lần chỉ thấy người cuối). Nếu cần chính xác lịch sử gán → thêm `assignment_log` (nợ #3, #5 sẽ hưởng). Ghi rõ giới hạn ở API.
- **Đồng bộ:** rollup incremental chạy trong request (kế thừa nợ hàng đợi nền của #2/#3). Với tải cao, tách job nền — nợ sau.
- **KPI kỳ:** `achievement_percent` của #4 gắn `period`; #5 báo cáo phải nêu rõ kỳ. Không tự nội suy giữa kỳ.
- **Số mẫu thời gian phản hồi:** chỉ tính khi có mốc rõ (tin khách đầu → tin nhân viên đầu). Hội thoại chưa phản hồi không vào mẫu (không kéo trung bình xuống sai).

## 9. Câu hỏi mở cho plan

- Cơ chế hook: thêm nhiều list (`post_reply_hooks`, `post_assign_hooks`, `post_request_decided_hooks`) hay một **`post_domain_event_hooks` chung** mang một event trung lập? (đề xuất: một list chung mang DTO sự kiện trung lập — gọn, dễ mở rộng cho #5; nhưng cân nhắc phá vỡ pattern hiện tại của #2/#3.)
- Rollup ca/KPI: rollup lại hay đọc thẳng #4 khi query? (đề xuất đọc thẳng #4 — dữ liệu đã tổng hợp; chỉ rollup #1 conversation/agent + #4 request.)
- "Hôm nay": đọc thẳng rollup (đơn giản) hay cộng bù ngày hiện tại từ nguồn? (đề xuất bản đầu đọc thẳng rollup + `RebuildDailyRollup` định kỳ; ghi nợ độ trễ.)
- Có cần alembic migration cho 3 bảng rollup ngay GĐ1 không (chắc chắn có) — chốt tên cột ở plan.
