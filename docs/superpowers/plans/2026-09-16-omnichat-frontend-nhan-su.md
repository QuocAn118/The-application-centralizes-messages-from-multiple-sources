# Plan #F3 — Frontend Nhân sự

**Spec:** [2026-09-16-omnichat-frontend-nhan-su-design.md](../specs/2026-09-16-omnichat-frontend-nhan-su-design.md)
**Nhánh:** `feat/fe-nhan-su`

Ba giai đoạn, mỗi giai đoạn tự đứng được và kết thúc bằng một commit chạy được
kèm kiểm chứng thật — như #F2.

**Thứ tự cố ý khác #F2:** ở #F2 tôi làm màn khó nhất (Người dùng) trước. Ở đây
làm **Đơn từ trước Ca làm việc**, vì RB-2 (ai duyệt đơn nào) là rủi ro lớn nhất
và cần biết sớm nó có làm được không — còn màn Ca tuy to hơn nhưng không có ẩn
số nào.

---

## Giai đoạn 1 — Nền chung + màn Đơn từ

| # | Việc | Xong khi |
|---|---|---|
| 1.1 | Type + `lib/nhan-su-api.ts` + `lib/quyen-nhan-su.ts`; mở khoá mục Nhân sự ở `nav-rail` (mọi vai) | `tsc` sạch, khớp schema backend |
| 1.2 | Khung `/nhan-su` + thanh tab ba màn | Staff vào được, không bị chặn |
| 1.3 | Danh sách đơn + lọc theo trạng thái + phân trang | Ba vai thấy đúng phạm vi |
| 1.4 | Gửi đơn — `NGHI_PHEP` có khoảng ngày, hai loại kia không (RB-1: Admin không thấy nút) | Admin không có nút gửi |
| 1.5 | Duyệt · Từ chối (bắt buộc lý do, RB-7) · Thu hồi | RB-2 đúng cho cả hai chiều |
| 1.6 | Test: quyền duyệt theo vai NGƯỜI GỬI, nhãn phủ đủ `RequestType`/`RequestStatus` | `npm test` xanh |

### Kiểm chứng GĐ1

Staff gửi đơn → Manager phòng đó duyệt được. Manager gửi đơn → Manager khác
không duyệt được, chỉ Admin duyệt. Không ai thấy nút duyệt trên đơn của chính
mình. Admin không thấy nút gửi đơn.

---

## Giai đoạn 2 — Màn Ca làm việc

Giai đoạn lớn nhất: hai thực thể lồng nhau (mẫu ca ↔ buổi phân ca).

| # | Việc | Xong khi |
|---|---|---|
| 2.1 | Danh sách mẫu ca + tạo/sửa/ngừng (RB-4: ca **không** qua đêm) | Ca 22:00–06:00 bị chặn kèm giải thích |
| 2.2 | Lịch phân ca theo tuần: hàng nhân viên × cột ngày | Staff chỉ thấy hàng của mình |
| 2.3 | Phân ca — ô chọn nhân viên lọc theo phòng của mẫu ca (RB-6) | Không hiện người ngoài phòng |
| 2.4 | Huỷ phân ca | |
| 2.5 | Test + kiểm chứng: phân trùng giờ hiện thông điệp server (RB-5) | Xanh |

---

## Giai đoạn 3 — Màn KPI + review tổng

| # | Việc | Xong khi |
|---|---|---|
| 3.1 | Danh sách mục tiêu theo kỳ (năm/tháng) | |
| 3.2 | Đặt mục tiêu — chỉ ô `target_value` (RB-3) | Không có ô nhập thực đạt |
| 3.3 | Tiến độ: `null` hiện dấu gạch, không hiện 0% | |
| 3.4 | Test nhãn phủ đủ `KpiMetricType`/`KpiSubjectType` (RB-9) | |
| 3.5 | Review tổng + cập nhật tài liệu | |

---

## Ràng buộc xuyên suốt

