# #F5 — Frontend Báo cáo (Analytics dashboard) — Thiết kế

Sub-project **cuối** của roadmap frontend. Trình bày 4 báo cáo tổng hợp đọc-chỉ
của module #5 (analytics) cho Manager/Admin.

**Spec này soạn SAU khi dò API thật** (15+ lời gọi, 2026-09-17) — theo bài học
`bai-hoc-goi-api-that`. Mọi hình dạng dữ liệu, mã lỗi, ngữ nghĩa null dưới đây
là **đo được**, không suy từ tên endpoint.

## 1. Phạm vi

Một khu riêng `/bao-cao/*` với 4 màn (mỗi báo cáo một tab):

| Tab | Endpoint | Nội dung |
|---|---|---|
| Hội thoại | `GET /analytics/conversations` | khối lượng tin theo (phòng, kênh) |
| Nhân viên | `GET /analytics/agents` | hiệu suất theo nhân viên |
| Ca & KPI | `GET /analytics/workforce` | số ca, giờ công, %KPI theo nhân viên |
| Đơn từ | `GET /analytics/requests` | đơn theo (phòng, loại, trạng thái) |

**Ngoài phạm vi:** `POST /analytics/rollups/rebuild` là công cụ VẬN HÀNH
(admin-only, backfill rollup), không phải màn người dùng. Bỏ khỏi #F5.

## 2. Quyền — KHÁC #F4

`/nhan-su` và `/tu-khoa` cho mọi vai. **Báo cáo thì không.** Đo thật:

- Staff → **403 `ANALYTICS_MANAGER_REQUIRED`** ở CẢ 4 endpoint. Chỉ Manager/Admin.
- → Layout `/bao-cao` PHẢI có `<ChanTheoVai cho="khuQuanTri">` (như `/quan-tri`),
  KHÔNG phải layout mở như `/nhan-su`.
- Nav-rail: mục "Báo cáo" chỉ hiện cho Manager/Admin (dùng `vaoDuocKhuQuanTri`),
  Staff không thấy — khác "Từ khoá"/"Nhân sự" (mọi vai thấy).

### RB-1 — Manager KHÔNG có ô chọn phòng

