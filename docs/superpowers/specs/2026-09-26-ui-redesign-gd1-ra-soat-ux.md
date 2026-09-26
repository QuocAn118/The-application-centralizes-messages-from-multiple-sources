# Redesign UI/UX — Giai đoạn 1: Rà soát UX

Trạng thái: **ĐÃ DUYỆT 2026-09-26**, kèm các quyết định và điều chỉnh ở §10
(§10 **đè** lên mọi chỗ khác trong file nếu có mâu thuẫn).

Ưu tiên: **C** = cao · **TB** = trung bình · **T** = thấp.
Nhãn **[BE-x]** = cần thay đổi backend, chi tiết ở §5.

---

## 0. Hiểu biết chung (để bạn sửa nếu sai)

**Bạn đã nói:**
- Người dùng chính là nhân viên CSKH, dùng **cả ngày**. Tác vụ số một là đọc và
  trả lời khách. Sau đó mới tới quản lý ca, từ khoá, báo cáo.
- Sửa cả UX lẫn UI. Phong cách Neo-Brutalism theo đặc tả, taste-skill chỉ để
  nâng chất lượng.
- Chỉ làm desktop 1280–1920px. Dưới 1280px không được vỡ layout.
- Được sửa backend, nhưng mỗi thay đổi phải được duyệt trước và có test.
- Thống nhất tên "Cấu hình". Dùng lucide-react. Được dùng Radix/shadcn và
  Recharts. Ảnh chụp để ngoài repo.

**Tôi giả định (cần bạn xác nhận):**
- Thành công = nhân viên xử lý hội thoại nhanh hơn: thấy ngay cái gì chưa đọc,
  cái gì của mình, trả lời ít thao tác nhất. Quản lý thấy ngay chỗ có vấn đề.
- Nhất quán giữa các màn quan trọng hơn làm từng màn thật "độc".

---

## 1. Vấn đề xuyên suốt

| # | Vấn đề | Đề xuất | Ưu tiên |
|---|---|---|---|
| X1 | Dưới 1280px vỡ layout (đo thật ở 390px: rail lệch, chat mất, bảng cắt) | Khung app `min-width: 1280px`, màn hẹp hơn thì cuộn ngang. Không làm màn "hãy dùng máy tính" (YAGNI — cuộn ngang đã không vỡ) | C |
| X2 | Tương phản dưới AA: `muted-soft` 2,58:1 (24 file), chữ badge Telegram 3,68:1 | Bảng màu mới phải đạt ≥ 4,5:1 cho mọi chữ. Kiểm bằng script ở Giai đoạn 2 | C |
| X3 | Không có focus bàn phím (0 lần `focus-visible` trong `src/`) | Viền focus 3px rõ ràng trong mọi component gốc | C |
| X4 | Nội dung bảng trải hết 1920px | Màn bảng/form: `max-width` ~1440px, căn giữa. Hộp thư và Lịch vẫn dùng hết bề ngang (đó là nơi cần chỗ) | TB |
| X5 | Nút thao tác lặp trên mọi dòng, chữ đỏ (Ca, Từ khoá, KPI, Phòng ban, Kênh) | Menu "⋯" (Radix DropdownMenu) giống màn Người dùng. Thao tác huỷ hoại (Xoá, Ngừng, Ngắt) nằm cuối menu, **luôn có hộp xác nhận** | C |
| X6 | Phân cấp chữ phẳng. Tiêu đề khu và tiêu đề mục chỉ lệch nhau ~2px | Thang chữ cố định: tiêu đề trang 28/800, tiêu đề mục 18/700, nội dung 14/400–500 | C |
| X7 | Tiêu đề đặt lúc ngoài card (Người dùng, Kênh, Phòng ban), lúc trong card (Ca, Từ khoá, KPI) | Một mẫu duy nhất: **Header trang** (tiêu đề + mô tả ngắn + nút chính bên phải) → **Card** (bộ lọc + bảng) | C |
| X8 | Nút chính vô hiệu trông như hỏng (Gửi, mọi nút "Lưu") | Trạng thái vô hiệu kiểu Neo-Brutalism: nền xám, viền đứt, bỏ bóng. Không được nhạt như lỗi tải | C |
| X9 | Trạng thái đang tải / rỗng / lỗi: mỗi màn một kiểu, có màn chỉ in "Đang tải…" | 3 component `TrangThaiTai` / `TrangThaiRong` / `TrangThaiLoi` (có icon, câu giải thích, nút hành động) | TB |
| X10 | 4 thanh tab chép nhau (`TabNhanSu/QuanTri/TuKhoa/BaoCao`) | Một component `TabKhu` nhận danh sách tab | TB |
| X11 | "Cấu hình" (nav) và "Quản trị" (tiêu đề) lệch nhau | Đổi mọi chữ hiển thị thành "Cấu hình". **Giữ route `/quan-tri/*`**: đổi route phải sửa link, 8+ kịch bản kiểm chứng và tài liệu, mà người dùng không thấy URL. Ghi rõ trong spec | C |
| X12 | Mốc giờ có cả giây ("16:53:26 17/9/2026") ở Đơn từ, Nhật ký | Mốc tương đối cho mốc gần ("5 phút trước", "Hôm qua 14:32"), mốc đầy đủ hiện khi rê chuột (`title`) | T |
| X13 | Không có bộ icon, 9 SVG vẽ tay | lucide-react thay toàn bộ | TB |
| X14 | Nav rail không có huy hiệu số: không biết có tin mới / đơn chờ duyệt | Huy hiệu trên "Hộp thư" (số chưa đọc) **[BE-1]** và "Nhân sự" (số đơn chờ duyệt — lấy từ API sẵn có) | TB |