- **Không sửa backend.** Thiếu API thì **dừng và báo cáo**.
- Dùng lại component của #F2 (`HopThoai`, `HopXacNhan`, `ThanhPhanTrang`,
  `OTimKiem`, `thongDiepLoi`) — không dựng lại.
- Mỗi giai đoạn kết thúc: `npm test` + `tsc --noEmit` + `eslint` + `next build`,
  **và kiểm chứng bằng trình duyệt thật với ba vai**.
- Giữ nguyên hành vi #F1/#F2.

## Ước lượng

GĐ2 lớn nhất (lịch dạng lưới). GĐ3 nhỏ nhất. Nếu phải cắt, GĐ3 hoãn được — KPI
chỉ để theo dõi, không chặn gì.


---

## Kết quả

| GĐ | Commit | Kiểm chứng thật |
|---|---|---|
| Spec + plan | `e4cdf45e` | — |
| GĐ1 Đơn từ | `83d24d14` | 27/27, bốn vai |
| GĐ2 Ca làm việc | `92dedaf8` | 27/27, chạy 3 lần |
| GĐ3 KPI | (commit này) | 29/29, chạy 3 lần |

212 test xanh · `tsc` sạch · `eslint` sạch · `next build` sạch.

## Những chỗ thực tế khác với spec

Ba lần trong #F3 spec của tôi sai và chỉ lộ ra khi gọi API thật:

1. **RB-4 viết ngược.** Tôi khẳng định ca qua đêm hợp lệ và dặn UI *đừng*
   validate `end_time > start_time`, suy từ việc #3 có xử lý ca bắc qua nửa đêm.
   Backend trả 422 `INVALID_SHIFT_WINDOW`; `shift.py` ghi rõ "ca không qua nửa
   đêm ở #4". → *"module khác xử lý được X" không có nghĩa "module này chấp nhận X".*

2. **`PAST_SHIFT_DATE`** — quy tắc thứ ba của HRM không có trong spec, phát hiện
   lúc chạy. Ô ngày đã qua nay không có nút "+".

3. **RB-3 đúng nhưng thiếu một nửa.** Tôi chỉ lường trước `null`; thực tế
   `CONVERSATIONS_CLOSED` trả `"0"` thật còn `AVG_RESPONSE_MINUTES` trả `null`,
   hai chỉ số cạnh nhau trên cùng một màn. Nếu gộp lại thì "chưa có dữ liệu"
   biến thành "không làm gì".

Thêm hai điều không mâu thuẫn spec nhưng spec không biết: KPI **upsert**
(RB-10) và kỳ phải gửi **đủ cặp** năm+tháng, gửi lẻ thì bộ lọc bị bỏ qua trong
im lặng (RB-11).

## Nợ còn lại

- ~~**N4 — mỗi dòng KPI một lời gọi `/kpi-progress`.**~~ **ĐÃ TRẢ** — xem mục
  dưới.


---

## Trả nợ N4 — tiến độ KPI gom lô

### Đo trước khi sửa

Không ước lượng, đo thật trên DB dev (chỉ có **172 tin nhắn**, 20 hội thoại) với
bảng 68 dòng của Admin — con số thực tế cho một công ty 27 nhân viên × 2 chỉ số
+ 9 phòng × 2:

| | Trước | Sau |
|---|---|---|
| Lời gọi `/kpi-progress` từ trình duyệt | **68** | **0** |
| Bảng đầy đủ (trình duyệt) | 3 170 ms | **1 057 ms** |
| Phía server, 68 dòng | 2 472 ms | **172 ms** |

Song song 6 kết nối chỉ kéo 2 472 → 2 110 ms, tức nghẽn ở **server**, không phải
ở mạng: mỗi lời gọi quét lại toàn bộ `messages`/`conversations` rồi vứt đi
67/68 phần việc.

### Sửa ở đâu

Sửa **tận gốc tại port**, không vá riêng màn KPI — vì cùng một lỗi có ở hai nơi:

