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

## Chi tiết GĐ3 — Khung chat & Reply: XONG

| # | Task | Trạng thái |
|---|---|---|
| 1 | `inbox-api.ts`: `layChiTietHoiThoai` + `traLoiHoiThoai` | xong |
| 2 | `bong-bong-tin.tsx` — INBOUND trái/trắng, OUTBOUND phải/xanh, mốc thời gian, **placeholder "[ảnh đính kèm]"** (nợ b) | xong |
| 3 | `o-soan-tin.tsx` — khoá theo trạng thái (RB-5), Enter gửi / Shift+Enter xuống dòng, đếm ký tự gần trần 8000 (+4 test IT-2) | xong |
| 4 | `khung-chat.tsx` — header + danh sách tin + reply; lỗi 409/422/403 thì refetch đồng bộ trạng thái | xong |
| 5 | `/inbox/[id]` dùng `key={id}` để đổi hội thoại là dựng lại khung — không dính nội dung gõ dở sang hội thoại khác | xong |

**Quyết định đáng lưu:** ô soạn khoá **chỉ theo trạng thái**, KHÔNG theo `assigned_user_id`. Đã đọc `ReplyToConversation`: backend chỉ đòi đúng phòng + `DANG_MO`, không đòi người gọi là người đang xử lý. Khoá thêm theo người xử lý sẽ chặn nhầm Manager và đồng nghiệp cùng phòng vốn được phép trả lời.

**Kiểm chứng đầu-cuối (trình duyệt thật):**
- Luồng chat 9/9 PASS: `DANG_MO` gõ+gửi được và tin hiện ra; `DA_DONG` và `CHO_PHAN` khoá ô kèm gợi ý đúng (IT-2).
- **IT-5 6/6 PASS:** ép server trả 409 và ép mạng hỏng → nội dung đã gõ CÒN NGUYÊN, có báo lỗi rõ nghĩa; bỏ chặn gửi lại thì thành công và ô mới được xoá.
- API thật: reply vào `DANG_MO` → 200; reply vào `DA_DONG` → **422 `CONVERSATION_NOT_OPEN`** (RB-5 do server ép, FE chỉ phản ánh).

**Hạn chế kiểm thử:** adapter thật gọi API Zalo/Meta ngoài internet nên không chạy được ở máy dev (credential seed là giả → `InvalidToken`). Đã kiểm bằng một backend phụ ở cổng 8001 dùng **app thật**, chỉ thay adapter gửi tin + cipher bằng bản giả — quyền, máy trạng thái, DB, lưu tin vẫn là code thật. **Chưa từng gửi tin thật ra Zalo/Facebook.**

## Chi tiết GĐ4 — Hành động & vai: XONG

| # | Task | Trạng thái |
|---|---|---|
| 1 | `inbox-api.ts`: `nhanViec` / `dongHoiThoai` / `phanPhong` + `layPhongBanHoatDong` | xong |
| 2 | `lib/quyen-hanh-dong.ts` — logic ẩn/hiện nút tách riêng để test được (+15 test IT-3) | xong |
| 3 | `dialog-phan-phong.tsx` — modal radio phòng ban, Esc/bấm nền để đóng | xong |
| 4 | Ba nút trong header khung chat + xử lý 403/409/422 (toast + refetch) | xong |

**Quy tắc rút từ use case backend (không đoán):**

| Hành động | Điều kiện | Ai thấy nút |
|---|---|---|
| Nhận việc | `DANG_MO` + `assigned_user_id == null` | ai trong phạm vi phòng (gồm Staff) |
| Đóng | `DANG_MO` (kể cả đã có người nhận) | ai trong phạm vi phòng |
| Phân phòng | `CHO_PHAN` | MANAGER / ADMIN |

**Phát hiện quan trọng — `ASSIGN_OUT_OF_SCOPE`:** `AssignConversationToDepartment` chặn Manager phân về phòng KHÁC phòng mình (403). Nên dialog **lọc sẵn danh sách phòng theo vai**: Manager thấy đúng 1 phòng (và được chọn sẵn), Admin thấy tất cả. Hiện cả danh sách rồi để server từ chối là mời người dùng vào một thất bại đã biết trước. Đã kiểm bằng API thật: Manager phân về Phòng Kỹ thuật → 403 `ASSIGN_OUT_OF_SCOPE`; phân về phòng mình → 200, `CHO_PHAN` → `DANG_MO`.

**Bẫy đã tránh:** `take`/`close`/`assign` trả `Conversation` **không kèm `messages`**. Ghi đè thẳng response vào cache sẽ làm trắng khung chat — `apDungHoiThoaiMoi` giữ lại mảng tin đang có.

