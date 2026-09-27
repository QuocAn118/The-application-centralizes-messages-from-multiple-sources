# Redesign — Phần 4: Từ khoá + Phân tích AI

Nguồn: GĐ1 §4.1 (T1–T3), §4.2 (A1–A2), X7 (một mẫu đầu trang), X9 (3 trạng
thái), X12 (mốc tương đối). **Không đổi backend.**

## Từ khoá (`/tu-khoa/danh-sach`)

- Đầu trang: tiêu đề + mô tả + ô tìm + nút chính "Thêm từ khoá" (vẫn giữ: là
  đường duy nhất thêm vào phòng chưa hiện thẻ, và Admin chọn phòng trong hộp).
- **T1:** mỗi phòng một thẻ, từ khoá là **chip**; cuối dãy có ô thêm nhanh (gõ +
  Enter), giữ focus để gõ tiếp. Phòng người xem thêm được thì **luôn có thẻ**,
  kể cả khi rỗng (không thì không có chỗ thêm nhanh). Đang tìm thì ẩn ô thêm và
  ẩn thẻ rỗng.
- **T2:** "dạng khớp" không hiện thường trực; chỉ ở `title` của chip và trong
  hộp sửa. Ô thêm nhanh báo trùng = thông điệp **server** + câu giải thích bỏ
  dấu/hoa thường, nối với ô bằng `aria-describedby`.
  - **Lệch GĐ1:** GĐ1 muốn lỗi trùng chỉ ra *dạng khớp*. Lỗi 409
    `KEYWORD_DUPLICATE` không trả dạng chuẩn hoá hay từ khoá bị trùng, và RB-3
    cấm FE tự bỏ dấu để đoán. Muốn chỉ đúng chip bị trùng cần backend thêm
    `details` vào 409 — chưa làm, chờ duyệt.
- **T3:** bấm chip → hộp sửa (tên truy cập "Sửa <từ>"); nút × (tên "Xoá <từ>")
  → hộp xác nhận. Staff: chip là chữ thường, không nút nào.

## Phân tích AI (`/tu-khoa/phan-tich`)

- DauTrang + Bang + HuyHieu (Đã tự phân = ok, Chưa rõ phòng = wait, Không phân
  tích được = trung — không đỏ, vì thường chỉ là thiếu tin nhắn).
- **A1:** cột "Hội thoại" có link "Mở hội thoại" → `/inbox/<conversation_id>`.
  Quyền xem do Hộp thư kiểm.
- **A2 (một phần):** dòng AMBIGUOUS/NOT_ANALYZED tô nền vàng nhạt + dòng đếm
  "n kết quả trên trang này … cần người quyết".
  - **Lệch GĐ1:** GĐ1 muốn **bộ lọc** "Cần xem lại". `GET /analyses` không có
    tham số `outcome` và danh sách phân trang (25/trang) — lọc tại client chỉ lọc
    được trang đang xem, sẽ báo sai. Đề xuất BE-10: `GET /analyses?outcome=…`
    (lặp được), chờ duyệt.
  - Ghi nhận: phạm vi Manager/Staff lọc theo `suggested_department_id`, mà hai
    loại "cần xem lại" luôn có phòng `null` → **chỉ Admin thấy** chúng.

## Kiểm chứng

- Kịch bản mới `ui-p4.mjs` (scratchpad): 3 vai, 1440 và 1280.
- `ui-f4-gd1/gd2/no` cập nhật selector vì đổi UI có chủ đích (không còn một
  `<section>` chung; Sửa/Xoá theo tên truy cập; dạng khớp kiểm ở tooltip). Kiểm
  "dạng khớp có hiện" đổi thành "dạng khớp ở tooltip + KHÔNG hiện thường trực".

## Cập nhật sau duyệt (2026-09-27) — hai lệch GĐ1 đã đóng

- **BE-10** (`GET /analyses?outcome=` lặp được): nút lọc **Tất cả / Cần xem lại (n)**
  lọc ở server trên toàn bộ dữ liệu; `n` = `total` của truy vấn `limit=1`.
  Kèm đổi phạm vi: Manager thấy đề xuất về phòng mình **cộng** mọi hội thoại HIỆN
  đang chờ phân (nhất quán quy tắc "phân tích lại"); Staff giữ như cũ.
- **409 `KEYWORD_DUPLICATE`** trả `error.details.existing_keyword {id, text,
  normalized}`: ô thêm nhanh tô đỏ đúng chip đang có + "Trùng với “…”"; hộp thoại
  nêu tên. FE vẫn không tự bỏ dấu (RB-3).
