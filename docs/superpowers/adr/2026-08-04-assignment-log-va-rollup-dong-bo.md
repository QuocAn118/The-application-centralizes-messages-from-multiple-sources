# ADR 2026-08-04 — `assignment_log` và rollup #5 chạy đồng bộ

Trạng thái: **Chấp nhận** (2026-08-04). Bối cảnh: sau khi khép roadmap 0→1→4→2→3→5,
trả nợ kỹ thuật của #3/#5.

Hai quyết định độc lập được chốt trong đợt trả nợ:

---

## 1. `assignment_log` — nguồn sự thật cho `assigned_count` (ĐÃ LÀM)

### Vấn đề
`conversations.assigned_user_id` chỉ giữ **người cuối** của hội thoại. Khi một hội
thoại được gán lại (auto-assign nhiều lần, kéo hàng đợi), số lần gán thực sự không
tái dựng được từ bảng `conversations`. Báo cáo "hiệu suất nhân viên" của #5 cần
`assigned_count` đếm **đủ mọi lần gán** — nợ ghi từ GĐ1/GĐ3/GĐ4 của #5.

### Quyết định
Thêm bảng `assignment_log` (thuộc module #3 assignment), mỗi dòng là **một lần gán
thành công**:

- Ghi tại điểm DUY NHẤT một lần gán thực sự xảy ra: `InboxConversationAssigner.
  assign_to_agent` khi (và chỉ khi) inbox trả `AssignResult.ASSIGNED`. `ALREADY_TAKEN`
  và `REJECTED` KHÔNG ghi.
- Ghi **cùng session/giao dịch** với việc gán ở inbox: hoặc cùng commit, hoặc cùng
  rollback. Không có dòng log "ma" (log mà không gán) hay ngược lại.
- Bảng chỉ chứa UUID thuần (không khoá ngoại) — giữ #3 độc lập, chỉ tham chiếu inbox/
  identity qua UUID như mọi module khác.
- Cột: `conversation_id`, `user_id`, `department_id` (phòng lúc gán, cho audit),
  `assigned_at` (`timestamptz`).

### Cập nhật rollup `assigned_count`: **CHỈ backfill**, không hook incremental
- `RebuildDailyRollup` (qua `InboxStatsSource.agent_metrics_cho_ngay`) đếm dòng
  `assignment_log` theo `date(timezone(tz, assigned_at))` (event-time), gán theo
  **phòng HIỆN TẠI** của hội thoại (join `conversations`, quy tắc GĐ3 F-A) — KHÔNG
  dùng `department_id` trong log — để nhất quán với mọi metric nhân viên khác.
- KHÔNG thêm `post_assign_agent_hooks`. Lý do: điểm gán nằm sâu trong after-commit
  hook của #3 (post_ingest/post_close chạy trên session riêng); bắn một hook #5 qua
  ranh giới đó thêm phức tạp mà không đổi bản chất — `assignment_log` đã là nguồn sự
  thật. "Hôm nay" cập nhật qua `RebuildDailyRollup` định kỳ, đúng như các metric
  proxy khác (closed/resolution) vốn đã chịu độ trễ này.

### Hệ quả
- Đóng nợ `assigned_count = 0`. `assigned_count` giờ chính xác qua backfill.
- Là **nền cho KPI routing metric** sau này (KPI định tuyến cần lịch sử gán — giờ đã
  có). KPI vẫn là nợ mở, chưa làm trong đợt này.
- Nhận việc thủ công (`/take`) KHÔNG ghi log (không phải auto-assign) → `assigned_count`
  chỉ đếm việc do #3 tự gán. Đây là ngữ nghĩa mong muốn: "được hệ thống gán".

---

## 2. Rollup #5 chạy đồng bộ trong request — **GIỮ NGUYÊN** (chưa tách job nền)

### Vấn đề
Các hook incremental của #5 (`post_ingest`/`post_reply`/`post_close`) chạy **đồng bộ**
ngay trong request đã tạo ra sự kiện (trên session riêng, sau khi #1 commit). Về lâu
dài, tải cao có thể muốn tách rollup ra job nền (outbox/queue).

### Quyết định
**Giữ đồng bộ.** Không tách job nền ở thời điểm này.

Lý do:
- Tải hiện tại thấp; mỗi hook là vài câu UPSERT nhẹ.
- Hook đã **bọc try/except** (RB-1): rollup lỗi/chậm KHÔNG làm hỏng luồng chính
  (nhận tin/trả lời/đóng vẫn thành công). Rủi ro đã được cô lập.
- `RebuildDailyRollup` là lưới an toàn: mọi lệch/mất do hook đều sửa được bằng
  backfill từ nguồn sự thật.

### Khi nào nên tách (tiêu chí xét lại)
Chuyển sang job nền (ví dụ bảng `outbox` + worker, hoặc hàng đợi) khi BẤT KỲ điều nào
xảy ra:
- p95 độ trễ request có phần rollup vượt ngưỡng chấp nhận (đo, không đoán).
- Số hook mỗi request tăng (nhiều consumer hạ nguồn) khiến phần đồng bộ đáng kể.
- Cần đảm bảo **at-least-once** cho rollup (hiện tại: mất một lần bump thì chờ rebuild
  định kỳ — chấp nhận được cho read model báo cáo, không cho dữ liệu giao dịch).

### Hệ quả
- "Hôm nay" trên dashboard có thể trễ tới lần `RebuildDailyRollup` gần nhất cho các
  metric proxy (assigned_count, closed/resolution backfill). Chấp nhận cho báo cáo.
- Không thêm hạ tầng vận hành (worker/queue) chưa cần thiết.

---

## 3. KPI routing metric — ĐỊNH NGHĨA + NỐI (ĐÃ LÀM, bổ sung cùng ngày)

### Vấn đề
`kpi_percent` ở #3 (pool định tuyến, tiebreaker thứ 3) và #5 (báo cáo ca & KPI) đều
để `None` vì **chưa chốt định nghĩa** KPI định tuyến: đo chỉ số nào, kỳ nào, thiếu
target thì sao. #4 đã có đủ máy KPI (target + thực đạt + % theo chiều) nhưng hai
consumer này chưa nối.

### Quyết định (chốt nghiệp vụ)
- **Chỉ số**: `CONVERSATIONS_CLOSED` (% hoàn thành mục tiêu số hội thoại đóng). Người
  DƯỚI target được ưu tiên nhận thêm việc để đạt KPI — đúng tinh thần roadmap #3.
- **Kỳ**:
  - #3 pool: **tháng hiện tại** (theo `app_timezone`, thời điểm gán).
  - #5 workforce: **tháng của `to_date`** (kỳ KPI hiện hành ở cuối khoảng báo cáo);
    `period` ghi rõ `YYYY-MM`.
- **Thiếu target tháng đó** → `kpi_percent = None`. Ở #3, selector xử `None` như thấp
  nhất (trung tính giữa các ứng viên hoà tải) — giữ nguyên logic phá hoà.

### Thực hiện (không phá ranh giới module)
- Tách domain service `hrm.domain.services.kpi_achievement.tinh_phan_tram_kpi`
  (công thức % theo *chiều* chỉ số) — dùng CHUNG bởi `GetKpiProgress` (#4), pool
  (#3), workforce source (#5). Không nhân bản logic.
- #3 pool và #5 source dựng `SqlAlchemyKpiTargetRepository` + `InboxPerformanceSource`
  từ session sẵn có (như pool đã dựng shift repo) — wiring composition root KHÔNG đổi.
- import-linter vẫn 16 kept (assignment/analytics.infrastructure vốn được phép chạm
  #4).

### Nợ còn (kế thừa, KHÔNG phát sinh mới)
- Thực đạt `CONVERSATIONS_CLOSED` dùng `updated_at` proxy làm "mốc đóng" (nợ #4/#1,
  spec §10) — cần `closed_at` ở inbox mới chính xác tuyệt đối.
- `AVG_RESPONSE_MINUTES` thực đạt vẫn `None` ở #4 (`InboxPerformanceSource` chưa tính)
  — không dùng cho định tuyến nên không chặn.