---

## 2. Hộp thư (`/inbox`, `/inbox/[id]`) — ưu tiên cao nhất

**Mục đích:** nhận và trả lời khách. **Tác vụ chính:** tìm hội thoại cần xử lý →
đọc → trả lời → (đôi khi) nhận việc / phân công / đóng.

| # | Vấn đề | Đề xuất | Ưu tiên |
|---|---|---|---|
| I1 | Mỗi mục 3 dòng; tag kênh + "Đang mở" lặp ở mọi mục | 2 dòng: **tên · giờ** / **xem trước**. Kênh = icon lucide nhỏ gắn góc avatar, màu theo kênh. Trạng thái chỉ hiện khi cần chú ý ("Chờ phân", "Chưa ai nhận") | C |
| I2 | Không biết mục nào chưa đọc | Tên + xem trước in đậm, chấm và số đếm bên phải **[BE-1]** | C |
| I3 | Avatar chỉ là chữ cái xám, không phân biệt | Màu nền avatar suy ra ổn định từ id khách (6–8 màu dịu, đạt tương phản). Dùng `avatar_url` nếu có | TB |
| I4 | Thời gian "15/09" | Tương đối: "2 phút", "14:32", "Hôm qua", "Th 2", "15/09" | TB |
| I5 | **Thiếu bộ lọc quan trọng nhất cho nhân viên: "Của tôi"** (hiện chỉ lọc theo trạng thái) | Thêm tab "Của tôi" · "Chưa ai nhận" · "Tất cả" **[BE-3]**. Lọc trạng thái chuyển thành bộ lọc phụ | C |
| I6 | Phân trang "1–20 / 20" + nút ‹ › | Cuộn liên tục (IntersectionObserver + `offset` sẵn có). **Không cần backend** | TB |
| I7 | Khung chat: tin không có mốc ngày, không nhóm theo người gửi | Vạch mốc ngày ("Hôm nay", "Thứ Hai 15/09"). Gom tin liên tiếp cùng người gửi, chỉ hiện giờ ở tin cuối nhóm | C |
| I8 | Header chat: "Đóng hội thoại" là nút nổi bật nhất | Header: tên + kênh + phòng + **người phụ trách** (bấm để đổi) **[BE-2]**. Nút chính = "Nhận việc" (nếu chưa có ai). "Đóng" chuyển vào menu "⋯", có xác nhận | C |
| I9 | Không có panel thông tin khách | Panel phải 320px, **thu gọn được** (ở 1280px mặc định thu): kênh, id trên nền tảng, người phụ trách, nhãn **[BE-6]**, ghi chú nội bộ **[BE-5]**, lịch sử hội thoại **[BE-4]** | C |
| I10 | Ô nhập trông lỗi, nút Gửi như bị vô hiệu | Ô nhập viền 2px, nút Gửi nổi (vàng, bóng cứng). Dòng gợi ý nhỏ: "Enter để gửi · Shift+Enter xuống dòng" | C |
| I11 | Không có mẫu trả lời nhanh | Gõ `/` hoặc bấm nút → danh sách mẫu, chọn là chèn **[BE-7]** | TB |
| I13 | Không biết khách đã chờ bao lâu | Hội thoại có tin cuối là **tin vào chưa được trả lời**: hiện "Chờ 12 phút" ở danh sách + header. Quá ngưỡng (hằng số `NGUONG_CHO_PHUT = 15`) thì đổi màu cảnh báo **[BE-9]** | TB |
| I12 | Chưa hiện thông tin liên hệ (SĐT, email) | **Nền tảng không cung cấp**: bảng `customers` chỉ có tên, avatar, id. Muốn có thì phải cho nhân viên nhập tay → **đề nghị HOÃN** (xem §6) | T |

