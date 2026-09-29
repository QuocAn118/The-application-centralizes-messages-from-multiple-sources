# OmniChat

**Hộp thư đa kênh cho đội chăm sóc khách hàng.** OmniChat gom tin nhắn của khách từ nhiều nền tảng (Telegram, Zalo, Facebook, Instagram) về một hộp thư chung, tự phân hội thoại về đúng phòng ban nhờ từ khoá và AI, đồng thời quản lý ca làm, KPI và báo cáo hiệu suất của nhân viên.

<img width="1280" height="800" alt="image" src="https://github.com/user-attachments/assets/29f29390-f12b-4025-986c-a0a8cc4b382e" />



---

## Tính năng chính

### Hộp thư
- Gom hội thoại từ mọi kênh vào một danh sách, lọc theo **Của tôi / Chưa ai nhận / Tất cả** và theo trạng thái.
- **Chưa đọc tính riêng cho từng người**, có huy hiệu số trên thanh điều hướng.
- Hiện **thời gian khách đang chờ** ("Chờ 12 phút"), chuyển màu cảnh báo khi quá 15 phút.
- **Nhận việc, giao, đổi, gỡ người phụ trách** (Manager/Admin), có dòng hệ thống trong khung chat và thông báo realtime.
- **Mẫu trả lời nhanh:** gõ `/` trong ô soạn để chọn mẫu.
- **Panel thông tin khách:** lịch sử hội thoại, nhãn dùng chung, ghi chú nội bộ (chỉ phòng của người viết thấy).
- Cập nhật realtime qua WebSocket.

### Tự động phân phòng
- Mỗi phòng ban có bộ **từ khoá** riêng, so khớp không phân biệt dấu và hoa thường.
- **AI phân tích nhu cầu khách** để đề xuất phòng phù hợp. Hội thoại AI chưa quyết được được gom vào mục **"Cần xem lại"** để Manager xử lý.

### Nhân sự
- **Lịch phân ca** theo tuần, mỗi mẫu ca một màu, đánh dấu rõ hôm nay và ngày đã qua.
- **Đơn từ** (gửi, duyệt, từ chối, thu hồi) với số đơn chờ duyệt trên thanh điều hướng.
- **KPI** theo tháng, có thanh tiến độ hoàn thành.

### Báo cáo
- Thẻ tổng quan: tin vào, tỉ lệ phản hồi, thời gian phản hồi đầu trung bình, hội thoại đã đóng.
- Biểu đồ xu hướng theo ngày và bảng chi tiết theo phòng × kênh, cảnh báo dòng có tin vào mà chưa ai trả lời.
- Chọn nhanh khoảng thời gian: 7 ngày, 30 ngày, tháng này, tháng trước.

### Cấu hình (Admin, một phần cho Manager)
- Người dùng, phòng ban, kênh kết nối, nhãn, mẫu trả lời, nhật ký thao tác.

### Phân quyền
| Vai trò | Phạm vi |
|---|---|
| **Staff** | Hội thoại của phòng mình; nhận việc, trả lời, ghi chú, gắn nhãn |
| **Manager** | Toàn bộ phòng mình; giao/đổi người phụ trách, phân ca, duyệt đơn, quản lý từ khoá, nhãn, mẫu trả lời của phòng |
| **Admin** | Toàn hệ thống |

---

## Công nghệ

| Phần | Công nghệ |
|---|---|
| Frontend | Next.js 16 (App Router), React 19, TanStack Query v5, Tailwind CSS v4, Radix UI, lucide-react, Recharts |
| Backend | Python, FastAPI, SQLAlchemy, Alembic, WebSocket |
| Cơ sở dữ liệu | PostgreSQL |
| Kiểm thử | pytest, Vitest, Playwright |
| Chất lượng mã | ruff, mypy, import-linter, ESLint, TypeScript |
| CI | GitHub Actions |

Giao diện theo phong cách **Neo-Brutalism**: nền kem, viền đen, bóng đổ cứng, màu nhấn vàng. Mọi cặp màu chữ/nền đạt chuẩn tương phản WCAG AA. Trang `/design-system` (chỉ có ở môi trường dev) trình bày toàn bộ thành phần giao diện.

---

## Chạy trên máy

### Yêu cầu
- Python <!-- TODO: phiên bản --> và [uv](https://docs.astral.sh/uv/)
- Node.js <!-- TODO: phiên bản --> và npm
- PostgreSQL <!-- TODO: phiên bản -->

### Backend

```bash
cd backend
uv sync
# Tạo file .env (xem mục Biến môi trường)
uv run alembic upgrade head
uv run uvicorn <!-- TODO: đường dẫn app, vd app.main:app --> --reload --port 8003
```

Chạy worker nền: <!-- TODO: lệnh chạy worker -->

### Frontend

```bash
cd frontend
npm ci
# Tạo file .env.local (xem mục Biến môi trường)
npm run dev
```

Mở `http://localhost:3000`.

### Dữ liệu mẫu

```bash
cd backend
uv run python scripts/seed_kiem_chung.py   # <!-- TODO: kiểm tra đúng tên và cách chạy -->
```

---

## Biến môi trường

| Biến | Nơi dùng | Ý nghĩa |
|---|---|---|
| `APP_ENV` | Backend | `development`, `ci` hoặc `production` |
| `CHANNEL_CIPHER_KEY` | Backend | Khoá Fernet mã hoá thông tin kết nối kênh. Bắt buộc ngoài môi trường development |
| `DATABASE_URL` | Backend | <!-- TODO: kiểm tra tên biến --> Chuỗi kết nối PostgreSQL |
| <!-- TODO --> | | Khoá API của dịch vụ AI phân tích |
| <!-- TODO --> | | Token bot Telegram / thông tin các kênh |
| <!-- TODO --> | Frontend | Địa chỉ API backend |

Tạo khoá Fernet:

```bash
uv run python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

> Không commit file `.env` hay bất kỳ khoá nào lên repo.

---

## Kiểm thử

```bash
# Backend
cd backend
uv run pytest
uv run ruff check . && uv run mypy .
uv run lint-imports

# Frontend
cd frontend
npm test
npx tsc --noEmit && npm run lint
```

Kịch bản kiểm thử giao diện end-to-end (Playwright) nằm trong <!-- TODO: đường dẫn thư mục kịch bản -->, chạy trên dữ liệu seed.