**Kiểm chứng đầu-cuối (trình duyệt thật, 3 vai):**
- **STAFF 9/9**, **MANAGER 15/15**, **ADMIN 15/15** PASS. Điểm mấu chốt: dialog hiện **1 phòng** với Manager và **2 phòng** với Admin.
- Ba luồng chạy thật: Nhận việc → header đổi "Đang được xử lý" + nút biến mất; Phân phòng → dialog đóng, badge thành "Đang mở"; Đóng → badge "Đã đóng", ô soạn khoá, nút hành động biến mất.
- **Xử lý lỗi 7/7 PASS:** ép 422 → báo lỗi rõ **và refetch** (kiểm đếm số lần GET detail: 0 → 1); ép 403 → nói rõ không có quyền, không trắng màn; ép mạng hỏng → gợi ý kiểm tra kết nối.

## Chi tiết GĐ5 — Realtime: XONG

| # | Task | Trạng thái |
|---|---|---|
| 1 | `api-client.ts`: thêm `onAccessTokenChange` — mắt xích để WS biết token đã xoay | xong |
| 2 | `lib/use-inbox-socket.ts` — giữ WS sống, backoff có nhiễu, mở lại khi token đổi (+9 test) | xong |
| 3 | `components/cau-noi-realtime.tsx` — tín hiệu → `invalidateQueries` (RB-2), đặt ở layout `/inbox` | xong |
| 4 | 4 test cho cơ chế báo token đổi trong `api-client.test.ts` | xong |

**Vì sao cần `onAccessTokenChange`:** WS mang access token ở **query string**, nên token cũ hết hạn thì server đóng 1008. Trước đây `refreshAccessToken` gán thẳng biến module — không ai được báo, và realtime sẽ **chết âm thầm sau lần refresh đầu tiên**. Nay refresh đi qua `setAccessToken`, phát sự kiện, hook mở lại WS bằng token mới.

**Thiết kế đáng lưu:**
- Tín hiệu chỉ dùng `conversation_id` để chọn khoá cache; **không đọc nội dung nào từ payload WS** (RB-2). Chi tiết chỉ invalidate nếu hội thoại đó đang có trong cache — tránh gọi REST cho hội thoại người dùng không mở.
- Backoff có **nhiễu ngẫu nhiên** để nhiều tab không cùng đập vào server một nhịp sau khi mạng trở lại; trần 30s, sàn 0,5s.
- Gỡ handler trước khi đóng socket cũ: nếu không, `onclose` của kết nối đã bỏ sẽ kích hoạt vòng thử-lại cho một kết nối không còn dùng.
- Callback giữ trong `ref` — đổi callback không được làm đứt kết nối đang chạy.

**Kiểm chứng đầu-cuối (trình duyệt thật):**
- **IT-1 hai tab 7/7 PASS:** hai tab cùng mở một hội thoại; gửi tin ở tab A → **tab B thấy mà KHÔNG F5** (đã kiểm `beforeunload` để chắc chắn không reload); đóng hội thoại ở A → B thấy badge "Đã đóng" và **ô soạn tự khoá** theo trạng thái mới.
- WS mở đúng `ws://127.0.0.1:8001/ws/inbox?token=***` — không dính tiền tố `/api/v1`.
- **Reconnect 4/4 PASS:** đóng WS từ phía server → tự mở lại → kết nối mới ở trạng thái OPEN → gửi tin vẫn chạy.
- **Token xoay 2/2 PASS:** ép 401 → refresh → WS mở lại (2 → 3 kết nối) với **token khác token ban đầu**.

**Một FAIL ban đầu hoá ra là lỗi kịch bản, không phải lỗi code:** `context.setOffline(true)` không làm rớt WS tới `127.0.0.1` (loopback không chịu ảnh hưởng của giả lập offline), nên không có sự kiện `close` nào để kích hoạt reconnect. Đã kiểm lại đúng cách bằng cách đóng socket từ phía server.

## #F1 Inbox & Reply — HOÀN TẤT 5/5 giai đoạn

| GĐ | Commit | Kiểm chứng |
|---|---|---|
| 1 — Khung & Auth | `d7cb27e8` | 11 test, IT-4 single-flight |
| 2 — Inbox list | `b472c296` | 12/12 PASS × 2 vai |
| 3 — Khung chat & Reply | `c688fc41` | 9/9 + IT-5 6/6 |
| 4 — Hành động & vai | `d248b658` | STAFF 9/9, MANAGER 15/15, ADMIN 15/15, lỗi 7/7 |
| 5 — Realtime | (commit này) | IT-1 7/7, reconnect 4/4, token xoay 2/2 |

Cộng thêm `b8da7f7b` (backend CORS). Tổng: **50 unit test**, build/tsc/eslint sạch. Năm bất biến IT-1…IT-5 của spec §8 đều đã kiểm.

### Nợ ghi ở GĐ2 — ĐÃ TRẢ (xem mục dưới)

- ~~Preview tin cuối~~ · ~~Ô tìm kiếm~~ — trả xong ở đợt trả nợ 2026-08-09.

## Đợt trả nợ 2026-08-09 — XONG 4/4

User chốt sửa backend (vượt RB-1, như đã làm với CORS).

### 1. `event_loop.py` cho Python 3.13 — XONG

