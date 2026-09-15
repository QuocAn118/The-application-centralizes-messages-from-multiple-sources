# Plan #F2 — Frontend Quản trị

**Spec:** [2026-09-15-omnichat-frontend-quan-tri-design.md](../specs/2026-09-15-omnichat-frontend-quan-tri-design.md)
**Nhánh:** `feat/fe-quan-tri`

Bốn giai đoạn, mỗi giai đoạn tự đứng được và kết thúc bằng một commit chạy được.
Review cuối mỗi giai đoạn trước khi sang giai đoạn sau — như #F1.

---

## Giai đoạn 1 — Nền chung + màn Người dùng

Màn khó nhất (9 endpoint, mỗi hành động một quy tắc quyền) nên làm trước khi
còn nhiều thời gian, và nền dựng ở đây sẽ dùng lại cho ba màn sau.

### Task

| # | Việc | Xong khi |
|---|---|---|
| 1.1 | Type + hàm API cho users/departments trong `types.ts`, `lib/quan-tri-api.ts` | `tsc` sạch, khớp schema backend |
| 1.2 | Khung `/quan-tri` + mở khoá mục Cấu hình ở `nav-rail`, chặn theo vai | STAFF gõ URL bị chặn |
| 1.3 | Component dùng chung: bảng có phân trang, hộp xác nhận, ô tìm kiếm (dùng `use-debounce` sẵn có) | Dùng lại được ở GĐ2–4 |
| 1.4 | Danh sách người dùng + bộ lọc (ẩn bộ lọc phòng với Manager — RB-2) | Manager không thấy bộ lọc phòng |
| 1.5 | Tạo tài khoản + hiện mật khẩu tạm một lần (RB-3) | Không lưu vào localStorage/URL |
| 1.6 | Sửa hồ sơ · đổi vai trò · đổi phòng | Nút ẩn đúng theo `can_manage` |
| 1.7 | Vô hiệu hoá / kích hoạt lại · đặt lại mật khẩu | Lỗi admin-cuối hiện rõ (RB-4) |
| 1.8 | Test: quyền hiển thị nút, lỗi nghiệp vụ, bảng nhãn phủ đủ enum (RB-9) | `npm test` xanh |

### Kiểm chứng GĐ1 (không chỉ chạy test)

Đăng nhập thật bằng ba vai, làm đủ vòng: tạo phòng → tạo nhân viên → nhân viên
đăng nhập bằng mật khẩu tạm → bị buộc đổi. Ghi lại kết quả.

---

## Giai đoạn 2 — Màn Phòng ban

| # | Việc | Xong khi |
|---|---|---|
| 2.1 | Danh sách + số nhân viên mỗi phòng (đọc `total`, không tải hết) | Không gọi thừa |
| 2.2 | Tạo · sửa tên/mô tả | Trùng tên hiện lỗi rõ |
| 2.3 | Ngừng hoạt động — nhãn "Ngừng hoạt động", không phải "Xoá" (RB-5) | Hộp xác nhận nói rõ dữ liệu còn |
| 2.4 | Test | Xanh |

---

## Giai đoạn 3 — Màn Kênh

Giai đoạn nhạy cảm nhất vì chạm token thật.

| # | Việc | Xong khi |
|---|---|---|
| 3.1 | Danh sách kênh (4 nền tảng, gồm TELEGRAM) | Badge đúng cho cả 4 |
| 3.2 | Kết nối kênh — credential `type="password"` (RB-6) | Token không lọt vào bảng/log/thông báo lỗi |
| 3.3 | Sửa kênh — để trống credential = giữ nguyên | Gửi đúng `null` khi để trống |
| 3.4 | Gỡ phòng bằng `clear_department: true` (RB-7) | Gỡ có hiệu lực thật |
| 3.5 | Ngắt kênh | Hội thoại cũ vẫn xem được |
| 3.6 | Test, gồm một test khẳng định credential không xuất hiện trong DOM | Xanh |

---

## Giai đoạn 4 — Màn Nhật ký + review tổng

| # | Việc | Xong khi |
|---|---|---|
| 4.1 | Bảng nhật ký + phân trang | |
| 4.2 | Bộ lọc: hành động, loại tài nguyên, người thực hiện, khoảng thời gian | |
| 4.3 | Nhãn tiếng Việt cho 15 `AuditAction`, nhóm theo tiền tố | Test phủ đủ 15 giá trị (RB-9) |
| 4.4 | Review tổng: quyền, i18n, không chuỗi cứng, không `fetch` rải rác | |
| 4.5 | Cập nhật roadmap + tài liệu vận hành | |

---

## Ràng buộc xuyên suốt

- **Không sửa backend.** Nếu thấy thiếu API, **dừng và báo cáo** thay vì tự thêm
  — F2 là sub-project frontend.
- Mọi lệnh gọi qua `api-client.ts`; type khai ở `types.ts`; nhãn qua `i18n.ts`.
- Mỗi giai đoạn kết thúc: `npm test` + `tsc --noEmit` + `eslint` + `next build`.
- Giữ nguyên hành vi #F1 — không sửa màn inbox.

## Ước lượng

GĐ1 lớn hơn ba giai đoạn còn lại cộng lại. Nếu phải cắt bớt, GĐ4 (Nhật ký) là
phần hoãn được — nó chỉ để tra cứu, không chặn sub-project nào khác.
