# OmniChat Frontend #F1 — Inbox & Reply: Thiết kế

> Frontend đầu tiên, dựng trên backend đã hoàn tất (roadmap 0→1→4→2→3→5 + đóng nợ). Phạm vi bản đầu chốt với user 2026-08-05: **Inbox & Reply**. API tham chiếu là API THẬT đang chạy (prefix `/api/v1`), không phải giả định.

## 1. Mục tiêu

Nhân viên/Manager/Admin đăng nhập, thấy **một inbox đa kênh thống nhất**, mở một hội thoại, đọc lịch sử tin, **trả lời** (text), **nhận việc / phân phòng / đóng** — cập nhật **thời gian thực** khi có tin mới hay đổi trạng thái. Đây là giá trị nhìn thấy được đầu tiên của FE, tương ứng đúng module #1 (Inbox) của backend.

**Không thuộc bản đầu:** dashboard báo cáo (#5), quản trị HRM (#4), cấu hình kênh & keyword (#1 admin / #2). Các màn đó là sub-project FE sau — spec riêng. Bản đầu **chừa sẵn chỗ** cho chúng (layout có nav, auth/role đã đủ để mở rộng).

## 2. Ràng buộc kiến trúc quyết định (đọc trước khi thiết kế chi tiết)

**RB-1 — API là hợp đồng cố định, FE không đổi backend.** Toàn bộ màn hình chỉ gọi các endpoint `/api/v1` đã có. Nếu một nhu cầu FE thiếu endpoint, ghi nợ (không tự ý sửa backend trong sub-project FE này). Danh sách endpoint dùng ở §6.

**RB-2 — Realtime là TÍN HIỆU, không phải dữ liệu.** WebSocket `/ws/inbox?token=<access>` chỉ đẩy `{conversation_id, change, department_id}` với `change ∈ {new_message, status_changed}`. FE nhận tín hiệu rồi **gọi lại REST** để lấy nội dung mới. Không bao giờ hiển thị thẳng payload WS như nội dung tin. Lý do: backend cố ý không gửi nội dung qua WS (bảo mật + phạm vi quyền lọc ở server).

**RB-3 — Phạm vi quyền theo vai, khớp server.** Server đã lọc theo vai (Staff/Manager/Admin) ở cả REST lẫn WS. FE **không tự phân quyền dữ liệu** (không nơi nào FE quyết định "được thấy gì") — chỉ ẩn/hiện *nút hành động* theo vai để UX gọn. Nguồn sự thật quyền là 403/404 từ server; FE xử lý lỗi đó tử tế.

**RB-4 — Token sống ngắn, refresh minh bạch.** `login`/`refresh` trả `access_token` + `refresh_token` + `expires_in` (giây). Access token hết hạn → tự refresh một lần rồi thử lại; refresh hỏng → về màn đăng nhập. WS dùng access token ở query param; token xoay thì phải reconnect WS với token mới.

**RB-5 — Reply chỉ khi hội thoại mở.** Backend chỉ cho reply khi `DANG_MO` (đóng/chờ-phân sẽ 4xx). FE phản ánh: ô soạn tin **disabled** khi không `DANG_MO`, kèm gợi ý ("nhận việc để trả lời" / "hội thoại đã đóng").

**RB-6 — Không state backend giả lập ở FE.** FE không giữ bản sao "sự thật" của hội thoại quá thời điểm; sau mỗi hành động (reply/take/close/assign) dùng response trả về (đã là view mới nhất) để cập nhật, và tin cậy tín hiệu WS cho thay đổi từ người khác.

## 3. Ngôn ngữ miền (khớp backend)

| Khái niệm | FE hiển thị |
|---|---|
| **Conversation** | Một dòng inbox + một khung chat. Có `status`, `platform`, `department_id`, `assigned_user_id`, `customer_display_name`, `last_message_at`. |
| **Status** | `CHO_PHAN` (chờ phân phòng — chỉ Manager/Admin thấy), `DANG_MO` (đang mở — trả lời được), `DA_DONG` (đã đóng). |
| **Message** | `direction` (INBOUND/OUTBOUND), `text`, `created_at`, `sender_user_id`, `attachments[]`. |
| **Platform** | `ZALO`/`FACEBOOK`/`INSTAGRAM` — badge kênh trên mỗi hội thoại. |
| **Actor** | Người đăng nhập: `role` (STAFF/MANAGER/ADMIN) + `department_id`. Quyết định nút nào hiện. |

### Trạng thái & hành động theo vai

| Hành động | Endpoint | Điều kiện | Ai thấy nút |
|---|---|---|---|
| Trả lời | `POST /inbox/{id}/reply` | status = DANG_MO | Người đang xử lý / Manager/Admin phòng đó |
| Nhận việc | `POST /inbox/{id}/take` | DANG_MO, chưa có người | Staff/Manager phòng đó |
| Phân phòng | `POST /inbox/{id}/assign` | status = CHO_PHAN | Manager/Admin |
| Đóng | `POST /inbox/{id}/close` | status = DANG_MO | Người xử lý / Manager/Admin |

FE chỉ *ẩn/hiện* nút theo điều kiện trên; server vẫn là trọng tài cuối (403/409/422).

## 4. Màn hình & luồng

### 4.1 Đăng nhập (`/login`)
Form email + mật khẩu → `POST /api/v1/login`. Lưu token (bộ nhớ + refresh token ở nơi bền hơn — xem §7 bảo mật). Sai → thông báo lỗi. Thành công → `/inbox`.

### 4.2 Inbox hai cột (`/inbox`, `/inbox/[id]`)
- **Cột trái — danh sách:** `GET /api/v1/inbox?status=&limit=&offset=`. Mỗi dòng: tên khách, badge kênh, trạng thái, mốc tin cuối. Bộ lọc trạng thái (tất cả / CHO_PHAN / DANG_MO / DA_DONG). Phân trang (limit ≤ 100). Sắp theo `last_message_at` giảm dần (server đã sắp). Dòng đang chọn nổi bật.
- **Cột phải — khung chat:** `GET /api/v1/inbox/{id}?limit=&offset=`. Header: khách + kênh + trạng thái + người xử lý. Thân: bong bóng tin (INBOUND trái, OUTBOUND phải), ảnh đính kèm, mốc thời gian. Footer: ô soạn + nút Gửi (RB-5) + nút hành động theo vai (§3).
- **Rỗng:** chưa chọn hội thoại → hướng dẫn; inbox rỗng → trạng thái trống.

### 4.3 Luồng thời gian thực
Mở `/inbox` → kết nối WS `/ws/inbox?token=`. Nhận `{conversation_id, change}`:
- `new_message`: nếu là hội thoại đang mở → refetch chi tiết (thêm tin mới); luôn refetch/patch dòng danh sách (đưa lên đầu, cập nhật mốc).
- `status_changed`: refetch dòng danh sách + (nếu đang mở) chi tiết để đồng bộ trạng thái/người xử lý.
Reconnect có backoff khi rớt; refresh token → đóng WS cũ, mở WS mới với token mới.

### 4.4 Luồng hành động (optimistic có kiểm soát)
Reply: khoá ô nhập → `POST reply` → thêm tin từ response → mở khoá. Lỗi → giữ nội dung đã gõ, báo lỗi, không mất tin. Take/Close/Assign: gọi endpoint → dùng `ConversationResponse` trả về cập nhật cả chi tiết lẫn dòng danh sách.

## 5. Kiến trúc FE

- **Next.js (App Router) + TypeScript.** Server Components cho khung tĩnh; Client Components cho phần tương tác (chat, WS, form).
- **Tầng API client** duy nhất: gói fetch có base URL `/api/v1`, tự gắn `Authorization: Bearer`, tự refresh 401 một lần, ném lỗi có mã để UI xử lý. **Mọi màn gọi qua tầng này** — không fetch rải rác (đối xứng RB-1 "API là hợp đồng").
- **Kiểu dữ liệu** sinh/khai báo khớp schema backend (§6) — một nguồn type cho response, tránh lệch.
- **State máy chủ** (danh sách, chi tiết) qua một lớp data-fetching có cache + invalidate theo tín hiệu WS (ví dụ React Query hoặc tương đương — chốt ở plan). **State cục bộ** (nội dung đang gõ, hội thoại đang chọn) ở component.
- **Realtime** một hook `useInboxSocket` quản vòng đời WS + phát sự kiện invalidate.
- **Auth** một context giữ actor (`/me`) + token; guard route `/inbox*`.

## 6. Hợp đồng API dùng ở bản đầu (khớp backend thật)

| Việc | Method + path | Body/Query | Response |
|---|---|---|---|
| Đăng nhập | `POST /api/v1/auth/login` | `{email, password}` | `{access_token, refresh_token, token_type, expires_in, must_change_password}` |
| Làm mới token | `POST /api/v1/auth/refresh` | `{refresh_token}` | như trên |
| Đăng xuất | `POST /api/v1/auth/logout` | `{refresh_token}` | 204 (cần Bearer) |
| Đổi mật khẩu | `POST /api/v1/auth/change-password` | `{current_password, new_password}` | 204 |
| Tôi là ai | `GET /api/v1/auth/me` | — | `UserResponse` (xem kiểu chính) |
| Danh sách inbox | `GET /api/v1/inbox` | `status?, limit≤100, offset` | `PageResponse<InboxItem>` |
| Chi tiết hội thoại | `GET /api/v1/inbox/{id}` | `limit≤200, offset` | `Conversation` (kèm `messages[]`) |
| Trả lời | `POST /api/v1/inbox/{id}/reply` | `{text}` (≤8000, không rỗng) | `Message` |
| Phân phòng | `POST /api/v1/inbox/{id}/assign` | `{department_id}` | `Conversation` |
| Nhận việc | `POST /api/v1/inbox/{id}/take` | — | `Conversation` |
| Đóng | `POST /api/v1/inbox/{id}/close` | — | `Conversation` |
| Realtime | `WS /ws/inbox?token=<access>` | — | tín hiệu `{conversation_id, change, department_id}` |

> **Đã đối chiếu mã nguồn backend 2026-08-05 (trước khi code GĐ1).** Hai điểm spec bản đầu ghi sai/thiếu, nay đã sửa ở bảng trên:
> 1. **Nhóm auth nằm dưới `/api/v1/auth/...`**, không phải `/api/v1/...` — `auth_router` khai báo `prefix="/auth"` rồi mới được `main.py` gắn `prefix="/api/v1"`. Các endpoint inbox thì đúng như spec (`/api/v1/inbox`), WS cũng đúng (`/ws/inbox`, không có tiền tố `/api/v1`).
> 2. **`login`/`refresh` trả thêm `must_change_password`.** Khi `true`, người dùng phải đổi mật khẩu trước khi làm việc — FE điều hướng sang màn đổi mật khẩu (`/api/v1/auth/change-password`). Bản đầu xử lý tối thiểu: hiện thông báo + cho đổi mật khẩu, không bỏ qua cờ này.

**Kiểu chính (rút từ schema backend):**
- `UserResponse` (`/auth/me`, `/auth/login`): `id, email, full_name, phone?, role, department_id?, is_active, must_change_password, last_login_at?, created_at`.
- `InboxItem`: `conversation_id, channel_id, platform, customer_id, customer_display_name?, status, department_id?, assigned_user_id?, last_message_at`.
- `Conversation`: các trường của InboxItem (trừ tên trường lặp) + `messages: Message[]`.
- `Message`: `id, direction, text?, created_at, sender_user_id?, attachments: Attachment[]`.
- `Attachment`: `id, kind, stored_path, content_type?, size?`.
- `PageResponse<T>`: `{items: T[], total, limit, offset}`.

**Nợ hợp đồng (ghi để plan quyết):** reply hiện chỉ nhận `text` (đính kèm ảnh outbound là iteration sau — schema `ReplyRequest` chưa nhận media); `stored_path` của attachment cần một route phục vụ ảnh (kiểm ở plan xem đã có chưa, nếu chưa thì FE hiển thị placeholder + ghi nợ, không tự thêm backend).

## 7. Bảo mật & lỗi

- **Token:** access token giữ trong bộ nhớ (không localStorage) để giảm XSS; refresh token lưu ở nơi bền vừa đủ (chốt cơ chế ở plan — cookie httpOnly qua route handler là hướng ưu tiên). Không log token. WS token ở query string chỉ trên kết nối TLS.
- **401/refresh:** một lần refresh cho mỗi 401; nhiều request 401 đồng thời gom về một lần refresh (single-flight).
- **403/404:** hiển thị "không có quyền / không tìm thấy" thay vì trắng màn; không rò thông tin.
- **409/422:** hành động không hợp lệ (đóng hội thoại đã đóng, reply khi không DANG_MO) → toast rõ nghĩa, refetch để đồng bộ trạng thái thật.
- **CSP/không bí mật ở client:** không nhúng secret; base URL API qua biến môi trường build-time.

## 8. Bất biến kiểm thử (định hướng test FE)

- **IT-1** WS chỉ trigger refetch, không render thẳng payload (RB-2).
- **IT-2** Ô soạn disabled đúng theo trạng thái (RB-5).
- **IT-3** Nút hành động ẩn/hiện đúng theo vai + trạng thái (§3), nhưng server lỗi vẫn xử lý tử tế (RB-3).
- **IT-4** 401 tự refresh một lần rồi thử lại; refresh hỏng → `/login` (RB-4).
- **IT-5** Reply lỗi không mất nội dung đã gõ (§4.4).

## 9. Nợ ghi sẵn (không làm bản đầu)

(a) đính kèm ảnh khi trả lời (cần mở rộng `ReplyRequest` — backend, ghi nợ) — **CÒN NỢ**;
(b) ~~phục vụ ảnh attachment~~ — **ĐÃ TRẢ 2026-08-09**: `GET /inbox/{cid}/attachments/{aid}` với URL ký HMAC hết hạn 300s (thẻ `<img>` không gửi được Bearer nên dùng chữ ký);
(c) các màn #4/#5/#2 (sub-project FE sau, spec riêng) — **CÒN NỢ**;
(d) i18n/đa ngôn ngữ (bản đầu tiếng Việt) — **CÒN NỢ**;
(e) ~~mockup UI bằng Stitch~~ — **XONG 2026-08-05** (6 màn);
(f) ~~preview tin cuối ở dòng danh sách~~ — **ĐÃ TRẢ**: `InboxItem.last_message_preview`, một truy vấn `DISTINCT ON` cho cả trang;
(g) ~~ô tìm kiếm~~ — **ĐÃ TRẢ**: `GET /inbox?q=` lọc theo tên khách, **bỏ dấu** (`unaccent`) nên gõ không dấu vẫn khớp.

## 10. Bước tiếp (thứ tự)

1. Spec này (xong) → **plan** (map ra công việc theo giai đoạn).
2. (Tuỳ chọn) **Mockup UI bằng Stitch** từ spec đã chốt — chỉ khi user đồng ý.
3. Code Next.js theo plan.
