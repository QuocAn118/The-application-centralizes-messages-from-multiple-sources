# Tổng kết đợt redesign giao diện (26–29/09/2026)

Đổi toàn bộ frontend sang **Neo-Brutalism**, kèm 10 thay đổi backend (BE-1…BE-10)
và 6 migration. Làm theo từng phần; mỗi phần có spec riêng (`docs/superpowers/specs/2026-09-2*-ui-redesign-*.md`),
được duyệt kèm ảnh chụp trước khi merge. Bản rà soát UX ban đầu (GĐ1) nằm ở
`2026-09-26-ui-redesign-gd1-ra-soat-ux.md`. Mục §10 của file đó ghi các quyết định
sau duyệt và **thay thế** những đoạn trước nó.

Điểm bắt đầu: `2b6b6e89`. Toàn đợt: 246 file, +17 434 / −4 070 dòng.

## 1. Đã làm gì, theo từng phần

| Phần | Merge | Nội dung |
|---|---|---|
| **1 — Design system + khung app** | `c87a5075` | Token màu/bóng/viền (tương phản đã kiểm bằng test đọc thẳng CSS). Token cũ được ánh xạ sang giá trị mới để màn chưa làm không vỡ. Component gốc ở `components/ui/`: `Nut`, `NutIcon`, `ONhap`/`VungNhap`/`OChon`, `Truong`, `The`, `DauTrang`, `TabKhu`, `HuyHieu`, `Bang`, `Avatar`, `IconKenh`, `GoiY`, `MenuHanhDong`, `TrangThai*`. Thêm trang `/design-system` (chỉ chạy ở dev), nav rail có huy hiệu và đổi tên "Quản trị" thành "Cấu hình" |
| **2a — Hộp thư** | `cea379ee` | Danh sách hai tầng: tab Của tôi / Chưa ai nhận / Tất cả, số chưa đọc, "Chờ N phút", cuộn liên tục. Khung chat có dòng hệ thống, vạch ngày, gom tin theo nhóm. Header có nút đổi người phụ trách. Tín hiệu realtime chỉ phát **sau commit** (`NotifierSauCommit`). Backend: BE-1, BE-2, BE-3, BE-9 |
| **2b — Panel khách + ô soạn** | `9f494bc8` | Panel khách có lịch sử, ghi chú theo phòng và nhãn. Ô soạn có mẫu trả lời: gõ `/` hoặc bấm nút. Thêm dòng hệ thống phân phòng. Backend: BE-4, BE-5, BE-6, BE-7 |
| An toàn dữ liệu | `8c83c2d1` | Phiên DB commit **trước** khi trả phản hồi. Quyền phân tích lại xét theo phòng hiện tại. Token WebSocket được che trong log uvicorn (tạm thời, xem WS-1) |
| **3 — Nhân sự** | `e3a5b20a` | Lịch phân ca dạng lưới, Đơn từ, KPI có thanh tiến độ |
| **4 — Từ khoá + Phân tích AI** | `9a034a20`, `506c8044` | Từ khoá dạng chip gom theo phòng, thêm nhanh. Phân tích có bộ lọc "Cần xem lại". Backend: BE-10 và 409 kèm từ khoá trùng |
| CI + bản vá | `6996ff44`, `8504b33f` | CI sinh `CHANNEL_CIPHER_KEY` ngẫu nhiên. Next.js 16.3.0 → 16.3.6 vá GHSA-p293-qw3h-jr36 và GHSA-2xp9-vwfh-vxw4; `npm audit` còn 0 lỗ hổng |
| **5 — Báo cáo** | `75c1b7fd`, `04e7dea6` | Tổng quan có 4 thẻ số, biểu đồ xu hướng (Recharts) và bảng. Bốn tab dùng chung khung chọn khoảng thời gian. Backend: BE-8. ADR ghi việc module khác đọc bảng `conversations` |
| **6 — Cấu hình + Xác thực** | `36f6651d` | Đăng nhập và Đổi mật khẩu bố cục chia đôi: báo lỗi chung, cảnh báo Caps Lock, nhớ email, điều kiện mật khẩu tick dần. Bảng Cấu hình dùng menu "⋯", ẩn mục đã ngừng/ngắt, lỗi hiện dưới đúng ô. Thêm tab **Nhãn** và **Mẫu trả lời** trong Cấu hình |
| **GĐ4 — Hoàn thiện** | nhánh `feat/hoan-thien-gd4` | 5 hộp thoại Nhân sự dùng component chung. Bỏ token cũ và các lớp màu không còn ai dùng. Sửa 4 lỗi FE tìm được khi code-review. Thêm kịch bản rà nhất quán `ui-nhat-quan` |

