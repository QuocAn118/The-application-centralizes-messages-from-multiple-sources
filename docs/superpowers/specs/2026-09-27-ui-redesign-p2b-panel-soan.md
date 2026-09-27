# Redesign Phần 2b — Panel khách + ô soạn (BE-4, BE-5, BE-6, BE-7 + dòng phân phòng)

Nguồn: [GĐ1 §5 + §10](2026-09-26-ui-redesign-gd1-ra-soat-ux.md) (đã duyệt),
[Phần 2a](2026-09-27-ui-redesign-p2a-hop-thu.md) (đã duyệt + merge `cea379ee`).
Nhánh: `feat/ui-hop-thu-2b`. Spec soạn SAU khi dò code thật (bài học "gọi API thật").

## 1. Phạm vi

Panel khách thêm: **lịch sử hội thoại** (BE-4), **ghi chú nội bộ theo phòng**
(BE-5), **nhãn** (BE-6). Ô soạn thêm **mẫu trả lời** (BE-7). Khung chat thêm
**dòng phân phòng** (user yêu cầu khi duyệt 2a). Không làm: lọc hộp thư theo nhãn,
liên hệ nhập tay (đã hoãn).

## 2. Điều phát hiện khi dò code (khác GĐ1)

1. **"Khớp từ khoá Y" không có sẵn.** Lúc tự phân, #2 chỉ biết *cụm nhu cầu* LLM
   trích ra (`ExtractedTerm.normalized`) và phòng LLM chọn — không có "từ khoá nào
   khớp". Để câu "khớp từ khoá Y" đúng sự thật, #2 **so chuỗi**: từ khoá (đã chuẩn
   hoá) của phòng được chọn nằm trong cụm nhu cầu (đã chuẩn hoá). Có khớp → "khớp
   từ khoá Y, Z"; không khớp (LLM suy luận) → "theo nhu cầu: a, b".
2. **Customer gắn với kênh** (`customers.channel_id`): cùng một người nhắn qua
   Zalo và Facebook là HAI khách. Lịch sử (BE-4) vì thế chỉ là lịch sử **trong
   cùng kênh**. Ghép khách xuyên kênh là việc khác, không làm.
3. **Admin không thuộc phòng** → ghi chú Admin viết có `department_id = null`, chỉ
   Admin thấy; UI ghi "Chỉ quản trị viên thấy ghi chú này".
