# Spec #F3 — Frontend Nhân sự (Ca làm việc · Đơn từ · KPI)

**Ngày:** 2026-09-16
**Phụ thuộc:** #F1 (khung FE) · #F2 (khu quản trị, component dùng chung) · #4 HRM (backend)
**Trạng thái:** Thiết kế

---

## 1. Vì sao làm bây giờ

Backend #4 HRM đã xong từ lâu nhưng **chưa có màn nào** — 16 endpoint không ai
gọi tới. Hệ quả cụ thể, không phải giả định:

- Ca làm việc chỉ tạo được bằng script. Hôm 15/09 tôi phải viết script Python
  để tạo một ca cho `staff@congty.vn` chỉ để kiểm chứng #3 auto-assign.
- **#3 auto-assignment dựa vào ca làm việc để chọn người.** Không có màn xếp ca
  thì tiêu chí đầu tiên của thuật toán gán việc luôn rỗng.
- Đơn từ và KPI hoàn toàn không dùng được.

#F2 vừa xong đã tạo ra nhân viên và phòng ban thật, nên giờ mới có gì để xếp ca.

## 2. Phạm vi

Ba màn, gom dưới mục **Nhân sự** của thanh điều hướng (hiện đang khoá):

| Màn | Đường dẫn | Ai vào được |
|---|---|---|
| Ca làm việc | `/nhan-su/ca-lam-viec` | Admin · Manager (phòng mình) · Staff (xem ca của mình) |
| Đơn từ | `/nhan-su/don-tu` | Mọi vai — nhưng thấy khác nhau |
| KPI | `/nhan-su/kpi` | Admin · Manager (phòng mình) · Staff (của mình) |

**Khác #F2 ở một điểm quan trọng:** đây **không phải khu quản trị**. Staff cũng
vào được cả ba màn, chỉ là thấy ít hơn. Vì vậy mục "Nhân sự" ở nav mở cho **mọi
vai**, không chặn như mục "Cấu hình".

**Ngoài phạm vi:** chấm công thực tế (backend không có), bảng lương, form builder
động (RequestType cố định ba loại).

## 3. Quyền — chép từ use case thật

Phần dễ sai nhất, nên chép chính xác thay vì suy đoán.

### 3.1 Ca làm việc

| Hành động | Quy tắc | Nguồn |
|---|---|---|
| Xem mẫu ca | Admin: tất cả. Manager/Staff: phòng mình | `shift_use_cases.py:131` → `pham_vi_phong_doc` |
| Tạo / sửa / ngừng mẫu ca | Manager (phòng mình) hoặc Admin | `:60-61`, `:94-98`, `:113-117` |
| Xem lịch phân ca | Admin: tất cả. Manager: cả phòng. **Staff: chỉ ca của CHÍNH MÌNH** | `shift_assignment_use_cases.py:142-147` |
| Phân ca / huỷ phân ca | Manager (phòng mình) hoặc Admin | `:69-76`, `:116-120` |

### 3.2 Đơn từ

| Hành động | Quy tắc | Nguồn |
|---|---|---|
| Gửi đơn | Ai cũng gửi được, nhưng **phải thuộc một phòng ban** (`REQUESTER_HAS_NO_DEPARTMENT`) | `request_use_cases.py:81-83` |
| Xem danh sách | Staff: đơn của mình. Manager: đơn phòng mình **HOẶC** của chính mình. Admin: tất cả | `:231-239` + `_ap_pham_vi` dùng `or_` |
| Thu hồi | Chỉ người gửi (`NOT_REQUEST_OWNER`), và chỉ khi còn `CHO_DUYET` | `:128-131` |
| Duyệt / từ chối | Xem RB-2 | `:158-186` |

### RB-1 — Admin không gửi được đơn từ