Thư viện thêm: `lucide-react` (icon), `@radix-ui/react-dialog`, `-dropdown-menu`,
`-tooltip` (dùng thẳng Radix, không qua shadcn), `recharts` (chỉ cho Báo cáo),
`simple-icons` (logo kênh thật).

## 2. Thay đổi backend

Mọi thay đổi đều có test và được duyệt trước khi làm. Import-linter (16 hợp đồng)
không đổi.

| Mã | Tính năng | API | Dữ liệu |
|---|---|---|---|
| BE-1 | Chưa đọc **theo từng người** | `POST /inbox/{id}/read` (204), `GET /inbox/unread-count`, `InboxItem.unread_count` | Bảng `conversation_reads`, partial index `messages(conversation_id, created_at) WHERE direction='INBOUND'` |
| BE-2 | Giao / đổi / gỡ người phụ trách, timeline | `POST /inbox/{id}/assign-user {user_id\|null}`, `GET /inbox/{id}` thêm `events[]` | Bảng `conversation_events`. **Đổi quy tắc:** trước đây người phụ trách là cố định; giờ Manager (phòng mình) và Admin được đổi hoặc gỡ. So-và-đổi ở repository nên hai người đổi cùng lúc thì một người nhận 409 |
| BE-3 | Lọc "Của tôi" / "Chưa ai nhận" | `GET /inbox?assignee=me\|none` | — |
| BE-4 | Lịch sử hội thoại của khách (trong cùng kênh) | `GET /inbox?customer_id=` | — |
| BE-5 | Ghi chú nội bộ theo phòng | `GET/POST /customers/{id}/notes`, `DELETE /notes/{id}` | Bảng `customer_notes` (có `department_id` của người viết) |
| BE-6 | Nhãn khách dùng chung | `GET/POST/PATCH /tags`, `GET/PUT /customers/{id}/tags` | Bảng `tags`, `customer_tags`; màu chỉ nhận `swatch-1..8` |
| BE-7 | Mẫu trả lời | CRUD `/reply-templates` | Bảng `reply_templates` (`department_id` null = mẫu dùng chung) |
| BE-8 | Tổng quan báo cáo | `GET /analytics/overview?from&to&department_id` | — (đọc bảng rollup có sẵn) |
| BE-9 | Khách chờ bao lâu | `InboxItem.waiting_since` | — (dùng index của BE-1) |
| BE-10 | Lọc phân tích cần xem lại | `GET /analyses?outcome=` (truyền được nhiều lần); Manager thấy thêm hội thoại đang chờ phân; 409 `KEYWORD_DUPLICATE` kèm `details.existing_keyword` | — |

Thêm vào phản hồi, không đổi schema: `assigned_user_name`, `customer_external_id`,
và tên người/phòng trong `events` (backend tra qua `IWorkforceDirectory`).

### Migration (theo thứ tự, head mới `f2a3b4c5d6e7`)

| Revision | Nội dung | `downgrade()` |
|---|---|---|
| `a7b8c9d0e1f2` | `conversation_reads` + index tin vào | Xoá bảng và index |
| `b8c9d0e1f2a3` | `conversation_events` | Xoá bảng (**mất timeline**) |
| `c9d0e1f2a3b4` | `conversation_events` thêm `department_id`, `detail` và 2 loại sự kiện mới | **Xoá các dòng** `DEPARTMENT_ASSIGNED`/`AUTO_ROUTED` rồi dựng lại ràng buộc cũ |
| `d0e1f2a3b4c5` | `customer_notes` | Xoá bảng (**mất ghi chú**) |
| `e1f2a3b4c5d6` | `tags`, `customer_tags` | Xoá bảng (**mất nhãn**) |
| `f2a3b4c5d6e7` | `reply_templates` | Xoá bảng (**mất mẫu**) |