4. **Ai quản lý nhãn/mẫu ở đâu:** khu "Cấu hình" chỉ Admin vào được, mà Manager
   cũng phải quản lý. → Quản lý bằng **hộp thoại ngay trong Hộp thư** ("Quản lý
   nhãn" trong ô chọn nhãn, "Quản lý mẫu" trong danh sách mẫu), chỉ hiện với
   Manager/Admin. Không thêm trang/mục nav.

## 3. Backend (module `inbox`; không import identity — tên qua `IWorkforceDirectory`)

### 3.1 BE-4 — Lịch sử
`GET /inbox?customer_id=` lọc thêm; phạm vi theo vai **giữ nguyên** (Staff không
thấy hội thoại phòng khác của cùng khách).

### 3.2 Dòng phân phòng (mở rộng `conversation_events`)
Migration thêm cột `department_id uuid null`, `detail text null`. Loại mới:

| kind | Ghi khi | Dòng |
|---|---|---|
| `DEPARTMENT_ASSIGNED` | Manager/Admin bấm Phân phòng | "A phân về Phòng X" |
| `AUTO_ROUTED` | #2 tự phân | "Tự động chuyển tới Phòng X — khớp từ khoá Y" / "— theo nhu cầu: a, b" |

`IConversationRouter.assign_to_department(conv, dept, ly_do: str \| None = None)`.
Tên phòng: `IWorkforceDirectory.get_department_names(ids)` (tra theo lô).
`events[]` thêm `department_name`, `detail`.

### 3.3 BE-5 — Ghi chú theo phòng
Bảng `customer_notes(id, customer_id, department_id null, author_id, body, created_at)`,
index `(customer_id, department_id, created_at)`.
- `GET /customers/{id}/notes`: Admin thấy tất cả; người khác chỉ ghi chú có
  `department_id = phòng mình`.
- `POST /customers/{id}/notes {body}` (1–2000 ký tự): `department_id` = phòng người
  viết lúc viết.
- `DELETE /notes/{id}`: người viết (và vẫn cùng phòng) hoặc Admin → 204.
- **Được đụng tới khách** = có ít nhất một hội thoại của khách mà người gọi xem
  được (`co_the_thao_tac`). Không → 404 (không lộ khách tồn tại).
- Test bắt buộc: nhân viên phòng A **không** đọc được ghi chú phòng B qua API.

### 3.4 BE-6 — Nhãn dùng chung
Bảng `tags(id, name, color, is_active, created_at)` (tên duy nhất không phân biệt
hoa thường/dấu cách thừa), `customer_tags(customer_id, tag_id, PK)`.
- `color` ∈ `swatch-1..swatch-8` (bảng màu đã kiểm tương phản) — backend từ chối
  giá trị khác (422).
- `GET /tags` (mọi vai; `?include_inactive=true` cho Manager/Admin),
  `POST /tags`, `PATCH /tags/{id}` (tên/màu/ngừng dùng) — Manager/Admin.
  Không xoá cứng: ngừng dùng thì nhãn biến khỏi ô chọn, khách đang gắn vẫn giữ.
- `PUT /customers/{id}/tags {tag_ids}` — ai đụng được khách đều gắn/gỡ được; chỉ
  gắn MỚI được nhãn đang dùng.
- Nhãn đang gắn của khách: `GET /customers/{id}/tags` (endpoint riêng — không đụng
  use case chi tiết hội thoại).

### 3.5 BE-7 — Mẫu trả lời
Bảng `reply_templates(id, department_id null=dùng chung, title, body, created_at, updated_at)`.
- `GET /reply-templates`: Staff/Manager thấy dùng chung + phòng mình; Admin thấy tất cả.
- `POST/PATCH/DELETE`: Manager chỉ mẫu của phòng mình (không tạo mẫu dùng chung);
  Admin mọi mẫu. Xoá cứng (mẫu không phải dữ liệu kiểm toán) → 204.
- Không đụng luồng gửi tin: FE chỉ chèn chữ vào ô soạn.

## 4. Frontend

- **Panel khách** (sau 3 mục của 2a): Nhãn (chip màu + ô chọn gắn/gỡ; Manager/Admin
  có "Quản lý nhãn"), Ghi chú (danh sách + ô viết, dòng "Chỉ phòng X thấy ghi chú
  này", xoá có xác nhận), Lịch sử (các hội thoại khác của khách: trạng thái, mốc,
  xem trước; bấm để mở).
- **Ô soạn**: nút mẫu (icon lucide) + gõ `/` ở đầu ô → danh sách lọc theo chữ gõ,
  ↑↓ Enter chọn, Esc đóng; chọn là thay chữ `/…` bằng nội dung mẫu. Manager/Admin
  có "Quản lý mẫu".
- **Dòng hệ thống** 2 loại mới.

## 5. Kiểm chứng
Test backend cho mọi endpoint (quyền, phạm vi phòng, 404 không lộ, màu ngoài bảng,
trùng tên nhãn), migration up→down→up; test FE logic (lọc mẫu theo `/`, câu dòng hệ
thống mới). 12 kịch bản gốc + `ui-p2a` + kịch bản mới `ui-p2b`. Ảnh 1440px trước/sau.

## 6. Task
T1 BE-4 · T2 dòng phân phòng · T3 BE-5 · T4 BE-6 · T5 BE-7 · T6 FE lib · T7 FE panel
(nhãn/ghi chú/lịch sử) · T8 FE mẫu trả lời · T9 kiểm chứng + ảnh. Mỗi task một commit.
