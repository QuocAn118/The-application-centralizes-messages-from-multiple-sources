# Redesign Phần 2a — Hộp thư mới + BE-3, BE-2, BE-1, BE-9

Nguồn: [GĐ1 §2 + §5 + §10](2026-09-26-ui-redesign-gd1-ra-soat-ux.md) (đã duyệt),
[Phần 1](2026-09-26-ui-redesign-p1-design-system.md) (design system, đã merge).
Nhánh: `feat/ui-hop-thu-2a`. Không dùng taste-skill (quyết định sau Phần 1).

## 1. Phạm vi

**Làm:** giao diện Hộp thư mới (danh sách, khung chat, panel khách tối giản) +
bốn thay đổi backend BE-3, BE-2, BE-1, BE-9.
**Panel khách ở 2a CHỈ có:** kênh, id trên nền tảng, người phụ trách.
**Không làm (để 2b):** lịch sử (BE-4), ghi chú (BE-5), nhãn (BE-6), mẫu trả lời
(BE-7). Không hiện ô trống hay nút "+ Thêm" cho những phần đó.

## 2. Điều đã đổi so với spec GĐ1 (phát hiện khi đọc code)

1. **Dòng hệ thống KHÔNG lấy từ `assignment_log`** (GĐ1 §10.2 viết sai). Bảng đó
   chỉ được #3 ghi khi tự giao; "Nhận việc" không ghi; không có loại sự kiện hay
   người trước; và là nguồn "Được gán" của #5. **User chọn (2026-09-27): bảng
   timeline mới `conversation_events` thuộc module Hộp thư.** `assignment_log`
   vẫn được ghi cho giao TAY (như đã duyệt), KHÔNG ghi khi tự nhận hay gỡ → "Được
   gán" ở Báo cáo giữ đúng nghĩa cũ. Hội thoại cũ không có dòng hệ thống (timeline
   bắt đầu từ lúc triển khai).
2. **Tên người phải do backend trả.** Staff bị 403 ở `/users`, nên FE không tự
   tra được tên người phụ trách / người trong dòng hệ thống. Thêm trường tên vào
   phản hồi (§3.5). Không đổi schema.
3. **Id khách trên nền tảng chưa có trong API** — thêm `customer_external_id`
   vào chi tiết hội thoại (§3.5).
4. **Socket FE bỏ qua loại tín hiệu lạ** (`use-inbox-socket.ts` chỉ nhận
   `new_message`/`status_changed`) — phải mở rộng cho tín hiệu mới.

## 3. Backend

Mọi thay đổi: thêm mới, có test; migration có `downgrade()` và được thử
up → down → up. Import-linter (16 hợp đồng) phải giữ nguyên.

### 3.1 BE-3 — Lọc "Của tôi" / "Chưa ai nhận"

`GET /inbox` thêm `assignee: "me" | "none" | (không truyền)`.
- `me`: `assigned_user_id = actor.user_id`.
- `none`: `assigned_user_id IS NULL`.
- Phạm vi theo vai **giữ nguyên** (lọc chồng lên phạm vi, không mở rộng).
- Giá trị lạ → 422 (enum FastAPI).

### 3.2 BE-9 — Khách đã chờ bao lâu

`InboxItem` (danh sách + chi tiết) thêm `waiting_since: datetime | null`:
= thời điểm **tin VÀO đầu tiên sau tin RA cuối cùng**.
- Tin cuối là tin ra → `null`. Chưa có tin vào → `null`. Hội thoại `DA_DONG` → `null`.
- Khách nhắn 3 tin liên tiếp → tính từ tin thứ nhất.

### 3.3 BE-1 — Chưa đọc theo từng người

**Bảng mới** `conversation_reads(user_id UUID, conversation_id UUID,
last_read_at timestamptz, PK(user_id, conversation_id))`. Không khoá ngoại sang
identity (như mọi bảng tham chiếu chéo module).

**Chưa đọc** = số tin VÀO có `created_at > last_read_at` (không có dòng = chưa đọc
tin nào). **Hội thoại `DA_DONG` luôn tính 0** — đã xử lý xong, không làm nhiễu.