**Sửa lại brief:** "Enter để gửi / Shift+Enter xuống dòng" và "đính kèm ảnh"
**đã có sẵn** trong `o-soan-tin.tsx`. Vấn đề là không có gì cho người dùng biết.
Chỉ cần thêm gợi ý, không phải làm lại.

---

## 3. Nhân sự

### 3.1 Ca làm việc (`/nhan-su/ca-lam-viec`)

**Mục đích:** xem ai làm ca nào trong tuần; Manager phân ca. **Tác vụ chính:**
xem lịch tuần này, thêm/huỷ phân ca. Sửa mẫu ca là việc thỉnh thoảng.

| # | Vấn đề | Đề xuất | Ưu tiên |
|---|---|---|---|
| S1 | Màn mở ra ở danh sách **Mẫu ca** (việc ít dùng); lịch phải cuộn mới thấy | **Lịch lên đầu, chiếm cả màn.** Mẫu ca chuyển vào ngăn kéo bên phải (nút "Mẫu ca") hoặc tab con | C |
| S2 | T2–T6 trống không giải thích | **Nguyên nhân thật:** đó là ngày **đã qua** (hôm nay T7 26/09); lưới cố ý không cho phân ca lùi ngày. Đề xuất: ngày đã qua nền xám kẻ sọc, nhãn "Đã qua", vẫn **hiện ca đã phân** (dữ liệu có sẵn) | C |
| S3 | Ô "+" 1px mờ, gần như vô hình | Ô trống cả ô là vùng bấm; "+" hiện rõ khi rê chuột / focus | C |
| S4 | Các ca không phân biệt được | Mỗi mẫu ca một màu dịu (suy từ id), dùng làm dải màu trái của khối ca + chú giải | TB |
| S5 | "Hôm nay" chỉ có chữ xanh ở tiêu đề cột | Cột hôm nay: viền dày + nền vàng nhạt + nhãn "Hôm nay" | C |
| S6 | Badge "Đang dùng" trông như nút | Badge = chữ + chấm, **không viền, không bóng**, để khác hẳn nút | C |
| S7 | Sửa/Ngừng dùng lặp mỗi dòng | Menu "⋯" (X5) | TB |

### 3.2 Đơn từ (`/nhan-su/don-tu`)

| # | Vấn đề | Đề xuất | Ưu tiên |
|---|---|---|---|
| D1 | Đơn chờ duyệt lẫn trong đơn đã quyết | Với Manager/Admin: mặc định lọc **"Chờ duyệt"**, tab kèm số đếm. "Đã quyết" là tab riêng | C |
| D2 | Câu "Quản trị viên không thuộc phòng ban nào…" lơ lửng ở góc phải | Đưa vào chỗ lẽ ra có nút "Gửi đơn", dạng ghi chú giải thích nút vắng mặt | T |
| D3 | Lý do từ chối chữ đỏ lẫn trong ô nội dung | Dòng riêng có nhãn "Lý do từ chối:" | T |

