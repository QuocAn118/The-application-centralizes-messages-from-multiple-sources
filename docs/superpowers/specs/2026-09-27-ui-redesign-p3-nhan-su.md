# Redesign — Phần 3: Lịch phân ca + Đơn từ + KPI

Nguồn: GĐ1 §3 (S1–S7, D1–D3, K1–K3), X7 (một mẫu đầu trang), X4 (bảng tối đa
~1440px), X5 (menu "⋯"), X9 (3 trạng thái), X12 (mốc tương đối), X14 (huy hiệu
"Nhân sự"). **Không đổi backend.**

## Ca làm việc (`/nhan-su/ca-lam-viec`)

- Đầu trang "Ca làm việc" + nút chính "Phân ca…" không có (xếp bằng ô lưới).
  Nút phụ chuyển chế độ xem: **Lịch tuần** (mặc định) · **Mẫu ca** (S1). Chế độ
  xem là 2 nút bật/tắt (`aria-pressed`), không phải route mới.
- Lịch dùng hết bề ngang. Điều hướng tuần: ‹ · Tuần này · › + khoảng ngày.
- Cột hôm nay: viền dày + nền vàng nhạt + nhãn "Hôm nay" (S5).
- Ngày đã qua: nền sọc xám + nhãn "Đã qua"; ca đã phân vẫn hiện (S2); không
  có nút thêm (backend trả `PAST_SHIFT_DATE`).
- Ô trống cả ô là vùng bấm; "+" rõ khi rê/focus (S3).
- Khối ca: dải màu trái theo mẫu ca (`mauTuId(shift_id)`, bảng 8 màu) + chú
  giải màu dưới lưới (S4). Huỷ ca = nút icon ✕ nhỏ trên khối (có xác nhận).
- Mẫu ca: bảng + huy hiệu trạng thái (S6) + menu "⋯" Sửa / Ngừng dùng (S7).

## Đơn từ (`/nhan-su/don-tu`)

- Bộ lọc thành hàng nút có số đếm: **Chờ duyệt (n)** · Đã duyệt · Từ chối ·
  Đã thu hồi · Tất cả. Manager/Admin mặc định "Chờ duyệt", Staff mặc định
  "Tất cả" (D1).
  - GĐ1 đề nghị tab "Đã quyết" gộp 3 trạng thái, nhưng `GET /requests` chỉ nhận
    **một** `status` — gộp phải đổi backend. Tách từng trạng thái đạt cùng mục
    đích (đơn chờ không lẫn đơn đã quyết) mà không đụng backend.
- Admin: câu "Quản trị viên không thuộc phòng ban nào…" đặt đúng chỗ nút "Gửi
  đơn" (D2).
- "Lý do từ chối:" dòng riêng có nhãn (D3). Mốc gửi tương đối, đầy đủ trong
  `title` (X12). Thao tác: Duyệt là nút chính nhỏ; Từ chối / Thu hồi trong "⋯".
- **Huy hiệu "Nhân sự" trên nav rail (X14):** số đơn CHỜ DUYỆT mà người xem
  duyệt được. Chỉ Manager/Admin. Đếm = đơn `CHO_DUYET` trong phạm vi trừ đơn
  của chính mình (backend chỉ cho 1 Manager/phòng nên Manager không bao giờ
  thấy đơn Manager khác trong phạm vi). Lấy tối đa 100, quá thì "99+".

## KPI (`/nhan-su/kpi`)

- Chọn kỳ: ‹ Tháng 9/2026 › (K3). Vẫn luôn gửi đủ cặp năm+tháng.
- Cột "Hoàn thành": thanh tiến độ + số; `null` hiện "—" và **không** vẽ thanh
  (null ≠ 0%) (K1). Thanh tối đa 100% chiều rộng, số vẫn in đúng (vd. 130%).
- "Sửa mục tiêu" vào menu "⋯" (K2).

## Kiểm chứng

- Kịch bản mới `ui-p3.mjs` (scratchpad) cho 3 màn × 3 vai.
- Kịch bản cũ `ui-f3-gd1/2/3` hỏng vì đổi UI có chủ đích → cập nhật selector,
  ghi lý do; không nới điều kiện kiểm.
