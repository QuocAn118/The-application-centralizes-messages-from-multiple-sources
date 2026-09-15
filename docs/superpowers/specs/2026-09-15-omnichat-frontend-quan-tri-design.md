# Spec #F2 — Frontend Quản trị (Người dùng · Phòng ban · Kênh · Nhật ký)

**Ngày:** 2026-09-15
**Phụ thuộc:** #F1 (khung FE, api-client, auth) · #0 Foundation · #1 Inbox (kênh)
**Trạng thái:** Thiết kế

---

## 1. Vì sao làm trước các màn FE khác

Hiện **mọi tài khoản và phòng ban trong hệ thống đều do script seed tạo ra**.
Không có màn nào để tự tạo nhân viên, phòng ban hay kênh. Hệ quả dây chuyền:

- #F3 (Nhân sự) không có nhân viên nào để xếp ca.
- #F4 (Keyword) không có phòng ban để gán từ khoá.
- #3 auto-assign không có ai để gán việc.

Nói cách khác, F2 là **dữ liệu nền** của mọi màn còn lại. Đó là lý do nó đi đầu
dù không phải màn người dùng cuối dùng hằng ngày.

## 2. Phạm vi

Bốn màn, gom dưới mục **Cấu hình** của thanh điều hướng — chỗ
[nav-rail.tsx](../../../frontend/src/components/nav-rail.tsx) đã chừa sẵn:

| Màn | Đường dẫn | Ai vào được |
|---|---|---|
| Người dùng | `/quan-tri/nguoi-dung` | Admin (toàn bộ) · Manager (phòng mình, chỉ xem/sửa hồ sơ) |
| Phòng ban | `/quan-tri/phong-ban` | Admin |
| Kênh | `/quan-tri/kenh` | Admin |
| Nhật ký | `/quan-tri/nhat-ky` | Admin |

**Ngoài phạm vi:** đổi mật khẩu của chính mình (đã có ở `/doi-mat-khau`), màn
HRM/Keyword/Báo cáo (các sub-project sau).

## 3. Quyền — đọc từ use case thật, không suy đoán

Đây là phần dễ làm sai nhất nên chép chính xác từ code:

| Hành động | Quy tắc | Nguồn |
|---|---|---|
| Xem danh sách người dùng | STAFF bị chặn. **Manager bị ép về phòng mình** — tham số `department_id` bị ghi đè, không phải chỉ lọc mặc định | `list_users.py:35-44` |
| Tạo tài khoản | **Chỉ Admin.** Phòng đã có Manager thì không thêm Manager thứ hai | `create_user.py:63`, `:81-85` |
| Sửa hồ sơ (tên, điện thoại) | Chính mình, hoặc người mình quản được. **`can_manage`: Admin quản mọi người; Manager chỉ quản STAFF CÙNG PHÒNG — không quản được Manager khác** | `update_user.py:43-49`, `user.py:236-246` |
| Đổi vai trò / đổi phòng | Chỉ Admin | `change_user_role.py:41` |
| Vô hiệu hoá | Chỉ Admin. **Không vô hiệu hoá được Admin đang hoạt động cuối cùng** | `deactivate_user.py:39`, `:50` |
| Đặt lại mật khẩu | Chỉ Admin | `reset_user_password.py:44` |
| Phòng ban (tạo/sửa/ngắt) | Chỉ Admin | `create_department.py:40` |
| Kênh (mọi thao tác) | Chỉ Admin (`bao_dam_admin(actor)`) | `connect_channel.py:43` |
| Nhật ký | Chỉ Admin | `department_router.py:134` |

### RB-1 — UI ẩn nút theo quyền, nhưng KHÔNG coi đó là bảo vệ

Backend đã chặn; ẩn nút chỉ để đỡ gây hiểu nhầm. Mọi màn vẫn phải xử lý 403 tử
tế (api-client đã có `isForbidden`). Không suy luận quyền ở FE rồi bỏ qua lỗi
server trả về.

### RB-2 — Manager vào màn Người dùng thấy phòng mình, không thấy bộ lọc phòng