### 3.3 KPI (`/nhan-su/kpi`)

| # | Vấn đề | Đề xuất | Ưu tiên |
|---|---|---|---|
| K1 | Chỉ có số, không thấy tiến độ | Thanh tiến độ trong ô "Hoàn thành". Giữ nguyên quy tắc null ≠ 0 (dấu gạch ≠ 0%) | TB |
| K2 | Nút "Sửa mục tiêu" mỗi dòng | Bấm dòng để sửa, hoặc menu "⋯" | T |
| K3 | Chọn kỳ bằng 2 ô select | Nút ‹ Tháng 9/2026 › | T |

---

## 4. Từ khoá, Báo cáo, Cấu hình, Xác thực

### 4.1 Từ khoá (`/tu-khoa/danh-sach`)

| # | Vấn đề | Đề xuất | Ưu tiên |
|---|---|---|---|
| T1 | Mỗi từ khoá một hàng full màn | **Chip** nhóm theo phòng; mỗi nhóm có ô thêm nhanh cuối dãy (gõ + Enter) | C |
| T2 | "dạng khớp" hiện thường trực | Ẩn. Chỉ hiện trong tooltip của chip, và **ở thông báo lỗi trùng** (đó là lúc người ta cần biết vì sao bị trùng) | TB |
| T3 | Sửa/Xoá mỗi dòng | Bấm chip để sửa; nút × trên chip (có xác nhận) | C |

### 4.2 Phân tích AI (`/tu-khoa/phan-tich`)

| # | Vấn đề | Đề xuất | Ưu tiên |
|---|---|---|---|
| A1 | Không bấm được sang hội thoại đang được phân tích | Mỗi dòng có link mở hội thoại trong Hộp thư | TB |
| A2 | "Chưa rõ phòng" (cần người xem) lẫn với kết quả tốt | Lọc nhanh "Cần xem lại" (AMBIGUOUS + NOT_ANALYZED) | TB |

### 4.3 Báo cáo (4 tab)

| # | Vấn đề | Đề xuất | Ưu tiên |
|---|---|---|---|
| B1 | Một bảng, trống 2/3 màn | Tab **Hội thoại** thành tổng quan: 4 thẻ KPI (tin vào, tỉ lệ phản hồi, thời gian phản hồi đầu TB, đã đóng) → biểu đồ xu hướng theo ngày → bảng chi tiết **[BE-8]** | C |
| B2 | Số cần cảnh báo bị chìm (Chưa phân phòng: 9 vào / 0 ra) | Dòng có tin vào mà 0 tin ra: nền cảnh báo + icon + câu "9 tin chưa ai trả lời" | C |
| B3 | Chỉ chọn ngày bằng 2 ô date | Nút nhanh: **7 ngày · 30 ngày · Tháng này · Tháng trước**; ô ngày tuỳ chọn vẫn giữ | C |
| B4 | Tab Nhân viên/Ca-KPI/Đơn từ chỉ có bảng | Mỗi tab 2–3 thẻ tóm tắt đầu trang (tổng xử lý, giờ công, đơn chờ). Tính từ dữ liệu đã tải, **không cần backend** | TB |

### 4.4 Cấu hình (`/quan-tri/*`)

| # | Màn | Vấn đề | Đề xuất | Ưu tiên |
|---|---|---|---|---|
| Q1 | Người dùng | Đã có menu "⋯" — **đây là mẫu chuẩn** cho các màn khác | Giữ, chỉ đổi style | T |
| Q2 | Phòng ban, Kênh | Mục đã ngừng/đã ngắt cùng trọng lượng với mục đang chạy | Mặc định chỉ hiện đang hoạt động, bật "Hiện cả đã ngừng (3)" | TB |
| Q3 | Kênh | "Ngắt kênh" đỏ trên mọi dòng | Menu "⋯" + xác nhận (X5) | TB |
| Q4 | Nhật ký | Cột "Đối tượng" hiện **UUID trần** | Tra tên qua map `/users` (giống màn Báo cáo), UUID chuyển vào tooltip. **Không cần backend** | TB |

### 4.5 Xác thực

