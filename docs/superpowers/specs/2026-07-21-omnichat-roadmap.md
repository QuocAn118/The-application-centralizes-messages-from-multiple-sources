# OmniChat — Phân rã hệ thống & Roadmap

**Ngày:** 2026-07-21
**Trạng thái:** Đã duyệt
**Nguồn:** `Dafr.md`

## Vì sao phải phân rã

Đề bài mô tả ít nhất sáu hệ thống con độc lập: nhắn tin đa kênh, phân tích từ khoá bằng AI,
phân công công việc tự động, quản lý nhân sự, luồng phê duyệt đơn từ, và báo cáo thống kê.
Gộp cả sáu vào một spec sẽ cho ra tài liệu vừa nông vừa không dùng được để implement.

Mỗi sub-project dưới đây có chu trình riêng: **spec → plan → implement**.

## Bối cảnh đã chốt

| Quyết định | Giá trị |
|---|---|
| Tenancy | Single-tenant (một doanh nghiệp) |
| Nhân viên ↔ phòng ban | 1 nhân viên thuộc đúng 1 phòng ban |
| Manager ↔ phòng ban | 1 Manager quản đúng 1 phòng ban |
| Backend | Python + FastAPI |
| Cơ sở dữ liệu | PostgreSQL |
| Frontend | Next.js / React (web only) |
| Mobile app | **Không làm** — xem "Mâu thuẫn trong đề bài" bên dưới |
| Kiến trúc | Clean Architecture, tổ chức theo module dọc |
| Tạo tài khoản | Chỉ Admin; không có tự đăng ký |
| Token | Access token + refresh token có rotation |
| Xoá nhân viên | Soft delete; Admin kích hoạt lại được |
| Cloud | Chưa quyết — đóng gói Docker, trung lập nền tảng |
| Credential Zalo OA / Meta | Người dùng xác nhận **có credential thật** |

## Roadmap

| # | Sub-project | Nội dung chính | Phụ thuộc |
|---|---|---|---|
| 0 | **Foundation** | Skeleton clean architecture, PostgreSQL, Alembic, auth JWT, RBAC 3 vai trò, CRUD User/Department, audit log, CI + test | — |
| 1 | **Omnichannel Inbox** | Channel adapter (Zalo OA, Meta), webhook, gửi/nhận tin, hội thoại hợp nhất, WebSocket realtime, Customer/CRM | 0 |
| 2 | **Keyword & AI Analysis** | CRUD từ khoá theo phòng ban, trích xuất từ khoá từ nội dung tin nhắn, gắn nhãn hội thoại | 1 |
| 3 | **Auto-Assignment** | Routing theo keyword + KPI + trạng thái ca làm, hàng đợi, đánh dấu hoàn thành | 1, 2, 4 |
| 4 | **HRM** | Ca làm việc, lịch phân ca, KPI, biểu mẫu đơn từ + luồng phê duyệt | 0 |
| 5 | **Analytics & Dashboard** | Báo cáo đa chiều (phòng ban / nhân viên / loại yêu cầu / thời gian), khối lượng tin nhắn, hiệu suất | 1–4 |

**Thứ tự khuyến nghị:** 0 → 1 → 4 → 2 → 3 → 5.

HRM (#4) được đưa lên sớm vì Auto-Assignment (#3) cần dữ liệu ca làm và KPI, trong khi #4
độc lập với #1 nên có thể triển khai song song.

Frontend Next.js sẽ có spec riêng sau khi API của #0 hoàn tất.

## Mâu thuẫn trong đề bài đã được giải quyết

**Mobile app.** Phần mô tả vai trò ghi cả ba vai trò đều dùng "ứng dụng di động & web",
nhưng phần "Công nghệ phía Client" chỉ liệt kê Web App (Next.js/React) và không nhắc tới bất
kỳ công nghệ mobile nào. Quyết định: **chỉ làm Web App**. API vẫn thiết kế trung lập
(REST + JWT) để mobile dùng lại được nếu phạm vi mở rộng sau này.

**Quyền tạo tài khoản.** Đề bài cho Admin "quản lý tài khoản" đồng thời cho Manager "tạo, cập
nhật, xóa" nhân viên trong phòng ban — hai quyền này chồng lấn. Quyết định: **chỉ Admin tạo và
xoá tài khoản**; Manager chỉ xem và sửa thông tin hồ sơ nhân viên trong phòng mình.

## Rủi ro cần theo dõi

**Credential nền tảng bên thứ ba (ảnh hưởng #1).** Zalo OA và Meta đều giới hạn tính năng theo
cấp độ duyệt ứng dụng. Trước khi bắt đầu #1 cần xác định chính xác: loại ứng dụng đã đăng ký,
các quyền (scope/permission) đã được cấp, và trạng thái xác minh. Phát hiện thiếu quyền giữa
chừng sẽ chặn toàn bộ sub-project.

**NFR 1000 người dùng đồng thời.** Chưa được kiểm chứng ở bất kỳ giai đoạn nào tính đến #0.
Con số này chỉ có ý nghĩa khi #1 hoàn tất, vì đó là nơi tải thực sự phát sinh.

**NFR uptime 99,5% và sao lưu/phục hồi.** Phụ thuộc hạ tầng cloud chưa được chọn. Thiết kế ứng
dụng giữ trạng thái stateless để không cản trở mục tiêu này, nhưng không thể đảm bảo con số khi
chưa có nền tảng triển khai.
