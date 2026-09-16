# Plan #F4 — Frontend Từ khoá & Phân tích AI

**Spec:** [2026-09-16-omnichat-frontend-tu-khoa-design.md](../specs/2026-09-16-omnichat-frontend-tu-khoa-design.md)
**Nhánh:** `feat/fe-tu-khoa`

Hai giai đoạn — nhỏ hơn #F3 (2 màn, một màn chỉ đọc). Spec đã soạn **sau khi dò
API thật**, nên giai đoạn này không có bước "đoán rồi sửa" như #F3.

---

## Giai đoạn 1 — Màn Từ khoá

| # | Việc | Xong khi |
|---|---|---|
| 1.1 | Type + `lib/tu-khoa-api.ts`; thêm tab "Từ khoá" (`riengAdmin: false`) ở `tab-quan-tri` | `tsc` sạch, khớp schema thật |
| 1.2 | Danh sách từ khoá, nhóm theo phòng, hiện cả `normalized` (RB-3) | Manager thấy phòng mình, Admin thấy tất cả |
| 1.3 | Tạo / sửa / xoá (RB-4: `DELETE` trả 204 → `Promise<void>`) | Manager chỉ sửa được phòng mình |
| 1.4 | Trùng: hiện thẳng thông điệp server, FE **không** tự đoán (RB-3) | Gõ khác dấu vẫn báo trùng |
| 1.5 | Test: `datLaiKieuTraVe` 204, nhãn phủ đủ enum | `npm test` xanh |

### Kiểm chứng GĐ1

Manager tạo "Bảo Hành" → gõ "bao hanh" phải báo trùng. Manager không thấy từ
khoá phòng khác. Staff bị chặn ở cửa khu Cấu hình (như bốn màn #F2) — **quyết
định của UI, không phải giới hạn backend**; xem §1 của spec.

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
  kiểm chứng trình duyệt thật (Manager, Admin, và Staff bị chặn đúng cách)**.
- Giữ nguyên hành vi #F1/#F2/#F3.

## Cố ý KHÔNG làm

**Nút "Phân tích lại"** (`POST /conversations/{id}/analyses`) — xem RB-10. Thuộc
về màn Hộp thư hơn, và endpoint có nợ phạm vi đã biết (chỉ kiểm vai, không kiểm
phòng). Ghi thành **N5**.

**Mở hai màn cho Staff.** Backend cho phép (200), UI cố ý không — vì cổng
`ChanTheoVai` của khu Cấu hình đang bảo vệ bốn màn #F2. Ghi thành **N6**; khi
nào cần thì tách khu riêng như `/nhan-su`, đừng nới cổng cũ.


---

## Kết quả

| GĐ | Commit | Kiểm chứng thật |
|---|---|---|
| Spec + plan | `a12f4ab9` | 15 phép thử API trước khi viết |
| GĐ1 Từ khoá | `4a1f4409` | 28/28, chạy 3 lần |
| GĐ2 Phân tích AI | (commit này) | 23/23, chạy 3 lần |

229 test FE xanh · `tsc`/`eslint`/`next build` sạch.
Hồi quy: #F3 GĐ1 27/27 · GĐ2 27/27 · GĐ3 29/29 · #F2 GĐ4 33/33.

## Cách làm khác #F3 — và có hiệu quả

Spec soạn **sau** 15 phép thử API. Kết quả: **không có lần nào spec sai** trong
suốt #F4, so với **ba lần** ở #F3 (RB-4 viết ngược, `PAST_SHIFT_DATE` bỏ sót,
RB-3 thiếu một nửa). Chi phí là ~15 phút dò trước; cái tiết kiệm được là ba vòng
viết-sai-rồi-sửa cộng với ba lần sửa tài liệu.

Điều đáng giá nhất không phải là xác nhận những gì đã đoán đúng, mà là **hai thứ
không đoán ra**:

1. Staff **xem được** cả hai màn (200, không phải 403) — trái với trực giác từ
   khu quản trị #F2. Biết sớm nên đưa được thành một quyết định có ý thức (§1
   của spec) thay vì phát hiện muộn rồi chữa cháy.
2. Ba `outcome` có **ba hình dạng `null` khác nhau**, mà dữ liệu thật chỉ có một
   nhánh. Nếu viết UI rồi mới xem, tôi sẽ chỉ kiểm được nhánh `AUTO_ASSIGNED` và
   hai nhánh kia hỏng âm thầm trên production.

## Nợ ghi nhận

- **N5** — nút "Phân tích lại" (`POST /conversations/{id}/analyses`): endpoint có
  nợ phạm vi đã biết (chỉ kiểm vai, không kiểm phòng của hội thoại). Thuộc màn
  Hộp thư hơn. Xem RB-10.
- **N6** — mở hai màn cho Staff: backend cho phép (200) nhưng UI cố ý hẹp hơn vì
  cổng `ChanTheoVai` đang bảo vệ bốn màn #F2. Khi cần thì **tách khu riêng** như
  `/nhan-su` của #F3, đừng nới cổng cũ.

## Dữ liệu gieo sẵn trong DB dev

`gieo_analysis_f4.py` chèn một `AMBIGUOUS` và một `NOT_ANALYZED` — LLM thật hầu
như luôn trả `AUTO_ASSIGNED` nên không có hai bản ghi này thì hai nhánh `null`
không kiểm được bằng trình duyệt. Giữ lại làm dữ liệu mẫu.