| # | Màn | Vấn đề | Đề xuất | Ưu tiên |
|---|---|---|---|---|
| L1 | Đăng nhập | Dòng giới thiệu "Zalo, Facebook, Instagram" **thiếu Telegram** — kênh duy nhất đang chạy thật | Sửa chữ + làm lại theo phong cách mới | TB |
| L2 | Đổi mật khẩu | Không có chỉ báo điều kiện mật khẩu (≥8 ký tự, có chữ + số) | Danh sách điều kiện tick dần khi gõ (quy tắc lấy đúng từ `kiem_tra_do_manh`) | T |
| L3 | Staff vào khu bị cấm | Màn chặn chỉ có 1 câu + nút | Giữ logic, làm lại theo mẫu `TrangThaiLoi` | T |

### 4.6 Hộp thoại (15 cái)

Tất cả đi qua `HopThoai` / `NutChinh` / `NutPhu`, nên sửa 3 component gốc là
cả 15 hộp thoại đổi theo. Riêng:

- Chuyển `HopThoai` sang **Radix Dialog**: bẫy focus, Esc, trả focus về nút mở
  (hiện đang tự viết tay).
- Form dài (Tạo người dùng, Kết nối kênh): lỗi hiện ngay dưới từng ô, không chỉ
  một dòng đỏ chung ở cuối.
- Hộp xác nhận thao tác huỷ hoại: nút xác nhận ghi đúng hành động ("Ngắt kênh"),
  không ghi chung chung "Xác nhận".

---

## 5. Thay đổi backend cần duyệt

Tất cả là **thêm mới**, có test. **Riêng BE-2 có đổi một quy tắc nghiệp vụ**
(cho phép đổi người phụ trách), xem câu hỏi 5 ở §6.

| Mã | Tính năng | API | Database | Ảnh hưởng phần đang chạy |
|---|---|---|---|---|
| **BE-1** | Chưa đọc (I2, X14) | `POST /inbox/{id}/read`; `GET /inbox` thêm `unread_count` mỗi mục; `GET /inbox/unread-total` cho huy hiệu nav | Bảng mới `conversation_reads(user_id, conversation_id, last_read_at)`, PK kép. Migration thêm bảng, không đụng bảng cũ | Truy vấn danh sách thêm một subquery đếm tin inbound sau `last_read_at` → **phải đo tốc độ** trước/sau. Socket realtime có sẵn chỉ cần phát thêm sự kiện |
| **BE-2** | Phân công nhân viên từ header (I8) | `POST /inbox/{id}/assign-user {user_id \| null}` | Không đổi schema. Ghi `assignment_log` có sẵn | ⚠ **Đổi một quy tắc nghiệp vụ.** Hàm domain hiện có `assign_to_agent` (`conversation.py:113`) **từ chối nếu đã có người phụ trách** (`AlreadyAssignedError`) — tức hiện nay người phụ trách là cố định. "Đổi người" cần thêm phương thức domain mới `reassign` / `unassign`. Quy tắc đề nghị: chỉ Manager (phòng mình) / Admin; người được gán phải đang hoạt động, cùng phòng; hội thoại phải `DANG_MO`. Ảnh hưởng #3: gán tay **đè** gán tự động, và tải của người cũ/mới thay đổi ngay. **Nếu bạn không muốn đổi quy tắc này**, BE-2 thu lại thành "Manager giao cho người khi hội thoại *chưa có ai*" — dùng được hàm cũ, không đổi quy tắc |
| **BE-3** | Lọc "Của tôi" / "Chưa ai nhận" (I5) | `GET /inbox` thêm `assignee=me\|none` | Không | Thêm một điều kiện `WHERE`; mặc định không truyền thì y như cũ |
| **BE-4** | Lịch sử hội thoại của khách (I9) | `GET /inbox` thêm `customer_id` | Không | Như BE-3. Vẫn áp phạm vi phòng như cũ |
| **BE-5** | Ghi chú nội bộ (I9) | `GET/POST /customers/{id}/notes`, `DELETE /notes/{id}` (chỉ người viết hoặc Admin) | Bảng mới `customer_notes(id, customer_id, author_id, body, created_at)` | Ghi chú gắn với **khách**, nên thấy được ở mọi hội thoại của khách đó. Ai xem được hội thoại thì xem được ghi chú |
| **BE-6** | Nhãn khách (I9) | CRUD `/tags` (Manager/Admin); `PUT /customers/{id}/tags` | Bảng mới `tags(id, name, color, is_active)`, `customer_tags(customer_id, tag_id)` | Không đụng luồng cũ. Chưa làm lọc hộp thư theo nhãn (thêm sau nếu cần) |
| **BE-7** | Mẫu trả lời nhanh (I11) | CRUD `/reply-templates` (Manager cho phòng mình, Admin cho tất cả); nhân viên chỉ đọc | Bảng mới `reply_templates(id, department_id null=dùng chung, title, body, updated_at)` | Không đụng luồng gửi tin: chỉ chèn chữ vào ô soạn |
| **BE-8** | Tổng quan báo cáo (B1) | `GET /analytics/overview?from&to&department_id` → `{totals, avg_first_response_seconds, response_rate, daily: [...]}` | Không. Đọc bảng rollup theo ngày **đã có** (`work_date`) | Chỉ thêm endpoint đọc, cùng quy tắc phạm vi (Manager ép về phòng mình). Thời gian phản hồi TB tính **có trọng số** (tổng giây / tổng mẫu), không lấy trung bình của các trung bình |