`create` đòi người gửi có `department_id`, mà **Admin không thuộc phòng nào**
(`ADMIN_CANNOT_HAVE_DEPARTMENT` ở #F2). Nên với Admin, UI **ẩn hẳn nút "Gửi
đơn"** thay vì để họ điền xong rồi nhận lỗi.

### RB-2 — Ai duyệt đơn nào phụ thuộc vai của NGƯỜI GỬI, không phải người duyệt

Đây là quy tắc dễ làm sai nhất của cả #F3:

- Đơn của **Staff** → Admin, **hoặc** Manager đúng phòng của đơn.
- Đơn của **Manager** → **chỉ Admin**.
- **Không ai tự duyệt đơn của chính mình** (`CANNOT_DECIDE_OWN_REQUEST`) — kể cả
  Admin.

Nghĩa là FE không thể quyết định hiện nút "Duyệt" chỉ từ vai người đang đăng
nhập; phải biết cả vai của người gửi. Mà `RequestResponse` **chỉ có
`requester_id`**, không có vai. Nên FE tra ngược từ danh sách người dùng đã tải.

Nếu không tra được (người gửi ngoài trang đầu), **vẫn hiện nút** và để server từ
chối — ẩn nhầm nút của người có quyền tệ hơn là hiện nhầm nút rồi báo lỗi rõ.

### 3.3 KPI

| Hành động | Quy tắc | Nguồn |
|---|---|---|
| Đặt mục tiêu | Manager (phòng mình) hoặc Admin | `kpi_use_cases.py:65,82` |
| Xem danh sách mục tiêu | Staff: **chỉ mục tiêu áp cho chính mình**. Manager: mọi mục tiêu trong phòng (cả cấp phòng lẫn cấp nhân viên). Admin: tất cả | `:116-127` |
| Xem tiến độ | Staff: chỉ của mình, **và không xem được KPI cấp phòng**. Manager: nhân viên phòng mình + phòng mình | `:180-204` |

### RB-3 — Giá trị thực đạt của KPI là chỉ đọc

`actual_value` và `achievement_percent` lấy từ nguồn hiệu suất (Inbox) qua port,
**không nhập tay**. UI chỉ có ô nhập `target_value`. Không dựng nút nào cho hai
trường kia.

Cả hai có thể `null` — nghĩa là "chưa có số liệu", không phải 0. Hiện dấu gạch,
không hiện `0%`: `0%` nói rằng đã đo và kết quả bằng không, sai hẳn nghĩa.

## 4. Màn Ca làm việc

Hai phần trên cùng một trang, vì chúng luôn được xem cùng nhau:

**Mẫu ca** (`GET /shifts`) — tên, giờ bắt đầu/kết thúc, phòng, trạng thái. Tạo,
sửa, ngừng hoạt động.

**Lịch phân ca** (`GET /shift-assignments?date_from&date_to`) — dạng lưới theo
tuần: hàng là nhân viên, cột là ngày. Phân ca bằng cách bấm vào ô trống.

### RB-4 — Ca KHÔNG qua đêm được (sửa lại sau khi kiểm chứng)

**Bản spec đầu của tôi ghi ngược.** Tôi suy đoán ca qua đêm hợp lệ vì #3 có xử
lý trường hợp "đang trong ca" bắc qua nửa đêm, rồi viết cả một quy tắc dặn
"UI không được validate `end_time > start_time`".

Chạy thật thì backend trả **422 `INVALID_SHIFT_WINDOW`** — "giờ kết thúc phải
sau giờ bắt đầu". Đọc `hrm/domain/entities/shift.py:12` thấy ghi rõ trong
docstring: *"ca không qua nửa đêm ở #4"*. Đây là giới hạn cố ý của backend, không
phải sơ suất.

Nên UI **phải** chặn trước: khoá nút Lưu và nói rõ lý do khi `end_time
<= start_time`. Để người dùng bấm Lưu rồi mới nhận 422 là bắt họ đoán.

**Bài học:** "module khác xử lý được X" không có nghĩa "module này chấp nhận X".
Lẽ ra phải thử một lời gọi thật trước khi viết quy tắc — đúng cùng loại sai lầm
mà kiểm chứng thật bắt được ở #F2 (`reset-password` trả 204).

### RB-5 — Trùng ca bị chặn ở server

`SHIFT_OVERLAP` khi phân cho một người hai ca chồng giờ cùng ngày. FE không tự
tính trùng — logic khoảng-thời-gian có ca qua đêm rất dễ sai. Hiện thẳng thông
điệp server (như RB-4 của #F2).

### RB-6 — Chỉ phân ca được cho nhân viên CÙNG PHÒNG với mẫu ca

`AGENT_OUT_OF_DEPARTMENT`. Ô chọn nhân viên phải lọc sẵn theo phòng của mẫu ca
đã chọn, không hiện cả công ty.

### RB-6b — Không phân ca cho ngày trong QUÁ KHỨ

Phát hiện khi chạy thật: `PAST_SHIFT_DATE` — "Không thể phân ca cho một ngày
trong quá khứ." Không có trong bản spec đầu.

Hệ quả lên lưới lịch: ô của ngày đã qua **không hiện nút "+"**. Buổi ca cũ vẫn
hiển thị bình thường (xem lại lịch sử), chỉ không xếp thêm được. Hiện nút ở đó
là mời người dùng vào một thất bại đã biết trước.

Đây là quy tắc thứ ba của #F3 mà tôi chỉ biết khi gọi API thật, sau `RB-4` và
`SHIFT_OVERLAP`.

## 5. Màn Đơn từ

Danh sách (`GET /requests?status&limit&offset`) + gửi đơn + duyệt/từ chối/thu hồi.

Ba loại đơn (`RequestType`): `NGHI_PHEP`, `TANG_LUONG`, `KHAC`. **Chỉ
`NGHI_PHEP`** có khoảng ngày; hai loại kia chỉ cần lý do.

Bốn trạng thái (`RequestStatus`): `CHO_DUYET`, `DA_DUYET`, `TU_CHOI`, `DA_HUY`.

### RB-7 — Từ chối bắt buộc có lý do

`RejectRequestRequest.reason` có `min_length=1`. Nút "Từ chối" mở hộp nhập lý do,
không từ chối thẳng. Duyệt thì không cần lý do.

## 6. Màn KPI

Danh sách mục tiêu (`GET /kpi-targets?period`) + đặt mục tiêu
(`POST /kpi-targets`) + xem tiến độ (`GET /kpi-progress`).

Hai loại chỉ số (`KpiMetricType`):
- `CONVERSATIONS_CLOSED` — số hội thoại đã đóng (càng cao càng tốt)
- `AVG_RESPONSE_MINUTES` — thời gian phản hồi trung bình (**càng THẤP càng tốt**)

### RB-8 — `achievement_percent` ĐÃ được backend chuẩn hoá chiều

Ban đầu tôi lo hai chỉ số ngược chiều nhau sẽ làm việc tô màu sai. Đọc
`domain/services/kpi_achievement.py` thì backend đã xử lý:

- Càng-cao-càng-tốt: `actual / target * 100`
- Càng-thấp-càng-tốt (`AVG_RESPONSE_MINUTES`): **`target / actual * 100`** —
  trả lời nhanh hơn mục tiêu cho ra > 100%.

Nên **`≥ 100%` luôn nghĩa là tốt** cho cả hai chỉ số, và FE tô màu thẳng theo
`achievement_percent` mà không cần biết chỉ số nào ngược chiều. Đây đúng là chỗ
lẽ ra tôi sẽ viết thêm logic thừa (và sai) nếu không đọc code.

**Nhưng `actual_value` thì vẫn phải hiểu theo chiều riêng:** 30 phút phản hồi so
với mục tiêu 15 phút là tệ, dù con số lớn hơn. Nên cột "thực đạt" hiện kèm đơn
vị và **không** tô màu theo độ lớn.

`achievement_percent` trả `None` không chỉ khi chưa có số liệu, mà còn khi mẫu
số bằng 0 (`target == 0`, hoặc `actual == 0` với chỉ số thời gian). Cả hai đều
hiện dấu gạch.

## 7. Điều hướng

Mở khoá mục **Nhân sự** ở `nav-rail` cho **mọi vai** (khác mục "Cấu hình" chỉ
Admin/Manager). Mục "Báo cáo" vẫn khoá — thuộc #F5.

Ba màn dùng lại thanh tab kiểu #F2, nhưng tab nào cũng hiện với mọi vai.

## 8. Kỹ thuật

Dùng lại nền #F1 + #F2, không dựng lại:

- `HopThoai`, `HopXacNhan`, `NutChinh`, `NutPhu`, `ThanhPhanTrang`, `OTimKiem`
- `thongDiepLoi` (RB-4 của #F2: hiện thẳng message server)
- `api-client`, type ở `types.ts`, nhãn ở `i18n.ts`

Thêm `lib/nhan-su-api.ts` + `lib/quyen-nhan-su.ts` theo mẫu `quan-tri-api.ts` /
`quyen-quan-tri.ts`.

### RB-9 — Bảng tra theo enum phải phủ đủ (giữ nguyên từ #F2)

Bốn enum mới: `RequestType` (3), `RequestStatus` (4), `KpiMetricType` (2),
`KpiSubjectType` (2). Mỗi bảng nhãn cần test duyệt toàn bộ giá trị, liệt kê tay
trong test chứ không đọc ngược từ chính bảng đang kiểm.

## 9. Tiêu chí nghiệm thu

1. Manager tạo được mẫu ca và phân ca cho nhân viên phòng mình.
2. Phân ca chồng giờ → hiện thông điệp server, không phải lỗi chung.
3. Staff vào màn Ca chỉ thấy ca của chính mình.
4. Staff gửi đơn → Manager phòng đó duyệt được; Manager gửi đơn → chỉ Admin duyệt.
5. Không ai thấy nút duyệt trên đơn của chính mình.
6. Admin không thấy nút "Gửi đơn".
7. Đặt mục tiêu KPI rồi xem được tiến độ; chưa có số liệu hiện dấu gạch, không hiện 0%.
8. `npm test` xanh, `tsc` sạch, `eslint` sạch, `next build` sạch.
9. Kiểm chứng thật bằng trình duyệt với cả ba vai.

## 10. Rủi ro

**Màn Ca làm việc có hai thực thể lồng nhau** (mẫu ca và buổi phân ca) và lịch
dạng lưới — phức tạp hơn mọi màn của #F2. Đây là nơi dễ sa đà nhất.

**RB-2 (ai duyệt đơn nào) cần dữ liệu FE không có sẵn.** Nếu tra tên/vai người
gửi không ổn thì cả màn Đơn từ sẽ khó dùng. Đây là điểm cần kiểm chứng sớm.

**RB-8 đã chốt** khi viết spec: backend chuẩn hoá chiều sẵn, FE không cần logic
riêng cho từng chỉ số.

**RB-4 đã phải viết lại** sau khi chạy thật: ca qua đêm bị backend từ chối, trái
hẳn với điều tôi suy đoán khi viết spec.
