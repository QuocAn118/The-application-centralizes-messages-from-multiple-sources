# OmniChat Frontend #F1 — Inbox & Reply: Kế hoạch

> Bám [spec FE Inbox & Reply](../specs/2026-08-05-omnichat-frontend-inbox-design.md). Backend API đã có thật (§6 spec). Chưa gọi Stitch — mockup UI là bước tuỳ chọn SAU khi plan chốt.

## Nguyên tắc thực hiện

- **Một tầng API client** là xương sống (RB-1): mọi call qua đó, tự gắn Bearer + refresh 401. Viết trước, mọi màn dựng trên nó.
- **Type khớp backend** (§6): khai báo type response một nơi; nếu lệch schema là lỗi tích hợp, sửa ngay.
- **Realtime = tín hiệu → refetch** (RB-2): không bao giờ render payload WS.
- **Server là trọng tài quyền** (RB-3): FE ẩn/hiện nút cho UX, nhưng luôn xử lý 403/404/409/422 tử tế.
- Mỗi giai đoạn có tiêu chí "xong" quan sát được; review trước khi sang giai đoạn sau (theo nhịp backend).

## Quyết định GĐ1 — ĐÃ CHỐT (2026-08-05)

| Vấn đề | Chốt |
|---|---|
| Styling | **Tailwind CSS** (Stitch xuất được Tailwind — thuận cho bước mockup) |
| Lưu refresh token | **Cookie httpOnly qua Route Handler của Next** (access token giữ trong bộ nhớ) |
| Vị trí thư mục FE | **`frontend/` cạnh `backend/`** (monorepo nhẹ) |
| Thư viện data-fetching/cache | React Query (TanStack) — invalidate theo tín hiệu WS gọn (xác nhận khi khởi tạo GĐ1) |

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

1. ~~(Tuỳ chọn) Mockup UI bằng Stitch~~ — **XONG 2026-08-05.** Xem mục Mockup bên dưới.
2. Code theo giai đoạn 1→5, review từng giai đoạn. **Đang làm: GĐ1.**

## Mockup Stitch — XONG (2026-08-05)

- **Project:** `projects/5926030180396822885` — "OmniChat FE #F1 — Inbox & Reply".
- **Design system:** `assets/11208640140243586743` — "OmniChat Light Blue": primary `#1D6FF2`, nền panel `#F5F7FA`, viền `#E3E8EF`, font Be Vietnam Pro, bo góc 8px. Đã nạp sẵn quy ước màu badge kênh + badge 3 trạng thái + quy tắc bong bóng chat, nên các màn nhất quán.
- **6 màn:** Đăng nhập · Hộp thư `DANG_MO` (bản chính) · Hộp thư `CHO_PHAN` (vai Manager) · Hộp thư `DA_DONG` · Dialog Phân phòng. (Ba bản Hộp thư trùng do tool timeout-nhưng-vẫn-sinh; user đã giữ bản ưng nhất và xoá 2 bản thừa.)
- **Mockup phản ánh đúng ràng buộc spec:** ảnh đính kèm vẽ dưới dạng placeholder "[ảnh đính kèm]" (nợ (b) — chưa có route phục vụ ảnh); ô soạn tin khoá kèm dòng gợi ý ở cả `CHO_PHAN` lẫn `DA_DONG` (RB-5); nút hành động đổi theo vai + trạng thái (§3).
- **Mockup là tham chiếu thị giác, không phải nguồn sự thật.** Khi lệch, spec §6 (hợp đồng API) và §3 (quyền) thắng.

## Chi tiết GĐ1 — Khung & Auth

**Bối cảnh đã xác minh:** `frontend/` rỗng; Node v25.8.0, npm 11.11.0; backend chạy ở `/api/v1`.

**Sửa hợp đồng (đã cập nhật vào spec §6):** nhóm auth thật là `/api/v1/auth/{login,refresh,logout,me,change-password}` — spec bản đầu ghi thiếu đoạn `/auth`. `login`/`refresh` trả thêm `must_change_password`.