Cả 6 migration chỉ **thêm**, không sửa cột cũ. Mỗi migration đã thử up → down → up.

## 3. Quyết định đã chốt

- Chỉ hỗ trợ desktop 1280–1920px. Màn hẹp hơn thì cuộn ngang. App mobile sẽ làm riêng.
- Không có dark mode. Giá trị null hiện `—`. Chữ nhỏ nhất 12px, có test kiểm.
- Quy tắc bóng: nút có bóng nhỏ và phản hồi khi nhấn; thẻ/bảng có bóng làm khung, không phản hồi; huy hiệu không có bóng.
- `primary` là màu cobalt, không phải vàng. Vàng (`accent`) dành cho nút chính và mục đang chọn.
- Logo kênh là logo thật lấy từ `simple-icons`. Riêng Zalo dựng chữ trắng trên nền xanh.
- Chưa đọc tính theo từng người, và hội thoại đã đóng luôn tính 0. Tỉ lệ phản hồi = số hội thoại có ít nhất 1 tin trả lời chia cho số hội thoại có tin vào trong kỳ. Thời gian phản hồi trung bình tính có trọng số.
- Nhãn dùng chung toàn công ty. Manager/Admin quản lý nhãn, mọi vai được gắn/gỡ. Màu nhãn chỉ chọn trong bảng màu đã kiểm.
- Ghi chú chỉ phòng của người viết xem được. Ghi chú Admin viết chỉ Admin xem được.
- Manager/Admin được đổi hoặc gỡ người phụ trách. "Nhận việc" và tự giao vẫn giữ quy tắc không cướp việc.
- Quản lý Nhãn/Mẫu trả lời có ở **cả hai chỗ**: tab trong Cấu hình và lối tắt trong Hộp thư, dùng chung component.
- Đăng nhập chỉ báo "Sai email hoặc mật khẩu." cho cả email không tồn tại lẫn sai mật khẩu. Chỉ nhớ email, không nhớ mật khẩu.
- Mọi migration có `downgrade()`. Kịch bản kiểm chứng cũ phải luôn qua; khi đổi UI có chủ đích thì sửa kịch bản và ghi lý do, không nới lỏng điều kiện kiểm.

## 4. Triển khai bản mới

Repo **không có** cấu hình production (không compose, không workflow deploy, không
Dockerfile frontend — chỉ `backend/Dockerfile`). Các bước dưới đây giả định một
máy chạy ba tiến trình như lúc dev: API, worker phân tích, frontend.

**Biến môi trường mới: không có.** Đợt redesign không thêm biến nào ở backend
(`.env.example` không đổi) hay frontend (vẫn `NEXT_PUBLIC_API_BASE_URL`, `API_BASE_URL`).

1. **Sao lưu DB** (bắt buộc: `downgrade` của 5/6 migration xoá dữ liệu mới):
   `pg_dump -Fc -f omnichat-truoc-redesign.dump "$DATABASE_URL_THUONG"`
   (URL dạng `postgresql://…`, bỏ `+psycopg`).
2. **Kiểm head hiện tại:** `cd backend && uv run alembic current` → mong đợi
   `f6a7b8c9d0e1`. Khác thì dừng, đối chiếu trước.
3. **Dừng API và worker** (`scripts.run_worker`). Code mới ghi vào bảng/cột mới
   (worker ghi dòng `AUTO_ROUTED`), nên KHÔNG được chạy code mới trước khi migrate.
