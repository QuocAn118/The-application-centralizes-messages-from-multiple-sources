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

- **N4 — mỗi dòng KPI một lời gọi `/kpi-progress`.** Không có API lấy hàng
  loạt, nên bảng N dòng tốn N lời gọi. Hiện tại mỗi phòng vài chục mục tiêu nên
  chấp nhận được; nếu bảng phình to thì cần backend cho phép truy vấn theo lô.
