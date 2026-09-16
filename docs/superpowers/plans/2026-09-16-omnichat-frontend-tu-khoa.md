# Plan #F4 — Frontend Từ khoá & Phân tích AI

**Spec:** [2026-09-16-omnichat-frontend-tu-khoa-design.md](../specs/2026-09-16-omnichat-frontend-tu-khoa-design.md)
**Nhánh:** `feat/fe-tu-khoa`

Hai giai đoạn — nhỏ hơn #F3 (2 màn, một màn chỉ đọc). Spec đã soạn **sau khi dò
API thật**, nên giai đoạn này không có bước "đoán rồi sửa" như #F3.

---

## Giai đoạn 1 — Màn Từ khoá

| # | Việc | Xong khi |
|---|---|---|
| 1.1 | Type + `lib/tu-khoa-api.ts`; mở tab "Từ khoá" cho **mọi vai** ở `tab-quan-tri` | `tsc` sạch, khớp schema thật |
| 1.2 | Danh sách từ khoá, nhóm theo phòng, hiện cả `normalized` (RB-3) | Ba vai thấy đúng phạm vi |
| 1.3 | Tạo / sửa / xoá (RB-4: `DELETE` trả 204 → `Promise<void>`) | Staff không thấy nút nào |
| 1.4 | Trùng: hiện thẳng thông điệp server, FE **không** tự đoán (RB-3) | Gõ khác dấu vẫn báo trùng |
| 1.5 | Test: `datLaiKieuTraVe` 204, nhãn phủ đủ enum | `npm test` xanh |

### Kiểm chứng GĐ1

Manager tạo "Bảo Hành" → gõ "bao hanh" phải báo trùng. Staff vào được màn, không
có nút Thêm/Sửa/Xoá. Manager không thấy từ khoá phòng khác.

---

## Giai đoạn 2 — Màn Phân tích AI + review tổng

| # | Việc | Xong khi |
|---|---|---|
| 2.1 | Danh sách phân tích + phân trang (`limit` trần 100) | |
| 2.2 | Ba `outcome` với ba hình dạng `null` khác nhau (RB-7) | Cả ba nhánh hiện đúng trên dữ liệu thật |
| 2.3 | `confidence` → phần trăm; `null` ra dấu gạch, **không** ra `0%` (RB-8) | |
| 2.4 | Test nhãn phủ đủ `AnalysisOutcome` (RB-9) | |
| 2.5 | Review tổng + cập nhật tài liệu | |

### Kiểm chứng GĐ2

Đã gieo sẵn một `AMBIGUOUS` và một `NOT_ANALYZED` trong DB dev (`gieo_analysis_f4.py`)
vì LLM thật hầu như luôn trả `AUTO_ASSIGNED` — không có hai bản ghi đó thì hai
nhánh `null` không thể kiểm bằng trình duyệt.

---

## Ràng buộc xuyên suốt

- **Không sửa backend.** Thiếu API thì dừng và báo cáo.
- Dùng lại component #F2/#F3 — không dựng lại.
- Mỗi giai đoạn kết thúc: `npm test` + `tsc` + `eslint` + `next build`, **và
  kiểm chứng trình duyệt thật với ba vai**.
- Giữ nguyên hành vi #F1/#F2/#F3.

## Cố ý KHÔNG làm

**Nút "Phân tích lại"** (`POST /conversations/{id}/analyses`) — xem RB-10. Thuộc
về màn Hộp thư hơn, và endpoint có nợ phạm vi đã biết (chỉ kiểm vai, không kiểm
phòng). Ghi thành **N5**.
