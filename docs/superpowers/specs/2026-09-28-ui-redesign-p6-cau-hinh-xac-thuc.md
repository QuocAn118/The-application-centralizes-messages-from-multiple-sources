# Redesign — Phần 6: Cấu hình + Xác thực

Nguồn: GĐ1 §4.4 (Q1–Q4), §4.5 (L1–L3), §4.6 (lỗi dưới từng ô), yêu cầu khi duyệt
Phần 5 (màn Đăng nhập "ấn tượng hơn", xem lại chỗ đặt quản lý nhãn/mẫu). Không
đổi backend. Không thư viện mới.

## Xác thực

Khung chung `KhungXacThuc` (chia đôi, dùng cho cả L1 và L2):
- **Trái**: khối vàng `accent`, tiêu đề 52–88px/900 "Mọi tin nhắn. Một hộp thư.",
  dòng mô tả nêu đủ 4 kênh (sửa L1: bản cũ thiếu Telegram), 4 thẻ tin mẫu
  Telegram/Zalo/Instagram/Facebook (logo thật qua `IconKenh`), viền mực + bóng cứng,
  xếp lệch bằng lề + xoay ≤1,5° (tĩnh, không animation, không ảnh nền). Cột minh hoạ
  `aria-hidden` trừ tiêu đề.
- **Phải**: form trong `The`, dùng `Truong`/`ONhap`/`Nut`.

**L1 Đăng nhập**
- Lỗi: MỘT câu "Sai email hoặc mật khẩu." cho sai email, sai mật khẩu, email sai
  định dạng (`thongDiepDangNhap`, có test). Backend vốn đã trả chung
  `INVALID_CREDENTIALS`. Giữ thông điệp server cho 429 (cần biết để chờ) và
  `INACTIVE_ACCOUNT` (backend chỉ trả SAU khi mật khẩu đúng → không dùng để dò được).
  Lỗi mạng / 5xx có câu riêng. Sau lỗi: xoá ô mật khẩu, focus lại ô đó.
- Caps Lock: đọc `getModifierState("CapsLock")` từ sự kiện phím trong form, cảnh
  báo trong vùng `aria-live`.
- Nhớ email: ô "Nhớ email trên máy này" (mặc định bật), lưu **chỉ email** vào
  localStorage sau khi đăng nhập thành công; đọc bằng `useSyncExternalStore` (trang
  prerender — không lệch hydrate); có email cũ thì focus ô mật khẩu. Try/catch mọi
  truy cập storage.
- Đang đăng nhập: `Nut dangChay` (vòng quay, `aria-busy`, chặn click) + `useRef`
  chặn Enter lặp giữa hai lần render → một yêu cầu duy nhất.
- Nút Đăng nhập luôn vàng (không `disabled` khi ô trống — ô `required`, trình duyệt
  tự báo).
- "Quên mật khẩu?" (`aria-expanded`) → "Liên hệ quản trị viên để được cấp lại mật
  khẩu tạm…". Không có luồng tự đặt lại (tài khoản do Admin cấp).

**L2 Đổi mật khẩu**: cùng khung. Danh sách 4 điều kiện tick dần khi gõ
(`dieuKienMatKhau`, đúng `kiem_tra_do_manh`: ≥ 8 ký tự theo code point, có chữ
cái Unicode, có chữ số; + khớp ô nhập lại). Mỗi dòng có chữ ẩn "đã đạt / chưa đạt"
(không chỉ dựa vào màu). Nút mở khi đủ điều kiện; server vẫn là trọng tài.

**L3** (Staff vào khu cấm): đã làm theo mẫu `TrangThaiLoi` ở Phần 1 — giữ.

## Cấu hình (`/quan-tri/*`, route giữ nguyên — X11)

- Mọi màn: `DauTrang` + mô tả + nút chính vàng, `Bang/Th/Td/Tr`, 3 trạng thái
  `TrangThaiTai/Rong/Loi`, bộ lọc `OChon/ONhap`.