**Thứ tự đề nghị:** BE-3 và BE-2 trước (nhỏ, giá trị cao cho nhân viên), rồi
BE-1, BE-4/5/6, BE-7. BE-8 làm cùng màn Báo cáo.

---

## 6. Cần bạn quyết định

1. **Chưa đọc (BE-1):** theo **từng người** (mỗi nhân viên có trạng thái đọc
   riêng) hay theo **hội thoại** (một người đọc là hết chưa đọc cho cả phòng)?
   → Đề nghị: **từng người**. Theo hội thoại thì Manager lướt qua là mất dấu của
   nhân viên.
2. **Tỉ lệ phản hồi (BE-8):** định nghĩa nào?
   (a) hội thoại có ≥1 tin trả lời / hội thoại có tin vào trong kỳ, hoặc
   (b) tin ra / tin vào.
   → Đề nghị **(a)**. (b) phạt nhân viên trả lời gọn trong một tin.
3. **Nhãn (BE-6):** dùng chung toàn công ty hay riêng từng phòng?
   → Đề nghị **dùng chung**, Manager/Admin quản lý. Đơn giản hơn; nhãn kiểu
   "VIP", "Khiếu nại" vốn không thuộc riêng phòng nào.
4. **Thông tin liên hệ (I12):** nền tảng không gửi SĐT/email. Có muốn cho nhân
   viên nhập tay không?
   → Đề nghị **hoãn**. Cần thêm cột và form nhập, mà chưa rõ ai dùng.
5. **Đổi người phụ trách (BE-2):** cho phép Manager **đổi / gỡ** người đang phụ
   trách (đổi quy tắc hiện tại), hay chỉ **giao khi chưa có ai** (giữ quy tắc)?
   → Đề nghị **cho đổi**: nhân viên nghỉ giữa ca thì hội thoại kẹt không ai gỡ
   được. Nhưng đây là thay đổi nghiệp vụ nên cần bạn chốt.
6. **Màn hẹp hơn 1280px:** chỉ cho cuộn ngang (đề nghị) hay thêm thông báo
   "Hãy dùng màn hình rộng hơn"?

---

## 7. Thư viện dự kiến (theo quyết định #4)

| Thư viện | Dùng cho | Lý do |
|---|---|---|
| `lucide-react` | Mọi icon | Bạn chọn. Chỉ bundle icon được import |
| `@radix-ui/react-dialog`, `-dropdown-menu`, `-select`, `-tabs`, `-tooltip`, `-popover` | Hộp thoại, menu "⋯", select, tab, tooltip, chọn người phụ trách | Lo phần khó (bẫy focus, bàn phím, ARIA); style 100% do mình. **Dùng thẳng Radix, không qua shadcn**: shadcn chỉ là lớp chép sẵn class kiểu "shadcn" mà ta sẽ xoá hết để thay Neo-Brutalism, tức là thêm file để rồi viết lại |
| `recharts` | Biểu đồ xu hướng ở Báo cáo | Chỉ thêm khi làm màn Báo cáo |