Vì backend ghi đè `department_id`, hiện bộ lọc phòng cho Manager sẽ gây hiểu
nhầm "lọc không ăn". Ẩn hẳn bộ lọc đó với Manager.

## 4. Màn Người dùng

Danh sách phân trang (`GET /users`, mặc định `limit=50`), kèm bộ lọc:
`search`, `role`, `is_active`, và `department_id` (chỉ Admin).

Mỗi dòng: tên, email, vai trò, phòng ban, trạng thái hoạt động. Hành động theo
quyền: sửa hồ sơ · đổi vai trò · đổi phòng · vô hiệu hoá/kích hoạt lại · đặt lại
mật khẩu.

### RB-3 — Mật khẩu tạm hiện MỘT lần, không lưu lại

`POST /users` và `POST /users/{id}/reset-password` đều nhận mật khẩu do Admin
tự đặt (`min_length=8`). Sau khi tạo, hiện mật khẩu đó **một lần** kèm nút sao
chép và cảnh báo "sẽ không hiện lại". Không ghi vào `localStorage`, không đưa
vào URL, không log ra console.

Người dùng mới bị buộc đổi mật khẩu ở lần đăng nhập đầu — luồng
`/doi-mat-khau` đã có sẵn từ #F1, không làm lại.

### RB-4 — Hai lỗi nghiệp vụ phải hiện rõ ràng, không phải "Đã có lỗi"

- `DepartmentAlreadyHasManagerError` → "Phòng này đã có quản lý. Mỗi phòng chỉ
  một quản lý."
- Vô hiệu hoá admin cuối → giải thích vì sao bị chặn, không chỉ báo lỗi chung.

Hai trường hợp này là *quy tắc nghiệp vụ*, người dùng cần biết để xử lý tiếp.

## 5. Màn Phòng ban

`GET /departments` → danh sách. Tạo (`POST`), sửa tên/mô tả (`PATCH`), ngắt hoạt
động (`POST /{id}/deactivate`).

Hiển thị kèm **số nhân viên** mỗi phòng — lấy bằng `GET /users?department_id=…`
đọc trường `total`, không tải hết danh sách.

### RB-5 — "Ngắt" không phải "Xoá"

Backend chỉ có `deactivate`, không có `DELETE`. Nhãn nút phải là "Ngừng hoạt
động", và hộp xác nhận nói rõ dữ liệu cũ vẫn còn. Dùng chữ "Xoá" sẽ khiến người
dùng tưởng mất dữ liệu.

## 6. Màn Kênh

`GET /channels` → danh sách kênh đã kết nối (platform, tên, phòng phụ trách,
trạng thái). Kết nối mới (`POST /channels`), sửa (`PATCH`), ngắt (`POST
/{id}/deactivate`).

### RB-6 — Credential là bí mật: chỉ ghi vào, không bao giờ đọc ra

`ConnectChannelRequest.credential` nhận token thô (Zalo OA / Meta / Telegram
bot token). `ChannelResponse` **không trả credential về** — đã kiểm tra schema.
Nên:

- Ô nhập dùng `type="password"`, có nút hiện/ẩn.
- Màn sửa để trống ô credential, ghi chú "để trống = giữ token hiện tại"
  (khớp `UpdateChannelRequest.credential: str | None`).
- Không hiện token trong bảng, không log, không đưa vào thông báo lỗi.

### RB-7 — `clear_department` là trường riêng, không phải `department_id = null`

`UpdateChannelRequest` có cả `department_id` lẫn `clear_department: bool`. Muốn
gỡ phòng khỏi kênh phải gửi `clear_department: true`; gửi `department_id: null`
sẽ bị hiểu là "không đổi". Đây là chỗ dễ viết sai.

## 7. Màn Nhật ký

`GET /audit-logs` với bộ lọc `actor_id`, `action`, `resource_type`, `from_time`,
`to_time`, phân trang.

15 giá trị `AuditAction` (từ `audit_log.py:19-35`) dạng `<đối tượng>.<hành động>`
— hiện nhãn tiếng Việt, nhóm theo tiền tố `user.` / `department.` / `auth.`.

