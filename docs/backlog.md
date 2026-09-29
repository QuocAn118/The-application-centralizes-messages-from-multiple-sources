# Backlog kỹ thuật

Việc đã biết, chưa làm. Mỗi mục: vấn đề, hiện trạng tạm, phương án.

## WS-1. Xác thực WebSocket bằng vé dùng một lần

- **Vấn đề:** `/ws/inbox?token=<access_token>` đặt access token (sống 15 phút,
  dùng được cho mọi API) lên query string. URL hay bị ghi lại: log truy cập của
  server, proxy/CDN phía trước, lịch sử công cụ gỡ lỗi.
- **Tạm thời (2026-09-27, nhánh `fix/an-toan-du-lieu`):** bộ lọc log che
  `token=***` trên logger `uvicorn.access` / `uvicorn.error`
  (`backend/src/shared/infrastructure/logging.py`). Chỉ che log của chính API;
  proxy đứng trước (cloudflared, nginx) vẫn thấy URL đầy đủ.
- **Phương án dài hạn:**
  1. `POST /api/v1/ws-ticket` (cần Bearer) trả một vé ngẫu nhiên, sống ~30 giây,
     gắn `user_id`; lưu băm của vé (DB hoặc bộ nhớ nếu chỉ một tiến trình).
  2. Client mở `/ws/inbox?ticket=<vé>`; server đổi vé → người dùng rồi **xoá vé
     ngay** (dùng một lần). Vé lọt log cũng vô dụng vì đã tiêu và đã hết hạn.
  3. Bỏ hẳn `?token=` sau khi frontend chuyển xong.
- **Chi phí:** 1 endpoint + 1 bảng/khoá nhỏ + đổi `cau-noi-realtime.tsx` lấy vé
  trước mỗi lần (tái) kết nối.

## KH-1. Nhận diện khách xuyên kênh

- **Vấn đề:** `customers.channel_id` — cùng một người nhắn qua Zalo và Facebook
  là HAI khách. Lịch sử (BE-4), ghi chú (BE-5) và nhãn (BE-6) vì thế bị tách theo kênh.
- **Hiện trạng:** panel không nói rõ lịch sử chỉ trong cùng kênh — người dùng có
  thể tưởng khách chưa từng nhắn kênh khác.
- **Phương án:** bảng `contacts` (người thật) + `customers.contact_id`; ghép tay
  (Manager chọn "cùng một người") trước, gợi ý tự động sau. Ghi chú/nhãn chuyển
  sang gắn theo `contact_id`. Cần migration dữ liệu — làm spec riêng.

## NH-1. Giao diện đổi tên / đổi màu nhãn

- **Vấn đề:** `PATCH /tags/{id}` đã nhận `name` và `color`; FE có sẵn `suaNhan`, nhưng
  hộp quản lý nhãn chỉ có tạo và ngừng/bật lại.
- **Phương án:** nút Sửa trên từng dòng → form cùng kiểu với form tạo (tên +
  bảng màu). Không cần backend.

## KH-2. Nhập tay thông tin liên hệ khách

- **Vấn đề:** nền tảng không gửi SĐT/email. **Hoãn** theo GĐ1 §10.1 #4 — chưa rõ
  ai dùng. Panel khách không hiện ô trống cho trường chưa làm.
- **Phương án khi làm:** cột `phone`, `email` (nullable) ở `customers` (hoặc
  `contacts` nếu KH-1 làm trước), sửa qua `PATCH /customers/{id}`, có nhật ký.

## HT-1. Ngưỡng "Chờ N phút" là hằng số

- **Hiện trạng:** `NGUONG_CHO_PHUT = 15` ở `frontend/src/lib/hop-thu.ts`, dùng chung
  mọi phòng.
- **Phương án:** cột `waiting_threshold_minutes` ở `departments` (mặc định 15),
  trả kèm `GET /departments`; FE đọc theo phòng của hội thoại.