Không thêm thư viện ngày giờ: mốc tương đối viết bằng `Intl.RelativeTimeFormat`
có sẵn trong trình duyệt.

---

## 8. Chia việc (đề nghị)

Việc này quá lớn cho một spec. Đề nghị các phần, mỗi phần có spec → plan →
thực thi riêng, đúng thứ tự Giai đoạn 3 bạn đã đặt:

1. **Design system + khung app** (Giai đoạn 2): token, component gốc, trang
   `/design-system`, nav rail, header trang, X1–X13
2. **Hộp thư**, gồm BE-1/2/3/4/5/6/7
3. **Lịch phân ca** + Đơn từ + KPI
4. **Từ khoá** + Phân tích AI
5. **Báo cáo**, gồm BE-8 + Recharts
6. **Cấu hình + Xác thực**

## 9. Công cụ đã dùng ở giai đoạn này

- **superpowers:brainstorming**: xếp việc này vào loại "kiến trúc" (đổi component
  dùng chung, thêm tính năng backend) → phải có spec + plan riêng cho từng phần
  (§8).
- **codebase-memory-mcp** + đọc code: kiểm từng đề xuất có cần backend không.
  Nhờ vậy phát hiện Enter-để-gửi đã có, `/assign` chỉ phân **phòng** (không phân
  người), và `customers` không có SĐT/email.
- **ponytail**: dùng làm bộ lọc khi chọn giải pháp. Nó quyết định: Radix thay vì
  shadcn, `Intl.RelativeTimeFormat` thay vì thư viện ngày giờ, cuộn liên tục trên
  `offset` sẵn có, không làm màn "hãy dùng máy tính", hoãn thông tin liên hệ. Ở
  Giai đoạn 4 sẽ chạy thêm `ponytail-review` bên cạnh `code-review` để bắt phần
  thiết kế thừa.
- **taste-skill**: chưa dùng. Để dành cho Giai đoạn 2 (thẩm mỹ, token, component).
- **Playwright MCP** đã kết nối lại trong phiên này; từ Giai đoạn 2 sẽ dùng nó để
  chụp ảnh.

---

## 10. Quyết định sau duyệt (2026-09-26) — ĐÈ lên các mục phía trên

### 10.1 Trả lời §6

| # | Câu hỏi | Chốt |
|---|---|---|
| 1 | Chưa đọc | **Theo từng người** |
| 2 | Tỉ lệ phản hồi | **(a)** hội thoại có ≥1 tin trả lời / hội thoại có tin vào trong kỳ. Thẻ KPI giữ thêm **thời gian phản hồi đầu TB có trọng số** |
| 3 | Nhãn | **Dùng chung toàn công ty.** Chỉ Manager/Admin tạo/sửa/xoá nhãn. Nhân viên được **gắn/gỡ** nhãn có sẵn cho khách. Màu nhãn **chỉ chọn từ bảng màu đã kiểm tương phản** của design system (không cho nhập mã màu tự do) |
| 4 | Liên hệ nhập tay | **Hoãn.** Panel khách **không** hiện ô trống hay nút "+ Thêm" cho trường chưa làm |
| 5 | Đổi người phụ trách | **Cho đổi/gỡ**, theo quy tắc đã đề nghị (chỉ Manager phòng mình / Admin; người được gán đang hoạt động, cùng phòng; hội thoại `DANG_MO`) |
| 6 | Màn < 1280px | **Chỉ cuộn ngang** |

### 10.2 Bổ sung cho BE-2 (phân công)

- Khung chat hiện **dòng hệ thống**: "Chuyển từ A sang B" / "Gỡ người phụ trách A"
  / "B đã nhận việc". Nguồn: `assignment_log` (đã ghi sẵn cho mọi lần gán).
- Phát **sự kiện realtime** cho người được giao **và** người bị gỡ.
- Ghi `assignment_log` cho mọi lần đổi/gỡ.