### RB-8 — Nhật ký chỉ đọc

Entity `AuditLog` cố ý không có phương thức sửa/xoá. Màn này không có nút ghi.

## 8. Điều hướng

Mở khoá mục **Cấu hình** trong `nav-rail` (hiện đang `cursor-not-allowed`), dẫn
tới `/quan-tri`. Hai mục "Nhân sự" và "Báo cáo" vẫn khoá — thuộc #F3/#F5.

STAFF không thấy mục này. Manager thấy, nhưng vào chỉ có màn Người dùng.

## 9. Kỹ thuật

Theo đúng nền #F1, không dựng lại:

- **Gọi API** qua `api-client.ts` — không `fetch` rải rác (RB-1 của #F1).
- **Type** khai trong `types.ts`, đối chiếu schema backend. Không ép kiểu tại
  chỗ gọi.
- **Nhãn** qua `i18n.ts`, không viết chuỗi thẳng trong JSX.
- **Bảo vệ route** dùng `auth-guard.tsx` sẵn có, thêm kiểm vai.
- Thư mục `src/app/quan-tri/` + component dùng chung trong `src/components/`.

### RB-9 — Bảng tra theo enum phải phủ đủ mọi giá trị

Bài học từ lỗi `TELEGRAM` (sửa cùng ngày): `Record<Enum, …>` thiếu một khoá thì
trả `undefined` mà **không lỗi**. Mọi bảng nhãn mới (vai trò, hành động nhật ký,
nền tảng) cần test duyệt qua toàn bộ giá trị enum, không liệt kê tay.

## 10. Tiêu chí nghiệm thu

1. Admin tạo được phòng ban → tạo được nhân viên vào phòng đó → nhân viên đăng
   nhập được bằng mật khẩu tạm và bị buộc đổi.
2. Manager vào màn Người dùng chỉ thấy người phòng mình; không thấy nút tạo.
3. STAFF không thấy mục Cấu hình; gõ thẳng URL thì bị chặn.
4. Vô hiệu hoá Admin cuối cùng → hiện thông báo giải thích, không phải lỗi chung.
5. Kết nối kênh xong, credential không xuất hiện ở bất kỳ đâu trong UI.
6. Gỡ phòng khỏi kênh bằng `clear_department` có hiệu lực thật.
7. Nhật ký lọc được theo hành động và khoảng thời gian.
8. `npm test` xanh, `tsc --noEmit` sạch, `eslint` sạch, `next build` thành công.

## 11. Rủi ro

**Màn Người dùng có 9 endpoint** — nhiều nhất trong bốn màn, và mỗi hành động có
quy tắc quyền riêng. Rủi ro là làm vội rồi sai quyền. Giảm bằng cách tách giai
đoạn: xong hẳn màn Người dùng (gồm test quyền) rồi mới sang màn khác.

**Mockup Stitch:** đã tạo trong chính project #F1 (`5926030180396822885`) nên
dùng lại đúng design system, không dựng hệ màu mới:

| Màn | Screen ID |
|---|---|
| Người dùng — danh sách + menu thao tác | `44aa01a901964aa8b1fc7bfe20c433b6` |
| Modal tạo tài khoản + trạng thái "đã tạo" | `afb9f1d9ec234f1a9597c78f3cf2fc96` |

Mockup là *tham chiếu*, không phải nguồn sự thật: hai điểm cần chỉnh khi code —
badge trạng thái đang tràn hai dòng (thêm `whitespace-nowrap`), và hàng "Đã vô
hiệu hoá" nên mờ rõ hơn để phân biệt từ xa.

Màn Phòng ban / Kênh / Nhật ký sẽ tạo mockup ở đầu giai đoạn tương ứng, không
tạo trước — tránh vẽ thứ có thể đổi sau khi làm GĐ1.

Một token màu **mới** cần thêm vào `globals.css`: badge vai trò "Quản trị"
(nền `#EDE9FE`, chữ `#6941C6`). Hai vai còn lại dùng lại màu sẵn có.