| # | Task | Xong khi |
|---|---|---|
| 1 | Khởi tạo Next.js (App Router, TS, Tailwind, ESLint) trong `frontend/`; `.env.example` với `NEXT_PUBLIC_API_BASE_URL`, `API_BASE_URL` | `npm run dev` chạy, `npm run build` sạch |
| 2 | `lib/types.ts` — khai báo type khớp schema backend (UserResponse, InboxItem, Conversation, Message, Attachment, PageResponse, TokenResponse) | Type khớp §6; một nguồn duy nhất |
| 3 | `lib/api-client.ts` — fetch bọc: base `/api/v1`, tự gắn Bearer, **refresh single-flight** 401→refresh→retry một lần, ném `ApiError{status, code, message}` | Test: nhiều 401 đồng thời chỉ gọi refresh MỘT lần (RB-4/IT-4) |
| 4 | Route Handlers `app/api/session/*` — đặt/xoá/đọc refresh token trong **cookie httpOnly** (`SameSite=Lax`, `Secure` khi production) | Refresh token không lộ ra JS; access token chỉ ở bộ nhớ |
| 5 | `AuthContext` — `login`/`logout`/`me`, giữ actor + access token trong bộ nhớ, khởi động thì thử refresh từ cookie | F5 vẫn giữ phiên; refresh hỏng → `/login` |
| 6 | Màn `/login` theo mockup + guard `/inbox*` (chưa đăng nhập → `/login`) | Đăng nhập được, `/me` hiện, route được bảo vệ |
| 7 | Layout có nav trái (Hộp thư active; Nhân sự/Báo cáo/Cấu hình để chỗ cho #4/#5/#2) | Khớp mockup, chưa cần chạy các mục sau |
| 8 | Xử lý `must_change_password` tối thiểu: báo + cho đổi qua `/auth/change-password` | Người dùng mật khẩu tạm không bị kẹt |

**Rủi ro cao nhất của GĐ1:** refresh single-flight (task 3) — viết test trước, vì GĐ5 (WS token xoay) dựng trên nó.

**GĐ1 XONG** (commit `052e4378`). Build/tsc/eslint sạch, 11/11 test đạt.

## Chi tiết GĐ2 — Inbox list: XONG

| # | Task | Trạng thái |
|---|---|---|
| 1 | `lib/inbox-api.ts` — lời gọi `GET /inbox` + khoá cache tập trung (GĐ5 cần để invalidate) | xong |
| 2 | `lib/hien-thi.ts` — nhãn tiếng Việt cho enum, lớp màu badge, định dạng mốc thời gian (+7 test) | xong |
| 3 | `components/badges.tsx`, `dong-hoi-thoai.tsx` — badge kênh/trạng thái, dòng danh sách | xong |
| 4 | `components/danh-sach-inbox.tsx` — chip lọc + phân trang + trạng thái tải/lỗi/rỗng | xong |
| 5 | Danh sách đặt ở `inbox/layout.tsx` để không dựng lại khi đổi hội thoại; route `/inbox/[id]` | xong |

**Bộ lọc và trang giữ trên URL** (`?status=&offset=`) thay vì state: tải lại trang / chia sẻ link vẫn đúng chỗ, nút lùi trình duyệt hoạt động.

**Kiểm chứng đầu-cuối (backend thật + trình duyệt thật):** 12/12 PASS với vai MANAGER và 12/12 với vai STAFF — guard, đăng nhập, danh sách, phân trang, badge, lọc, mở hội thoại, dòng đang chọn, không lỗi console. Manager thấy 15 hội thoại (có `CHO_PHAN`), Staff thấy 11 (không có) — phạm vi quyền do **server** quyết, đúng RB-3.

### Ba vấn đề môi trường phát hiện khi chạy thật (không phải lỗi GĐ2)

1. **DB thiếu 3 migration** (`closed_at` chưa có) → đã `alembic upgrade head`.
2. **Backend không chạy được bằng `uvicorn` CLI trên Python 3.13.** `cau_hinh_event_loop()` dùng `set_event_loop_policy`, nhưng 3.13 bỏ qua policy khi uvicorn tự dựng loop → psycopg ném `ProactorEventLoop`. Cách chạy được: `uv run python -c "import asyncio,selectors,uvicorn,src.main; asyncio.run(...(serve()), loop_factory=lambda: asyncio.SelectorEventLoop(selectors.SelectSelector()))"`. **Nợ backend: sửa `event_loop.py`/README cho Python 3.13.**
3. **Backend chưa có CORS** → trình duyệt chặn preflight, `/auth/me` hỏng. **User chốt: thêm `CORSMiddleware` vào backend** (vượt RB-1 nhưng là quyết định của user). Origin đọc từ `CORS_ALLOW_ORIGINS`, mặc định localhost:3000; không dùng `"*"` vì có `allow_credentials`. Đã kiểm: origin hợp lệ được phép, origin lạ bị 400. Backend sau thay đổi: 646 unit + 128 integration đạt, mypy sạch, 16/16 contract giữ.

### Nợ mới ghi ở GĐ2

- **Preview tin cuối trong dòng danh sách:** mockup có vẽ, nhưng `GET /inbox` trả `InboxItem` KHÔNG kèm tin nhắn → muốn preview phải gọi thêm N request. Bản đầu bỏ preview (RB-1 thắng mockup). Nếu cần, mở nợ backend thêm `last_message_preview` vào `InboxItem`.
- **Ô tìm kiếm** trong mockup chưa làm: backend không có tham số tìm kiếm ở `GET /inbox`.

Chi tiết từng task (files/interfaces/steps) viết khi bắt đầu mỗi giai đoạn, như cách backend #0–#5.