4. **Migration:** `cd backend && uv sync --locked && uv run alembic upgrade head`
   → head `f2a3b4c5d6e7`. Index `ix_message_inbound_conv_created` tạo KHÔNG
   `CONCURRENTLY`: bảng `messages` bị khoá ghi trong lúc dựng — với vài chục
   nghìn tin chỉ vài giây, lớn hơn nhiều thì chạy lúc vắng.
5. **Khởi động lại API + worker** với code mới.
6. **Frontend:** `cd frontend && npm ci && npm run build && npx next start -p <cổng>`
   (Next 16.3.6 nằm trong `package-lock.json` — `npm ci` lấy đúng bản đã vá).
7. **Kiểm nhanh:** `GET /health`; đăng nhập; mở Hộp thư (số chưa đọc, dòng hệ
   thống); Báo cáo tổng quan; `npm audit` = 0.

**Lưu ý sau khi lên:** `conversation_reads` rỗng nên **mọi tin vào của hội thoại
đang mở hiện là chưa đọc** với mọi người (huy hiệu có thể là 99+), tới khi từng
người mở hội thoại. Nếu không muốn, có thể đánh dấu đã đọc tới thời điểm triển
khai cho mọi (người, hội thoại đang mở) trong phạm vi — việc này ghi dữ liệu, cần
duyệt riêng. Timeline (`conversation_events`) bắt đầu từ lúc triển khai: hội thoại
cũ không có dòng hệ thống.

**Quay lại nếu lỗi:**
- *Lỗi ở code, DB vẫn ổn* (thường gặp nhất): chạy lại bản cũ, **giữ nguyên DB**.
  Migration chỉ thêm bảng/cột nullable, code cũ không đọc chúng nên chạy được trên
  schema mới. Không mất dữ liệu.
- *Buộc phải lùi schema:* dừng API + worker → `uv run alembic downgrade f6a7b8c9d0e1`
  → chạy bản cũ. **Mất** ghi chú, nhãn, mẫu trả lời, timeline, trạng thái đã đọc
  tạo từ lúc lên bản mới (xem bảng migration §2).
- *Migration hỏng giữa chừng:* `migrations/env.py` chạy cả lần `upgrade` trong
  MỘT transaction (không bật `transaction_per_migration`), PostgreSQL lùi được DDL
  → hỏng ở revision nào thì cả 6 cùng lùi, `alembic current` vẫn là `f6a7b8c9d0e1`.
  Chạy lại bản cũ là xong. Trường hợp xấu hơn: `pg_restore --clean -d … omnichat-truoc-redesign.dump`.

## 5. Backlog còn lại

Chi tiết từng mục (vấn đề, hiện trạng, phương án) ở `docs/backlog.md`.

| Mã | Việc | Ghi chú |
|---|---|---|
| WS-1 | Xác thực WebSocket bằng vé dùng một lần | Hiện access token vẫn nằm trên query string; log uvicorn đã che token, nhưng proxy vẫn thấy |
| KH-1 | Nhận diện khách xuyên kênh | Mỗi kênh đang là một khách riêng (`customers.channel_id`), nên lịch sử chỉ trong cùng kênh |
| NH-1 | Giao diện đổi tên nhãn | `PATCH /tags/{id}` đã nhận `name` và `color` (FE có sẵn `suaNhan`). UI mới chỉ có tạo và ngừng/bật lại |
| KH-2 | Nhập tay thông tin liên hệ khách | Hoãn theo GĐ1 §10.1 #4. Nền tảng không gửi SĐT/email |
| HT-1 | Ngưỡng "Chờ N phút" là hằng số 15 phút | `NGUONG_CHO_PHUT` trong `frontend/src/lib/hop-thu.ts`. Muốn mỗi phòng một ngưỡng thì cần cấu hình phía backend |
| HT-2 | Nhận việc / tự giao có thể ghi đè một lần giao tay chen giữa | Code-review GĐ4. `TakeConversation` và #3 ghi người phụ trách không so-và-đổi, khác `/assign-user`. Cách sửa: dùng `doi_nguoi_phu_trach_neu_chua_doi` (đã có), trả 409 khi lệch. **Chờ duyệt** vì là thay đổi backend |
