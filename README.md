# OmniChat - Hệ thống Quản lý Đa kênh

Hệ thống quản lý tin nhắn đa kênh cho doanh nghiệp, tích hợp Zalo OA, Facebook Messenger và các nền tảng khác.

## Công nghệ sử dụng

### Backend
- **Framework**: FastAPI (Python)
- **Database**: PostgreSQL
- **Authentication**: JWT
- **ORM**: SQLAlchemy

### Frontend
- **Framework**: React 18 + TypeScript
- **Build Tool**: Vite
- **UI Library**: Ant Design
- **State Management**: Zustand
- **HTTP Client**: Axios
- **Data Fetching**: TanStack Query

## Cài đặt và Chạy

### 1. Cài đặt PostgreSQL

Đảm bảo PostgreSQL đã được cài đặt và đang chạy. Tạo database:

```sql
CREATE DATABASE omnichat_db;
```

### 2. Khởi tạo Database

```bash
cd backend
psql -U postgres -d omnichat_db -f init_db.sql
```

### 3. Cài đặt Backend

```bash
cd backend
python -m venv venv
venv\Scripts\activate  # Windows
pip install -r requirements.txt
```

Cấu hình file `.env`:
```
DATABASE_URL=postgresql://postgres:postgres@localhost:5432/omnichat_db
SECRET_KEY=your-secret-key
```

Chạy backend:
```bash
python main.py
# hoặc
uvicorn main:app --reload --port 8000
```

Backend sẽ chạy tại: http://localhost:8000
API Documentation: http://localhost:8000/docs

### 4. Cài đặt Frontend

```bash
cd frontend
npm install
```

Chạy frontend:
```bash
npm run dev
```

Frontend sẽ chạy tại: http://localhost:5173

## Tài khoản Demo

### Admin
- Email: `admin@omnichat.com`
- Password: `admin123`

### Manager
- Email: `manager.sales@omnichat.com`
- Password: `manager123`

### Staff
- Email: `staff1@omnichat.com`
- Password: `staff123`

## Tính năng chính

### Admin
- Xem thống kê tổng quan hệ thống
- Quản lý người dùng (CRUD)
- Thay đổi vai trò người dùng
- Xem tất cả từ khóa trong hệ thống
- Thống kê theo phòng ban, nhân viên, loại yêu cầu

### Manager
- Quản lý nhân viên trong phòng ban
- Quản lý KPI
- Quản lý từ khóa
- Quản lý ca làm việc
- Phân công ca cho nhân viên
- Phê duyệt/từ chối yêu cầu của nhân viên

### Staff
- Xem tin nhắn được giao
- Đánh dấu tin nhắn hoàn thành
- Tạo yêu cầu nội bộ (nghỉ phép, tăng lương, v.v.)
- Xem thông tin khách hàng
- Xem thông tin cá nhân và hiệu suất

## Tính năng đặc biệt

### Tự động giao việc
Hệ thống sử dụng thuật toán phân tích từ khóa để tự động giao tin nhắn cho nhân viên phù hợp dựa trên:
- Từ khóa trong tin nhắn
- KPI hiện tại của nhân viên
- Trạng thái làm việc (đang trong ca hay không)

### Webhook Integration
- Endpoint nhận tin nhắn từ Zalo OA: `/api/webhook/zalo`
- Endpoint nhận tin nhắn từ Meta: `/api/webhook/meta`
- Endpoint test: `/api/webhook/test/create-message`

## Cấu trúc thư mục

```
omnichat/
├── backend/
│   ├── main.py              # FastAPI app
│   ├── database.py          # Database connection
│   ├── models.py            # SQLAlchemy models
│   ├── schemas.py           # Pydantic schemas
│   ├── auth.py              # Authentication
│   ├── keyword_analyzer.py  # Auto-assignment algorithm
│   ├── routers/             # API endpoints
│   │   ├── auth.py
│   │   ├── admin.py
│   │   ├── manager.py
│   │   ├── staff.py
│   │   └── webhook.py
│   ├── init_db.sql          # Database schema
│   └── requirements.txt
│
└── frontend/
    ├── src/
    │   ├── api/             # API client
    │   ├── components/      # React components
    │   ├── pages/           # Page components
    │   ├── store/           # Zustand stores
    │   ├── types.ts         # TypeScript types
    │   ├── App.tsx          # Main app
    │   └── main.tsx         # Entry point
    ├── index.html
    ├── package.json
    └── vite.config.ts
```

## Lưu ý

- Đảm bảo PostgreSQL đang chạy trước khi start backend
- Backend phải chạy trước frontend
- Tất cả mật khẩu demo đều là `admin123`, `manager123`, `staff123`
- Webhook endpoints hiện tại là mock, cần credentials thực tế để tích hợp production