1. `IPerformanceSource.get_metrics_for_users()` (mới) — một `GROUP BY` thay N
   truy vấn.
2. `ListKpiProgress` + `GET /kpi-progress-batch` — FE gọi **1 lần** thay 68.
3. **#5 Analytics** (`hrm_stats_source.py:106`) có **đúng** lỗi N+1 này trong
   vòng lặp; đã sửa luôn cùng đợt.

### Giữ đúng ngữ nghĩa None-vs-0

Đây là chỗ dễ làm hỏng nhất khi gom lô, vì hai chỉ số khác nhau:

- `CONVERSATIONS_CLOSED`: người không có dòng nào **không** biến mất khỏi
  `GROUP BY` mà phải bù `Decimal(0)` — "đã đếm, bằng không".
- `AVG_RESPONSE_MINUTES`: người không có mẫu thì **vắng khoá** → `None`.

Đối chiếu máy móc: **68/68 dòng** của bản lô trùng khít bản một-dòng (giá trị
thực đạt, % hoàn thành, mục tiêu).

### Kiểm chứng

- 878 test backend xanh (+11), 212 test FE xanh, 16 hợp đồng import-linter giữ.
- Test khoá N+1 **đếm số lời gọi**: 10 dòng phải là 1 lời gọi, 2 chỉ số là 2 lời
  gọi. Quay lại vòng lặp → 2 test đỏ (đã thử).
- Integration test chạy SQL thật: trung bình **từng người** đúng (nếu `GROUP BY`
  sai thì mọi người ra cùng một số), không lẫn người ngoài danh sách.
- Phạm vi: endpoint lô **không nhận `subject_id`**, suy từ vai người gọi. Staff
  gọi chỉ nhận 2 dòng của chính mình, không có dòng cấp phòng.
- Ba kịch bản trình duyệt chạy lại: GĐ1 27/27, GĐ2 27/27, GĐ3 29/29.

### Đợt 2 — gom nốt cấp phòng

Lần đầu tôi để mục tiêu **cấp phòng** gọi lẻ, lý do ghi trong mã là "phòng thường
chỉ vài dòng, gom thêm là thêm mã cho khoản lợi không đo được". **Đo lại thì
ngược:**

| | Trước | Sau |
|---|---|---|
| 18 mục tiêu cấp phòng | **222 ms** | **62 ms** |
| Bảng hỗn hợp 68 dòng (50 nhân viên + 18 phòng) | — | **94 ms** |

222 ms cho 18 dòng còn **chậm hơn 172 ms cho 68 dòng** đã gom lô — vì 18 dòng đó
là 18 truy vấn, còn 68 dòng kia chỉ là 2. Phỏng đoán "ít dòng nên rẻ" sai vì chi
phí nằm ở **số lời gọi**, không ở số dòng.

`get_metrics_for_departments()` gom theo `conversations.department_id` — **khác
chiều** bản nhân viên (gom theo người gửi tin OUTBOUND đầu): KPI phòng tính trên
mọi hội thoại của phòng, bất kể ai trả lời. Gom nhầm chiều thì số vẫn ra, chỉ là
sai; có integration test riêng cho chiều này.

Nay cả bảng tối đa **4 truy vấn** (2 chỉ số cho 2 cấp), bất kể bao nhiêu dòng.
Đối chiếu: **0/68 dòng** lệch so với bản một-dòng.

### Nợ có sẵn — đã trả luôn

`ruff format --check` đỏ ở 3 file trên `main` (`migrations/versions/c3d4e5f6a7b8_*.py`,
`tests/integration/test_assignment_bridges.py`, `tests/unit/hrm/test_kpi_achievement.py`)
— **CI backend đã đỏ từ trước đợt #F3**, phát hiện khi trả nợ N4. Thuần trình
bày (`line-length` đổi thành 100), `git diff -w` ra đúng cùng số dòng. Tách
thành commit riêng (`f81d38d9`) để diff giữ đúng một chủ đề.