Đo thật: mgrA truyền `department_id` của phòng khác → backend **im lặng** trả về
phòng của chính mgrA, HTTP 200 (`pham_vi_phong_bao_cao` ép Manager về phòng mình,
RB-4 của #5). Một ô chọn phòng cho Manager sẽ **nói dối** — trông như đổi được mà
không đổi gì.

→ Ô lọc phòng **chỉ hiện cho Admin**. Đúng tiền lệ `hienBoLocPhongBan()` của #F2.
Thêm `chiAdminLocPhong(vai)` vào `quyen-bao-cao.ts` (bản sao của quy tắc backend).

## 3. Tham số & validation (đo thật)

Mọi endpoint nhận:
- `from` (alias, bắt buộc) + `to` (bắt buộc) — ngày `YYYY-MM-DD`, đóng hai đầu.
- `department_id` (tùy chọn, UUID) — chỉ Admin dùng thực chất.

Lỗi đo được:
- thiếu `from`/`to` → **422** `VALIDATION_ERROR`
- `from` > `to` → **400** `ANALYTICS_INVALID_DATE_RANGE`
- ngày sai định dạng / `department_id` không phải UUID → **422**
- khoảng rỗng (không có dữ liệu) → **`[]` HTTP 200** (không phải lỗi)

→ FE tự chặn `from > to` trước khi gọi (đỡ một vòng mạng), nhưng vẫn hiện thông
điệp server nếu lọt. Khoảng ngày mặc định: **30 ngày gần nhất** (`to` = hôm nay).

## 4. Hình dạng phản hồi & bẫy null-vs-0

**Tất cả trả MẢNG TRẦN** (không `PageResponse`). Không phân trang → tải hết một
lần, lọc/sắp ở client.

### 4.1 Conversations
```
{department_id: UUID|null, channel_platform: str,
 inbound_count, outbound_count, opened_count, closed_count: int}
```
- **`department_id: null` XUẤT HIỆN THẬT** (hội thoại `CHO_PHAN` chưa phân phòng —
  đo: TELEGRAM 9 inbound, dept null). Hiện tên bucket **"Chưa phân phòng"**, KHÔNG
  để ô trắng.
- `channel_platform` là enum `Platform` → dùng `NHAN_KENH` + `LOP_BADGE_KENH` sẵn có.
- Các count luôn là số (0 nghĩa là đã đếm = 0).

### 4.2 Agents
```
{user_id: UUID, handled_count, assigned_count: int,
 avg_first_response_seconds: float|null, avg_resolution_seconds: float|null}
```
- **`avg_first_response_seconds: null` đi kèm `handled_count: 2` — đo thật.** Có
  việc nhưng chưa có mẫu phản hồi. `null` = **chưa đo được** (dash), 0 = phản hồi
  tức thì. Không suy null → 0.
- Trình bày thời-lượng: giây → "x phút", "x giờ y phút" (helper `khoangThoiGian`).

### 4.3 Workforce (Ca & KPI)
```
{user_id: UUID, department_id: UUID|null,
 shift_count, worked_seconds: int, kpi_percent: float|null, period: str|null}
```
- **`kpi_percent` và `period` đi CẶP** (đo thật cả ba hình dạng):
  - `null` / `null` → chưa đặt target tháng đó → dash.
  - `0.0` / `"2026-09"` → đã đo, hoàn thành 0% → **"0%"** (khác dash!).
  - `>0` / `"2026-09"` → phần trăm thật.
- `period` là kỳ KPI (`YYYY-MM` = tháng của `to`). Hiện cạnh %KPI để rõ đây là số
  của tháng nào, không phải của cả khoảng báo cáo.
- `worked_seconds` → giờ:phút.

### 4.4 Requests
```
{department_id: UUID|null, request_type, status: str,
 count: int, avg_decision_seconds: float|null}
```
- `request_type` (`NGHI_PHEP`…) / `status` (`DA_DUYET`,`TU_CHOI`,`CHO_DUYET`,`DA_HUY`)
  là enum → dùng `NHAN_LOAI_DON`, `NHAN_TRANG_THAI_DON`, badge sẵn của #F3.
- `avg_decision_seconds: null` khi chưa có đơn đã quyết → dash.

## 5. Bẫy TÊN — hạng nặng (chỉ lộ khi gọi thật)

Báo cáo trả **UUID trần, không có tên**. FE phải tự join. Nhưng:

1. `/users` của **Manager chỉ trả người TRONG phòng mình** (đo: total=2). `/users/{id}`
   người ngoài phòng → **403 `CANNOT_VIEW_USER`**.
2. Báo cáo agents chứa **user `department_id=null`** (Admin "Quản trị hệ thống" đã
   xử lý hội thoại — đo thật). Manager **KHÔNG BAO GIỜ** resolve được tên người này.
3. `/users` cap `limit=100` (total hiện 27 — đủ, nhưng đừng giả định vô hạn).

→ **Chiến lược tra tên (RB-2):**
- Tải một `Map<user_id, full_name>` và `Map<dept_id, name>` từ `/users?limit=100`
  và `/departments` (phạm vi backend tự lọc theo vai).
- Khi báo cáo có id **không có trong map** (người ngoài phòng của Manager, hoặc
  Admin dept=null): hiện **mã rút gọn** `#a1b2c3d4` (8 ký tự đầu UUID) — KHÔNG
  hiện "undefined"/ô trắng, KHÔNG gọi `/users/{id}` (chắc chắn 403).
- Helper `tenNguoi(map, id)` / `tenPhong(map, id|null)` một chỗ; `null` dept →
  "Chưa phân phòng".

## 6. UI mỗi màn

Một khung chung `KhungBaoCao`: bộ chọn khoảng ngày (2 `<input type="date">` —
native, không lib) + (chỉ Admin) ô chọn phòng, rồi bảng.

- Trạng thái: đang tải (skeleton), rỗng (`[]` → "Không có dữ liệu trong khoảng
  này."), lỗi (hiện thông điệp server).
- Bảng: sắp xếp mặc định theo cột số chính giảm dần. Tổng cộng ở chân bảng cho
  các cột đếm (client tự cộng — dữ liệu đã tải hết).
- Số: `Intl.NumberFormat` cho hàng nghìn; dash `—` cho null (dùng lại `DAU_GACH`).

## 7. File dự kiến

```
frontend/src/lib/bao-cao-api.ts            # 4 hàm GET + khoá cache
frontend/src/lib/quyen-bao-cao.ts (+.test) # chiAdminLocPhong, vào khu
frontend/src/lib/hien-thi.ts               # + khoangThoiGian, tenNguoi, tenPhong (test)
frontend/src/lib/types.ts                  # + 4 kiểu *ReportItem
frontend/src/app/bao-cao/layout.tsx        # AuthGuard + ChanTheoVai + TabBaoCao
frontend/src/app/bao-cao/hoi-thoai/page.tsx
frontend/src/app/bao-cao/nhan-vien/page.tsx
frontend/src/app/bao-cao/ca-kpi/page.tsx
frontend/src/app/bao-cao/don-tu/page.tsx
frontend/src/components/tab-bao-cao.tsx
frontend/src/components/bao-cao/khung-bao-cao.tsx   # chọn ngày + phòng + khung bảng
frontend/src/components/bao-cao/bang-*.tsx          # 4 bảng
frontend/src/components/nav-rail.tsx       # đổi placeholder "Báo cáo" thành link (Mgr/Admin)
```

## 8. Quy tắc kiểm chứng

- Test FE (`node` env): logic thuần — `quyen-bao-cao`, `khoangThoiGian`,
  `tenNguoi`/`tenPhong` (đặc biệt: id không có trong map → mã rút gọn; dept null →
  "Chưa phân phòng"), null-vs-0 của %KPI.
- Trình duyệt (Playwright): Admin thấy 4 tab + ô chọn phòng + đủ dữ liệu 3 hình
  dạng null; Manager KHÔNG có ô chọn phòng, thấy phòng mình, id ngoài phòng hiện
  mã rút gọn; Staff bị `ChanTheoVai` chặn ở cửa và không thấy mục nav "Báo cáo".
- Đối chiếu số liệu bảng với lời gọi API thật (không chỉ "có render").