- **Q1 Người dùng**: menu "⋯" chuyển sang `MenuHanhDong` (Radix) — bỏ menu tự viết.
  Avatar vuông, huy hiệu vai (`HuyHieu lop=`), dòng đã vô hiệu hoá nền lõm (bỏ
  `opacity-60` — trượt tương phản).
- **Q2 Phòng ban, Kênh**: mặc định chỉ mục đang hoạt động; nút bật "Hiện cả phòng
  đã ngừng (n)" / "Hiện cả kênh đã ngắt (n)" (`aria-pressed`, nhãn cố định). Chỉ
  hiện nút khi n > 0. Trạng thái phòng "Đã ngừng hoạt động" (thống nhất RB-5; trước
  ghi nhầm "Đã vô hiệu hoá").
- **Q3 Kênh / Phòng ban**: Sửa + Ngắt kênh / Ngừng hoạt động vào menu "⋯" (mục huỷ
  hoại tự xuống cuối, chữ đỏ), vẫn qua hộp xác nhận. Nền tảng: logo + tên.
- **Q4 Nhật ký**: cột Đối tượng tra tên qua `/users` (100) + `/departments`, loại đối
  tượng dịch tiếng Việt, UUID vào tooltip (`GoiY`, focus được). Không tra được →
  `#8 ký tự đầu`.
- **Hộp thoại (§4.6)**: ô nhập qua `Truong` (nhãn trên, gợi ý/lỗi dưới, ARIA nối
  sẵn). `loiTheoTruong` (có test) đặt lỗi server dưới đúng ô: theo `code`
  (`EMAIL_ALREADY_EXISTS` → Email, `WEAK_PASSWORD` → Mật khẩu,
  `CHANNEL_ALREADY_CONNECTED` → Mã kênh…) hoặc theo `loc` của 422. Không khớp → dòng
  lỗi chung. Lỗi dưới ô có `role="alert"` (xuất hiện sau khi bấm Lưu). Khối "mật
  khẩu chỉ hiện một lần" gom thành `MatKhauMotLan`. Thứ tự ô giữ nguyên.

## Chỗ đặt quản lý nhãn / mẫu trả lời (xem lại quyết định 2b)

Spec 2b đặt ở hộp thoại trong Hộp thư vì cho rằng "khu Cấu hình chỉ Admin vào
được" — **tiền đề này sai**: `vaoDuocKhuQuanTri` cho cả Manager (Manager có tab
Người dùng). Nay:
- thêm tab **Nhãn** (`/quan-tri/nhan`) và **Mẫu trả lời** (`/quan-tri/mau-tra-loi`)
  cho Manager + Admin — chỗ chính, tìm được từ nav;
- hộp thoại trong Hộp thư **giữ** làm lối tắt (quản lý giữa lúc đang trả lời, không
  rời hội thoại). Cả hai dùng CÙNG component (`KhungQuanLy` chọn trang/hộp) — không
  nhân bản logic.

## Kịch bản

- Mới `ui-p6.mjs` (1440 + 1280).
- `ui-f2-gd2`, `ui-f2-gd3` cập nhật vì đổi UI có chủ đích (ghi trong file): mở
  menu "⋯" rồi chọn mục thay vì bấm nút trên dòng; bật "Hiện cả…" trước khi kiểm
  dòng vừa ngừng/ngắt (+ kiểm mới: dòng ẩn mặc định, nút có `aria-pressed`);
  chữ "Đã vô hiệu hoá" → "Đã ngừng hoạt động" cho phòng. Điều kiện kiểm giữ nguyên.

## Ngoài phạm vi (ghi lại)

- Ô nhập trong 5 hộp thoại khu Nhân sự (Phần 3) vẫn dùng lớp cũ (đã ánh xạ sang
  token mới nên màu đúng, nhưng viền 1px, bo `lg`). Đề nghị gom vào lần dọn sau.