### 10.3 BE-1 (chưa đọc) — thời điểm đánh dấu đã đọc

Đánh dấu đã đọc (cập nhật `last_read_at`) khi:
1. mở hội thoại;
2. có tin mới đến **lúc hội thoại đang mở VÀ tab trình duyệt đang focus**
   (`document.hasFocus()`; tab nền thì không tính là đã đọc);
3. chính người đó gửi trả lời.

**Hiệu năng:** thêm index phục vụ truy vấn đếm (dự kiến
`messages(conversation_id, direction, created_at)`). Đo `GET /inbox` **trước và
sau** trên dữ liệu **vài nghìn hội thoại** (gieo dữ liệu đo riêng). Nếu chậm thêm
**> 100 ms** thì **dừng, báo user** trước khi làm tiếp — phương án dự phòng là lưu
sẵn bộ đếm.

### 10.4 BE-5 (ghi chú nội bộ) — giới hạn theo phòng

- Bảng `customer_notes` có thêm cột **`department_id`** = phòng của người viết
  **tại thời điểm viết**.
- Nhân viên / Manager chỉ xem ghi chú **của phòng mình**; Admin xem tất cả.
- Khách nhắn nhiều phòng → mỗi phòng chỉ thấy ghi chú của phòng đó.
- UI ghi rõ: *"Chỉ phòng [tên] thấy ghi chú này"*.
- Test bắt buộc: nhân viên phòng A **không** đọc được ghi chú phòng B qua API.

### 10.5 BE-9 (mới) — thời gian khách chờ (I13)

Kiểm tra dữ liệu sẵn có: `GET /inbox` trả `last_message_at` nhưng **không** trả
ai gửi tin cuối → **không tính được ở danh sách** (chỉ tính được trong khung chat
đã mở, nơi tin có `direction`). Vậy cần backend:

| Tính năng | API | Database | Ảnh hưởng |
|---|---|---|---|
| "Chờ 12 phút" ở danh sách + header | `GET /inbox` thêm `waiting_since: datetime \| null` = thời điểm **tin vào đầu tiên sau tin trả lời cuối**; `null` nếu tin cuối là tin ra (hoặc chưa có tin vào) | Không. Dùng chung index của BE-1 | Thêm một subquery vào truy vấn danh sách → **tính chung ngân sách 100 ms của BE-1**, đo cùng lúc |

"Chờ" tính từ **tin chưa trả lời đầu tiên**, không phải tin cuối: khách nhắn 3 tin
liên tiếp thì đã chờ từ tin thứ nhất. Ngưỡng cảnh báo là hằng số FE
`NGUONG_CHO_PHUT = 15`.

### 10.6 Chia lại phần (thay §8)

1. **Design system + khung app** (Giai đoạn 2)
2. **2a — Hộp thư mới** + BE-3 (Của tôi / Chưa ai nhận) + BE-2 (phân công) + BE-1
   (chưa đọc) + BE-9 (thời gian chờ, I13). Panel khách ban đầu **chỉ** có: kênh,
   id trên nền tảng, người phụ trách.
3. **2b — Bổ sung panel / ô soạn**, lần lượt: BE-4 (lịch sử) → BE-5 (ghi chú) →
   BE-6 (nhãn) → BE-7 (mẫu trả lời).
4. **Lịch phân ca** + Đơn từ + KPI
5. **Từ khoá** + Phân tích AI
6. **Báo cáo** + BE-8 + Recharts
7. **Cấu hình + Xác thực**

### 10.7 Quy tắc chung bổ sung

- **Mọi migration phải có `downgrade()` (rollback) chạy được**, và được thử
  up → down → up.
- Sau mỗi phần, **các kịch bản kiểm chứng hiện có vẫn phải chạy qua** (scripts
  Playwright của #F2–#F5 + test backend/frontend). Nếu một kịch bản hỏng *vì UI đổi
  có chủ đích* (đổi selector, đổi chữ) thì cập nhật kịch bản và ghi rõ lý do trong
  commit — không lặng lẽ nới lỏng điều kiện kiểm.
