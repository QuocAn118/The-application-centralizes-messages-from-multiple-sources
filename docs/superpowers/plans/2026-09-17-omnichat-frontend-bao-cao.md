# Plan #F5 — Frontend Báo cáo (Analytics)

**Spec:** [2026-09-17-omnichat-frontend-bao-cao-design.md](../specs/2026-09-17-omnichat-frontend-bao-cao-design.md)
**Nhánh:** `feat/fe-bao-cao`

Sub-project **cuối** roadmap FE. 4 báo cáo đọc-chỉ, một khung dùng chung. Spec
soạn sau khi dò API thật → không có bước "đoán rồi sửa".

---

## Giai đoạn 1 — Nền + màn Hội thoại

| # | Việc | Xong khi |
|---|---|---|
| 1.1 | 4 kiểu `*ReportItem` (types) + `lib/bao-cao-api.ts` (4 GET, khoá cache theo khoảng+phòng) | `tsc` sạch, khớp schema thật |
| 1.2 | `quyen-bao-cao.ts` + test; `khoangThoiGian`, `tenNguoi`, `tenPhong` ở `hien-thi.ts` + test | map thiếu id → mã rút gọn; dept null → "Chưa phân phòng" |
| 1.3 | Layout `/bao-cao` (AuthGuard + **ChanTheoVai** + `TabBaoCao`); nav-rail: placeholder → link (chỉ Mgr/Admin) | Staff bị chặn ở cửa, không thấy mục nav |
| 1.4 | `KhungBaoCao`: chọn ngày (native `input[type=date]`, mặc định 30 ngày) + ô chọn phòng (chỉ Admin, RB-1) | Manager KHÔNG có ô chọn phòng |
| 1.5 | Màn Hội thoại: bảng (phòng, kênh) + badge kênh; `department_id=null` → "Chưa phân phòng" | Admin thấy dòng dept-null thật |

### Kiểm chứng GĐ1
Admin vào được, chọn ngày/phòng thấy dữ liệu đổi. Manager vào được, không có ô
chọn phòng, chỉ thấy phòng mình. Staff bị `ChanTheoVai` chặn + không thấy nav
"Báo cáo". `from>to` chặn ở FE.

---

## Giai đoạn 2 — Ba màn còn lại + review

| # | Việc | Xong khi |
|---|---|---|
| 2.1 | Màn Nhân viên: tên qua `tenNguoi`, id ngoài phòng → mã rút gọn; `avg_*=null` → dash (không 0) | Manager thấy id không tra được hiện mã rút gọn |
| 2.2 | Màn Ca & KPI: %KPI ba hình dạng (null→dash, 0.0→"0%", >0→%); hiện `period` | Cả ba nhánh đúng trên dữ liệu thật |
| 2.3 | Màn Đơn từ: badge loại/trạng thái (#F3); `avg_decision_seconds=null` → dash | |
| 2.4 | Tổng cộng chân bảng, trạng thái rỗng/lỗi, sắp xếp mặc định | `[]` → "Không có dữ liệu" |
| 2.5 | Review tổng + cập nhật tài liệu + memory | mọi cổng xanh |

### Kiểm chứng GĐ2
Đối chiếu số bảng với lời gọi API thật. %KPI: staffA (mgrA) hiện "0%" + kỳ
"2026-09"; nhân viên không có target hiện dash. Bảng agents của Manager: dòng
Admin (dept=null) hiện mã rút gọn, không "undefined".

---

## Ràng buộc xuyên suốt
- **Không sửa backend.** Thiếu API thì dừng và báo cáo.
- Dùng lại `ChanTheoVai`, `ThanhPhanTrang`?(không cần — mảng trần), badge #F2/#F3,
  `NHAN_KENH`/`NHAN_TRANG_THAI_DON`, `DAU_GACH`. Không dựng lại.
- Mỗi GĐ kết thúc: `npm test` + `tsc` + `eslint` + `next build` + kiểm chứng
  trình duyệt thật (Admin, Manager, Staff-bị-chặn).
- Giữ nguyên hành vi #F1–#F4.

## Cố ý KHÔNG làm
- **`POST /rollups/rebuild`** — công cụ vận hành, không phải màn người dùng.
- **Biểu đồ** — bảng số trước; chart là lib mới, để sau nếu user cần (YAGNI).
- **Xuất CSV/Excel** — không có yêu cầu; thêm khi cần.
