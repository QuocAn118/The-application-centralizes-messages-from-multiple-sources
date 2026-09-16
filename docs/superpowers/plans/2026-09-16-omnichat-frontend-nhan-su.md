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
| 2.1 | Danh sách mẫu ca + tạo/sửa/ngừng (RB-4: ca qua đêm hợp lệ) | Tạo được ca 22:00–06:00 |
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
