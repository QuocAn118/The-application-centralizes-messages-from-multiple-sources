# OmniChat Frontend #F1 — Inbox & Reply: Kế hoạch

> Bám [spec FE Inbox & Reply](../specs/2026-08-05-omnichat-frontend-inbox-design.md). Backend API đã có thật (§6 spec). Chưa gọi Stitch — mockup UI là bước tuỳ chọn SAU khi plan chốt.

## Nguyên tắc thực hiện

- **Một tầng API client** là xương sống (RB-1): mọi call qua đó, tự gắn Bearer + refresh 401. Viết trước, mọi màn dựng trên nó.
- **Type khớp backend** (§6): khai báo type response một nơi; nếu lệch schema là lỗi tích hợp, sửa ngay.
- **Realtime = tín hiệu → refetch** (RB-2): không bao giờ render payload WS.
- **Server là trọng tài quyền** (RB-3): FE ẩn/hiện nút cho UX, nhưng luôn xử lý 403/404/409/422 tử tế.
- Mỗi giai đoạn có tiêu chí "xong" quan sát được; review trước khi sang giai đoạn sau (theo nhịp backend).

## Quyết định cần chốt khi bắt đầu GĐ1 (ghi để không đoán)

| Vấn đề | Hướng ưu tiên | Chốt ở |
|---|---|---|
| Thư viện data-fetching/cache | React Query (TanStack) — có invalidate theo tín hiệu WS gọn | GĐ1 |
| Lưu refresh token | Cookie httpOnly qua Route Handler của Next (giảm XSS) vs localStorage | GĐ1 |
| Styling | (chốt với user: Tailwind / CSS Modules / thư viện component) | GĐ1 |
| Vị trí thư mục FE | `frontend/` cạnh `backend/` (monorepo nhẹ) | GĐ1 |

## Giai đoạn

| GĐ | Nội dung | "Xong" khi |
|---|---|---|
| **1 — Khung & Auth** | Khởi tạo Next.js (App Router, TS); tầng API client (Bearer + refresh single-flight 401→refresh→retry, RB-4); AuthContext (`/login`, `/me`, `/logout`, guard `/inbox*`); layout có nav (chừa chỗ #4/#5). | Đăng nhập được, `/me` hiển thị, route được bảo vệ, refresh token hoạt động; test IT-4. |
| **2 — Inbox list** | Màn `/inbox` cột trái: `GET /inbox` + lọc trạng thái + phân trang; dòng hội thoại (khách, badge kênh, trạng thái, mốc). Trạng thái rỗng/đang tải/lỗi. | Danh sách hiển thị đúng, lọc + phân trang chạy, 403/lỗi xử lý; type khớp `PageResponse<InboxItem>`. |
| **3 — Khung chat & Reply** | `/inbox/[id]`: `GET /inbox/{id}` render tin (INBOUND/OUTBOUND, mốc, ảnh→placeholder nếu chưa có route phục vụ, xem Nợ); ô soạn + `POST reply`; ô soạn disabled đúng trạng thái (RB-5); reply lỗi không mất nội dung (IT-5). | Đọc + trả lời một hội thoại DANG_MO chạy trọn; disabled đúng; test IT-2, IT-5. |
| **4 — Hành động & vai** | Nút Take/Assign/Close gọi endpoint tương ứng, cập nhật từ `ConversationResponse` trả về; ẩn/hiện nút theo vai + trạng thái (§3); xử lý 409/422 (toast + refetch). | Ba hành động chạy, nút đúng theo vai, lỗi hợp lệ hiển thị rõ; test IT-3. |
| **5 — Realtime** | `useInboxSocket`: kết nối `/ws/inbox?token=`, backoff reconnect, reconnect khi refresh token; `new_message`/`status_changed` → invalidate list + (nếu đang mở) detail (RB-2). | Hai tab: gửi tin ở tab A → tab B thấy cập nhật không cần F5; test IT-1. |

## Ghi chú thực hiện

- **Điểm rủi ro nhất (như backend): refresh + WS token xoay.** Refresh single-flight (nhiều 401 gom một refresh); khi token mới, đóng WS cũ mở WS mới — nếu không, WS dùng token hết hạn sẽ bị server đóng (1008). Viết kỹ ở GĐ1 + GĐ5, có test.
- **Ảnh attachment:** backend expose `stored_path` nhưng **CHƯA có route phục vụ ảnh** (đã kiểm). Bản đầu: hiển thị placeholder "ảnh" (và text nếu có). Ghi nợ — KHÔNG tự thêm route backend trong sub-project FE (RB-1). Nếu user muốn ảnh thật, mở nợ backend riêng.
- **Đính kèm khi trả lời:** `ReplyRequest` chỉ nhận `text`. Bản đầu chỉ gửi text. Ảnh outbound = nợ backend (mở rộng schema) — không làm ở FE bản đầu.
- **RBAC UX:** ẩn/hiện nút chỉ để gọn; luôn code như thể server có thể từ chối (403/409/422) và xử lý — không tin tưởng điều kiện FE là đủ.
- **Không CSV/không i18n/không #4-#5-#2** (nợ spec §9).

## Sau khi plan chốt

1. (Tuỳ chọn) **Mockup UI bằng Stitch** từ spec — gọi khi user đồng ý. Cho Stitch: layout hai cột inbox, khung chat, form đăng nhập; bảng màu + component do user chọn.
2. Code theo giai đoạn 1→5, review từng giai đoạn.

Chi tiết từng task (files/interfaces/steps) viết khi bắt đầu mỗi giai đoạn, như cách backend #0–#5.