API:
- `InboxItem.unread_count: int` (của người đang gọi).
- `POST /inbox/{id}/read` → 204. Quyền = quyền xem hội thoại (như `GET /inbox/{id}`).
  Đặt `last_read_at = now()`; không bao giờ lùi (upsert lấy `GREATEST`).
- `GET /inbox/unread-count` → `{ "conversations": n }` = số hội thoại TRONG PHẠM VI
  người gọi (như `GET /inbox` không lọc) có `unread_count > 0` — cho huy hiệu nav.

Đánh dấu đã đọc khi (GĐ1 §10.3):
1. mở hội thoại → FE gọi `POST read`;
2. có tin mới lúc hội thoại đang mở **và** `document.hasFocus()` → FE gọi `POST read`;
3. người đó gửi trả lời → **backend** tự ghi trong use case trả lời (không phụ
   thuộc FE).

Index: partial index `messages(conversation_id, created_at) WHERE
direction = 'INBOUND'` (phục vụ đếm chưa đọc và BE-9); thêm bản `OUTBOUND` nếu đo
cho thấy cần.

**Hiệu năng (điều kiện dừng):** đo `GET /inbox` trước/sau trên **database đo riêng**
`omnichat_perf` (KHÔNG gieo hàng nghìn hội thoại giả vào DB dev của user) với
≥ 3.000 hội thoại, ~20 tin/hội thoại, 3 vai. **Chậm thêm > 100 ms → dừng, báo
user** (phương án dự phòng: lưu sẵn bộ đếm).

### 3.4 BE-2 — Đổi / gỡ người phụ trách + timeline

