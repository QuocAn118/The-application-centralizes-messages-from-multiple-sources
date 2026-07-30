# OmniChat #3 Auto-Assignment — Thiết kế

**Trạng thái:** nháp để duyệt · **Ngày:** 2026-07-29 · **Phụ thuộc:** #1 Inbox, #2 Keyword, #4 HRM (đều đã merge `main`)

## 1. Mục tiêu

Sau khi một hội thoại đã thuộc về một **phòng** (do #2 tự phân theo keyword, hoặc Manager phân tay ở #1), tự động chọn **một nhân viên cụ thể** trong phòng đó để giao việc — thay cho việc nhân viên phải tự bấm "nhận" ở #1. Nếu không chọn được ai, hội thoại nằm trong **hàng đợi của phòng** chờ tới lượt.

Ranh giới rõ với #2: **#2 chọn phòng, #3 chọn người.** #3 KHÔNG đụng tới việc phân phòng.

## 2. Phạm vi (đã chốt với user)

**Trong phạm vi:**
- Tự gán nhân viên cho hội thoại `DANG_MO` chưa có `assigned_user_id` (hàng đợi phòng).
- Bộ chọn nhân viên theo **chuỗi tiêu chí ưu tiên** (tiebreaker, không phải công thức trọng số).
- Kích hoạt tự gán ở hai thời điểm: (a) ngay sau khi #2/Manager phân hội thoại về phòng; (b) khi một nhân viên rảnh ra / vào ca (kéo việc từ hàng đợi).
- Hàng đợi phòng: hội thoại chờ khi không có ai nhận được.
- Đánh dấu hoàn thành: nhân viên đóng hội thoại (đã có ở #1 `close`) → #3 có thể kéo việc kế tiếp cho họ.

**Ngoài phạm vi (nợ/để module khác):**
- Không phân lại phòng (đó là #2).
- Không cân bằng tải xuyên phòng.
- Không SLA/ưu tiên theo loại khách (nợ tương lai).
- Báo cáo hiệu suất phân việc: thuộc #5.

## 3. Tiêu chí chọn nhân viên — chuỗi tiebreaker THEO THỨ TỰ

Cho một hội thoại thuộc phòng `D`, chọn nhân viên trong `D` theo thứ tự, dừng ở tiêu chí đầu tiên phá được hoà:

1. **Đang trong ca (LỌC BẮT BUỘC).** Chỉ xét nhân viên `STAFF`/`MANAGER` active của phòng `D` có một buổi phân ca (`ShiftAssignment` trạng thái `ACTIVE`) bao thời điểm hiện tại (ngày hôm nay + `start_time ≤ now.time ≤ end_time`). Không ai trong ca → **không chọn được** (xem §4).
2. **Tải hàng đợi thấp nhất.** Trong số ứng viên còn lại, chọn người đang giữ **ít hội thoại `DANG_MO` (đã gán mình) nhất**. Cân bằng tải, tránh dồn.
3. **Chưa đủ KPI ưu tiên.** Nếu vẫn hoà, ưu tiên người có **`achievement_percent` thấp hơn** (dưới 100% = chưa đạt target kỳ hiện tại) — chia việc để họ đạt KPI. Thiếu dữ liệu KPI (`None`) xếp như "chưa đạt" (được ưu tiên nhận thêm, đúng tinh thần khuyến khích).
4. **Xoay vòng (round-robin).** Hoà nốt → chọn người **được gán gần đây nhất cách xa nhất** (lâu chưa nhận việc nhất), phá hoà ổn định và công bằng. Mốc "lần gán gần nhất" suy từ `assigned_user_id` + thời điểm trên hội thoại (không cần bảng phụ ở bản đầu).

Kết quả: đúng một `user_id` hoặc "không có".

## 4. Hàng đợi phòng khi không chọn được ai

- Không có nhân viên nào trong ca (hoặc phòng rỗng) → hội thoại **giữ `DANG_MO`, `assigned_user_id = None`**. Đây chính là "hàng đợi phòng": các hội thoại `DANG_MO` chưa gán người của một phòng.
- **Kéo hàng đợi:** khi một nhân viên vào ca hoặc vừa đóng một hội thoại (rảnh ra), #3 thử gán cho họ hội thoại **chờ lâu nhất** trong hàng đợi phòng (theo `last_message_at`/`created_at`). Đây là chiều "người tìm việc" bổ sung cho chiều "việc tìm người" ở §3.
- Manager/nhân viên vẫn **tự nhận tay** được (dùng `TakeConversation` của #1) — #3 không khoá luồng thủ công.

## 5. Điểm kích hoạt (trigger)

| Trigger | Nguồn | Hành động |
|---|---|---|
| Hội thoại vừa được phân về phòng | #2 tự phân (hook) HOẶC Manager phân tay (#1 `AssignConversationToDepartment`) | Thử gán nhân viên ngay (§3) |
| Nhân viên đóng một hội thoại | #1 `CloseConversation` | Kéo một việc từ hàng đợi phòng cho họ (§4) |
| (Nợ) Nhân viên vào ca | #4 `AssignShift` bắt đầu | Kéo hàng đợi — cân nhắc ở giai đoạn sau |

Giữ đúng ranh giới module: các trigger nối qua **hook/port ở composition root**, KHÔNG để #1/#2/#4 import #3 (giống cách #2 móc vào webhook của #1 qua `app.state.post_ingest_hooks`). #3 là hạ nguồn.

## 6. Kiến trúc & độc lập module

Module mới `assignment` (hoặc `autoassign`), clean architecture 4 tầng như #2. Độc lập **hai chiều** với inbox/hrm/identity/keyword: `assignment.{domain,application,presentation}` không import module khác; chỉ `assignment.infrastructure` chạm chúng qua adapter port. Chiều ngược: #1/#2/#4 KHÔNG biết #3 tồn tại (import-linter thêm contract).

**Cổng (port) chính:**
- `IAgentPool` (đọc #4 + #1 + identity) — trả danh sách ứng viên của một phòng kèm: đang trong ca?, số hội thoại đang giữ, `achievement_percent`, mốc gán gần nhất. Đây là chỗ gom dữ liệu tiebreaker.
- `IConversationAssigner` (ghi #1) — gán một hội thoại cho một nhân viên qua use case `TakeConversation`/một use case gán-thay của #1, với actor hệ thống. Chỗ DUY NHẤT #3 tác động ngược inbox.
- `IWaitingQueue` (đọc #1) — liệt kê hội thoại `DANG_MO` chưa gán của một phòng (hàng đợi), sắp theo chờ lâu nhất.

**Lưu trữ riêng của #3:** bản đầu có thể **không cần bảng mới** — trạng thái hàng đợi suy từ inbox (`DANG_MO` + `assigned_user_id IS NULL`), round-robin suy từ mốc gán trên hội thoại. Nếu round-robin cần chính xác hơn, thêm bảng `assignment_log` (nợ, cân nhắc ở plan).

## 7. Bất biến & quy tắc nghiệp vụ

- **RB-1:** Chỉ gán khi hội thoại `DANG_MO` và `assigned_user_id IS NULL`. Đã có người → bỏ qua (idempotent, không cướp việc).
- **RB-2:** Chỉ gán nhân viên **active, thuộc đúng phòng của hội thoại, đang trong ca**. Máy trạng thái #1 (`assign_to_agent` chặn nếu không `DANG_MO`) là chốt cuối.
- **RB-3:** Gán qua use case chính thống của #1 với **actor hệ thống** — máy trạng thái/realtime/phân quyền #1 giữ nguyên. #3 chỉ "một Admin tự động chọn người".
- **RB-4:** Auto-assign thất bại (không ai trong ca, race đã có người nhận) KHÔNG được làm hỏng luồng gọi (webhook/đóng hội thoại) — nuốt lỗi, để hàng đợi.
- **RB-5:** Không cướp việc đang xử lý; không phân lại hội thoại đã đóng trừ khi khách nhắn lại (mở lại → lại vào hàng đợi phòng, #3 xử như hội thoại mới chưa gán).

## 8. Nợ chốt sẵn (ghi để #5/tương lai)

- **F1 từ review #2 GĐ4:** mô hình quyền định tuyến — endpoint kích hoạt lại của #2 cho Manager định tuyến chéo phòng. #3 nên thống nhất: **auto-assign chỉ trong phòng của hội thoại**; hành động thủ công của Manager vẫn theo quyền #1. Ghi rõ khi làm.
- Round-robin bản đầu suy từ mốc gán trên hội thoại (không tuyệt đối chính xác nếu nhiều phân song song) — nợ `assignment_log` nếu cần.
- Kéo hàng đợi khi "vào ca" là nợ (bản đầu chỉ kéo khi "đóng hội thoại").
- Phân tích đồng bộ: nếu gán chạy trong request đóng hội thoại/webhook, kế thừa nợ hàng đợi nền của #2 (spec §9 của #2).

## 9. Câu hỏi mở cho plan
- Tên module: `assignment` hay `autoassign`? (đề xuất `assignment`).
- Có endpoint HTTP cho Manager "chạy auto-assign lại một phòng" không, hay chỉ chạy ngầm qua trigger? (đề xuất có, giống re-trigger của #2, chỉ Admin/Manager phòng mình).
- Có cần bảng `assignment_log` ngay không (round-robin/analytics #5)? (đề xuất hoãn, dùng dữ liệu suy ra trước).