**Nguyên nhân gốc:** `set_event_loop_policy` chỉ có tác dụng với code sau đó *hỏi* asyncio lấy loop. Chương trình tự dựng loop — uvicorn chạy từ dòng lệnh — bỏ qua policy hoàn toàn, nên psycopg gặp `ProactorEventLoop` và mọi request chạm DB trả 500.

- Thêm `chay_async(coro)` truyền thẳng `loop_factory` (cách duy nhất chắc chắn) và `tao_event_loop()`.
- Thêm `scripts/run_server.py` (`--host/--port/--reload`) thay lệnh `uvicorn` hỏng; README sửa lại kèm cảnh báo.
- `seed_admin.py` chuyển sang `chay_async`.
- **+5 test**, gồm ca then chốt: cố ý đặt policy Proactor rồi kiểm `chay_async` vẫn cho ra `SelectorEventLoop`.
- Kiểm thật: `uv run python -m scripts.run_server --port 8002` → `/health` OK và **login chạm DB thành công**.

### 2. Route phục vụ ảnh — XONG (URL ký số có hạn, user chọn)

**Vì sao không dùng Bearer:** thẻ `<img>` không gửi được header `Authorization`. Thay vào đó backend cấp URL mang chữ ký HMAC-SHA256 trên `(attachment_id, conversation_id, hạn)`, TTL 300s (`ATTACHMENT_URL_TTL_SECONDS`), ký bằng `jwt_secret_key` sẵn có — không thêm bí mật mới.

- `infrastructure/attachments/signed_url.py` + **8 test bảo mật**: sửa hạn làm hỏng chữ ký, chữ ký của tệp/hội thoại khác không tái dùng được, khoá khác không ký được, so sánh hằng thời gian.
- `GET /inbox/{cid}/attachments/{aid}?expires=&signature=` — kiểm chữ ký, kiểm tệp thuộc đúng hội thoại, `resolve()` chống path traversal, trả `inline` + `nosniff`.
- `AttachmentResponse` thêm `url`; `GET /inbox/{id}` cấp URL đã ký cho từng đính kèm.
- Kiểm thật với ảnh PNG: URL ký tải được (**200, image/png, 67 bytes, KHÔNG cần Bearer**); chữ ký sai → **403**; thiếu chữ ký → **422**.
- **Bẫy đã gặp và sửa:** backend trả đường dẫn TƯƠNG ĐỐI (cố ý — nó không biết mình sau proxy nào), nên trình duyệt gọi vào `localhost:3000` và **404**. FE ghép `API_BASE_URL` ở `bong-bong-tin.tsx`.

### 3. Tìm kiếm theo tên khách — XONG (+ bỏ dấu)

- `GET /inbox?q=` → subquery `customers` (giữ hình dạng kết quả nên sắp xếp/phân trang không đổi). Thoát `%`, `_`, `\` để không thành ký tự đại diện.
- **Phát hiện khi kiểm thật:** hoa/thường đã đúng nhưng gõ **không dấu không khớp** ("nguyen" → 0 kết quả). User chốt thêm `unaccent`: migration `d4e5f6a7b8c9` bật `unaccent` + `pg_trgm`, hàm wrapper IMMUTABLE, index GIN trgm trên `lower(immutable_unaccent(display_name))`.
- Kiểm thật: "nguyen" → ra "Nguyễn"; "do trung" → ra "Đỗ Trung Kiên" (cả `Đ` cũng bỏ dấu); `%` → 0 (thoát đúng); `q` rỗng → đủ 15.
- **+5 test**, gồm ca quan trọng nhất: **tìm kiếm KHÔNG nới rộng phạm vi quyền** — Staff gõ đúng tên khách phòng khác vẫn không thấy.
- FE: ô tìm kiếm có debounce 350ms, giữ `q` trên URL (dùng `replace` để không rác lịch sử), nút xoá, trạng thái "Không tìm thấy".

### 4. Preview tin cuối — XONG

- `last_texts_for_conversations()` dùng `DISTINCT ON` lấy tin cuối cho **cả trang trong MỘT truy vấn** — hỏi từng dòng sẽ thành N+1. Bỏ tin chỉ có ảnh (`text` rỗng) nên preview lấy tin có chữ gần nhất.
- `InboxItem.last_message_preview` cắt 120 ký tự, gộp khoảng trắng.
- `message_repo` là tham số **tuỳ chọn** của `ListInbox` — nơi gọi cũ không phải đổi.

**Kiểm chứng giao diện 11/11 PASS** (trình duyệt thật): preview hiện dưới tên khách; tìm kiếm không dấu ra đúng kết quả, URL giữ từ khoá, nút xoá chạy; **ảnh TẢI ĐƯỢC thật** (`naturalWidth > 0`, không chỉ có thẻ `<img>`) qua URL đã ký; không lỗi console.

**Backend sau đợt trả nợ:** 663 unit (+13) + 128 integration đạt, mypy sạch, ruff sạch, **16/16 import contract giữ nguyên**. FE: 50 test, build/tsc/eslint sạch.

Chi tiết từng task (files/interfaces/steps) viết khi bắt đầu mỗi giai đoạn, như cách backend #0–#5.