**Domain:** thêm `Conversation.chuyen_nguoi_phu_trach(user_id | None, now)` trả
người cũ. Chỉ khi `DANG_MO`; đổi sang chính người đang phụ trách → lỗi
`ALREADY_ASSIGNED_TO_USER`; gỡ khi chưa có ai → `NOT_ASSIGNED`.
`assign_to_agent` (Nhận việc, #3 tự giao) **giữ nguyên** quy tắc "không cướp việc".

**API:** `POST /inbox/{id}/assign-user {"user_id": UUID | null}` → `Conversation`.
- Chỉ Manager (hội thoại thuộc phòng mình) hoặc Admin.
- Người được gán: đang hoạt động, **cùng phòng** với hội thoại (dùng lại kiểm tra
  của `AssignConversationToAgent`).

**Bảng mới** `conversation_events(id, conversation_id, kind, actor_user_id null,
from_user_id null, to_user_id null, created_at)`, index `(conversation_id,
created_at)`. `kind`:

| kind | Ghi khi | Dòng hiện trong chat |
|---|---|---|
| `TAKEN` | nhân viên bấm Nhận việc | "B đã nhận việc" |
| `AUTO_ASSIGNED` | #3 tự giao | "Hệ thống tự giao cho B" |
| `ASSIGNED` | Manager/Admin giao khi chưa có ai | "A giao cho B" |
| `REASSIGNED` | đổi người | "Chuyển từ A sang B" |
| `UNASSIGNED` | gỡ | "Gỡ người phụ trách A" |

`GET /inbox/{id}` thêm `events: [{id, kind, created_at, actor_name, from_name,
to_name}]` (tên do backend tra).

**`assignment_log`:** module Hộp thư phát **hook sau-giao-việc** (cùng mẫu với hook
sau-nhận-tin / sau-đóng đang có); module Assignment đăng ký hook đó trong `main.py`
và ghi `assignment_log` cho `ASSIGNED` và `REASSIGNED` (người MỚI). Không ghi cho
`TAKEN`, `UNASSIGNED`. `AUTO_ASSIGNED` vẫn do #3 ghi như cũ.

**Realtime:** mỗi kết nối WebSocket lưu thêm `user_id`. Sau khi đổi/gỡ:
- phát `status_changed` cho phòng như cũ;
- phát riêng `{"change": "assigned_to_you", conversation_id}` cho người MỚI và
  `{"change": "unassigned_from_you", conversation_id}` cho người CŨ.

### 3.5 Trường thêm vào phản hồi (không đổi schema)

- `InboxItem.assigned_user_name: str | null` (danh sách + chi tiết).
- `Conversation.customer_external_id: str` (chi tiết).
- Tên trong `events`.
Tra tên qua `IWorkforceDirectory` (thêm `full_name` + hàm tra theo lô) — module
Hộp thư vẫn không import identity.

## 4. Frontend

Bố cục 3 cột, dùng hết bề ngang (X4 cho phép Hộp thư full width):
`NavRail 84 | Danh sách 360 | Khung chat (co giãn) | Panel khách 320 (thu gọn được)`.
Ở 1280px panel mặc định thu gọn (nhớ lựa chọn trong `localStorage`, bọc try/catch).

### 4.1 Danh sách (I1–I6, I13)

- Tab chính: **Của tôi · Chưa ai nhận · Tất cả** (BE-3). Mặc định: Staff = Của
  tôi; Manager/Admin = Tất cả. Lọc trạng thái thành ô chọn phụ. Giữ trên URL như cũ.
- Mỗi mục 2 dòng: **tên · mốc giờ** / **xem trước**. Avatar màu theo id + logo
  kênh ở góc. Chưa đọc: tên + xem trước đậm, số đếm vàng bên phải (99+).
- Huy hiệu chỉ khi cần chú ý: "Chờ phân" (CHO_PHAN), "Chưa ai nhận" (DANG_MO không
  người). Không lặp "Đang mở".
- "Chờ 12 phút" khi `waiting_since` có giá trị; ≥ `NGUONG_CHO_PHUT = 15` thì tông
  cảnh báo. Cập nhật mỗi phút (không gọi lại API).
- Mốc giờ tương đối qua `Intl.RelativeTimeFormat` ("2 phút", "14:32", "Hôm qua",
  "Th 2", "15/09").
- **Cuộn liên tục** (`useInfiniteQuery` + IntersectionObserver, `offset` sẵn có).

### 4.2 Khung chat (I7, I8, I10)

- Header: avatar, tên, logo kênh, phòng, **người phụ trách** (Manager/Admin: ô
  chọn đổi/gỡ; người khác: chỉ chữ), "Chờ N phút". Nút chính theo ngữ cảnh:
  `CHO_PHAN` → "Phân phòng"; chưa ai nhận và được phép → "Nhận việc". "Đóng hội
  thoại" vào menu "⋯", **có xác nhận**.
- Tin: vạch mốc ngày ("Hôm nay", "Hôm qua", "Thứ Hai, 15/09"); gom tin liên tiếp
  cùng người gửi trong 5 phút, giờ ở tin cuối nhóm. Dòng hệ thống (`events`) chen
  đúng thời điểm.
- Ô soạn: viền 2px, nút Gửi vàng, dòng gợi ý "Enter để gửi · Shift+Enter xuống
  dòng", nút đính kèm icon lucide. Giữ nguyên luồng gửi/giữ chữ khi lỗi (IT-5).

### 4.3 Panel khách (tối giản)

Kênh (logo + tên), id trên nền tảng (có nút chép), người phụ trách, phòng. Không
gì khác ở 2a.

### 4.4 Realtime & nav

- `use-inbox-socket` nhận thêm `assigned_to_you` / `unassigned_from_you`: làm mới
  danh sách + hiện thông báo ngắn (vùng `aria-live`, tự tắt).
- Huy hiệu số chưa đọc trên mục "Hộp thư" của nav rail (`GET /inbox/unread-count`,
  làm mới khi có tín hiệu).

## 5. Kiểm chứng

- Backend: test domain (chuyển/gỡ), use case (quyền, cùng phòng, trạng thái),
  repository thật (đếm chưa đọc, `waiting_since`, lọc `assignee`, hook ghi
  `assignment_log`), migration up/down/up. Phủ đủ: người phòng A không đổi được
  hội thoại phòng B; gỡ khi chưa có ai; giao cho người phòng khác.
- Hiệu năng: bảng số trước/sau (§3.3).
- Frontend: test logic (mốc tương đối, nhóm tin, chèn dòng hệ thống, ngưỡng chờ).
- 12 kịch bản cũ vẫn qua (sau `seed_kiem_chung`); kịch bản mới `ui-p2a` cho Hộp thư.
- Playwright MCP 1440px: chụp trước/sau, tự xem ảnh; kiểm focus bàn phím, tương phản.

## 6. Thư viện

Không thêm gì. Ô chọn người phụ trách dùng `OChon` (select native) — không cần
Radix Popover như dự kiến ở Phần 1 (ponytail: native đủ).
