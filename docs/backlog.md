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
