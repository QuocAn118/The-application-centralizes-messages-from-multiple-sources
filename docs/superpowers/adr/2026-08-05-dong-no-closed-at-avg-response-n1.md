# ADR 2026-08-05 — Đóng nợ: `closed_at`, AVG_RESPONSE_MINUTES, N+1 pool

Trạng thái: **Chấp nhận / Đã làm** (2026-08-05). Bối cảnh: user yêu cầu "xử lý tất cả
nợ 1 lần". Sau khi quét toàn bộ marker nợ, phân loại thành nợ XỬ LÝ ĐƯỢC (A/C/D) và
nợ là QUYẾT ĐỊNH ĐÃ CHỐT (E/F/G — giữ nguyên). Đợt này làm A+C+D.

## A. `closed_at` — mốc đóng chính xác (nợ GỐC)

### Vấn đề
`conversations` không có cột mốc đóng riêng → #4 KPI (`CONVERSATIONS_CLOSED`) và #5
backfill (closed/handled/resolution) suy mốc đóng từ `updated_at` (proxy). Lệch hai
chiều: (1) đóng rồi khách nhắn lại (→ DANG_MO) không đếm; (2) đóng kỳ trước nhưng bị
cập nhật kỳ này (vẫn DA_DONG) đếm nhầm sang kỳ này.

### Quyết định
Thêm cột `conversations.closed_at` (nullable — mở rộng tương thích ngược, KHÔNG phá
schema #1 hiện có). `Conversation.close()` đặt `closed_at`; `register_incoming()` khi
mở lại XOÁ về NULL (không còn là "đã xử lý xong"). Migration `c3d4e5f6a7b8` backfill
dòng cũ `DA_DONG`: `closed_at = updated_at` (giữ đúng proxy cũ cho lịch sử).

Consumer đọc `COALESCE(closed_at, updated_at)`:
- #4 `InboxPerformanceSource._dem_hoi_thoai_dong`: lọc ngày theo mốc đóng đó.
- #5 `InboxStatsSource`: closed (conversation_metrics) + handled/resolution
  (agent_metrics) theo mốc đóng đó; `resolution = closed_at - created_at`.

### Hệ quả
Backfill #5 giờ KHỚP incremental (hook post_close vốn đọc `ClosedConversation.
closed_at` = đúng mốc). Đóng nợ "backfill xấp xỉ updated_at" ở cả #4 và #5. `opened`
vẫn xấp xỉ `created_at` (mở ≈ tạo — sát, giữ nguyên).

## C. AVG_RESPONSE_MINUTES thực đạt (#4)

### Vấn đề
`InboxPerformanceSource.get_metric_for_*` trả `None` cho chỉ số này → KPI thời gian
phản hồi không tính được, progress luôn "chưa có dữ liệu".

### Quyết định
Tính: mỗi hội thoại lấy giây từ tin INBOUND đầu tới tin OUTBOUND đầu; trung bình đổi
ra PHÚT (làm tròn 0.1). Event-time theo NGÀY tin OUTBOUND đầu (khớp #5). KPI cấp nhân
viên quy cho NGƯỜI gửi tin OUTBOUND đầu (người phản hồi, lấy `array_agg(... ORDER BY
created_at)[1]` vì Postgres không có `min(uuid)`); cấp phòng theo phòng hội thoại.
`None` khi chưa có mẫu. Chỉ số này "càng thấp càng tốt" — `tinh_phan_tram_kpi` đã xử
đúng chiều (target/actual*100).

## D. Gộp N+1 trong agent pool (#3)

### Vấn đề
`HrmIdentityAgentPool` chạy ~4-5 truy vấn MỖI nhân viên (on_shift, open_load,
last_assigned_at, KPI actual) → N+1 khi phòng đông.

### Quyết định
Ba tín hiệu phổ biến gộp thành MỘT truy vấn theo phòng mỗi loại:
- `on_shift`: `list_for_scope(user_ids, date=hôm nay)` rồi lọc ACTIVE + bao giờ
  hiện tại trong bộ nhớ.
- `open_load`: `GROUP BY assigned_user_id` đếm DANG_MO.
- `last_assigned_at`: `GROUP BY user_id` `max(assigned_at)` từ `assignment_log`.

KPI thực đạt GIỮ per-user vì chỉ hỏi cho người CÓ target (thường ít) — bị chặn bởi số
target, không phải số nhân viên. Kết quả định tuyến KHÔNG đổi (test cũ xanh nguyên),
chỉ giảm số truy vấn.

## Giữ nguyên (quyết định đã chốt — KHÔNG đụng đợt này)
- **E** hook chạy đồng bộ trong request (webhook LLM + rollup): ADR 2026-08-04 đã
  chốt giữ, có tiêu chí xét lại.
- **F** URL media Zalo/Meta cần access_token để tải: cần credential thật + quyết định
  lưu trữ media — ngoài phạm vi.
- **G** phạm vi keyword scan-limit tin chỉ-ảnh; realtime notifier #4 dùng log;
  quyền định tuyến chéo phòng: trade-off có chủ đích (spec/review đã ghi), không phải
  bug.

## Nợ còn lại sau đợt này
- `opened ≈ created_at` (#5) — xấp xỉ rất sát, chấp nhận.
- Media token (F), hook nền (E), phạm vi (G) — như trên.
