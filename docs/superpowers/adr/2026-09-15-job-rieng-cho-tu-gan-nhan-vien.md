# ADR: Job riêng cho việc tự gán nhân viên (#3)

**Ngày:** 2026-09-15
**Trạng thái:** Đã chấp nhận, đã chạy thật
**Liên quan:** [ADR Gemini + hàng đợi Procrastinate](2026-09-15-gemini-va-hang-doi-procrastinate.md)

## Bối cảnh

Hôm nay, ngay sau khi chuyển phân tích LLM (#2) sang chạy nền, chuỗi tự động
gán nhân viên (#3) **ngừng hoạt động hoàn toàn** mà không có lỗi nào hiện ra.

Trước đây cả ba việc nối nhau qua một danh sách `post_ingest_hooks`, chạy tuần
tự trong request webhook **theo thứ tự đăng ký**:

```
webhook → hook #2 (gọi LLM, phân phòng) → hook #3 (đọc phòng, gán người) → hook #5 (rollup)
```

Hook #3 dựa vào một giả định ngầm, ghi rõ trong docstring của nó: *"khi hook này
chạy, #2 đã commit việc phân phòng"*. Giả định đó đúng — cho tới khi hook #2
được thay bằng bản hàng đợi, chỉ `defer` một job rồi trả về sau vài mili-giây.

Từ đó, khi hook #3 chạy thì `conversation.department_id` vẫn `NULL`, nên nó
thoát ở guard đầu hàm. Vài giây sau worker phân phòng xong, nhưng **không còn ai
kích hoạt #3 nữa**. Hội thoại về đúng phòng và nằm đó vĩnh viễn, không người
phụ trách.

Không có lỗi, không có log cảnh báo. Đúng họ với lỗi `NOT_ANALYZED` hôm trước:
một giả định ngầm bị phá trong im lặng.

### Vì sao không test nào bắt được

Toàn bộ e2e chạy `QUEUE_ENABLED=false` — tức đường đồng bộ cũ, nơi #3 vẫn hoạt
động bình thường. Không có test nào đi qua chuỗi hook ở chế độ **nền**, vốn là
chế độ mặc định khi chạy thật.

## Audit toàn chuỗi `post_ingest_hooks`

Trước khi sửa, đã soát cả ba hook đăng ký sau #2 (yêu cầu của người dùng — không
chỉ xét #3):

| Hook | Có giả định #2 chạy xong? | Tình trạng |
|---|---|---|
| **#2 keyword** (`jobs/enqueue_hook.py`) | — | Chỉ `defer`, trả về sau vài ms |
| **#3 assignment** (`post_ingest_hook.py`) | **Có — điều kiện sống còn.** Đọc `department_id`, `NULL` thì `return` | **HỎNG HOÀN TOÀN** |
| **#5 analytics** (`rollup_hooks.py`) | **Có — nhưng không chí mạng.** Đọc `department_id` để gắn nhãn rollup | **SUY GIẢM** (xem dưới) |

Hai chuỗi còn lại (`post_reply_hooks`, `post_close_hooks`) không đi qua #2 nên
không bị ảnh hưởng.

### #5 analytics: nợ đã ghi nhận, CHƯA sửa trong đợt này

Docstring của `rollup_hooks` chốt hợp đồng *"Phòng HIỆN TẠI (GĐ3 F-A): đọc
`conversation.department_id` hiện tại khi ghi — kể cả INBOUND (đừng ghi NULL lúc
CHO_PHAN)"*. Hợp đồng đó **không còn giữ được**: hook chạy trước khi worker phân
phòng, nên tin đầu tiên của mỗi hội thoại mới rollup vào `department_id = NULL`.

Xếp là "suy giảm" chứ không phải "hỏng" vì hai lẽ:
- Số liệu tổng (inbound theo ngày/kênh) vẫn đúng; chỉ chiều "theo phòng" lệch.
- Có đường sửa sẵn: `RebuildDailyRollup` backfill từ nguồn sự thật.

Cố ý **không** gộp vào đợt sửa này: nó cần một quyết định riêng (chạy backfill
định kỳ, hay thêm job rollup nền), và gộp vào sẽ làm bản sửa phình ra.

## Quyết định

**Tách việc gán nhân viên thành một job riêng `tu_gan_nhan_vien`**, do job phân
tích đẩy tiếp sau khi phân phòng thành công.

```
webhook → defer(phan_tich_hoi_thoai) → 200 OK
worker  → phan_tich_hoi_thoai → Gemini → phân phòng → defer(tu_gan_nhan_vien)
worker  → tu_gan_nhan_vien → chọn nhân viên trong ca → gán
```

### Ba lựa chọn đã cân nhắc

| | Cách | Ưu | Nhược |
|---|---|---|---|
| A | Gộp #3 vào cuối job phân tích | Một job một việc trọn vẹn; ít phần động | **Retry gọi lại LLM đã thành công**; job phải tự nhớ "đã phân loại xong nhưng gán lỗi" — trạng thái nội bộ |
| **B** | **Job thứ hai `tu_gan_nhan_vien`** | **Mỗi job retry đúng phần việc của nó; guard nằm ở dữ liệu thật, không trong bộ nhớ job** | Thêm một loại job |
| C | Để #3 tự poll hội thoại chưa gán | Không phụ thuộc #2 | Thêm tiến trình định kỳ; trễ; tốn truy vấn vô ích |

**Chọn B** (quyết định của người dùng, 2026-09-15). Lý do: mỗi job chỉ retry
đúng phần việc của nó, tránh phải tự quản lý trạng thái nội bộ *"đã phân loại
xong nhưng gán người lỗi"* bên trong một job — đúng loại rủi ro đã sinh ra lỗi
`NOT_ANALYZED` hôm trước.

Hệ quả cụ thể của B so với A: LLM mất ~10–17 giây và tốn token mỗi lần gọi. Nếu
gán người lỗi vì DB chập, phương án A sẽ retry cả hai, gọi lại Gemini vô ích.
Với B, job phân tích đã `succeeded`, chỉ job gán retry.

### Chi tiết chốt kèm

- **Idempotency**: `chay_tu_gan` kiểm lại điều kiện trên dữ liệu thật (hội thoại
  `DANG_MO`, có phòng, chưa ai nhận) trước khi gán. Job chạy lại lần hai rơi vào
  guard này — không cần trạng thái nội bộ.
- **Không ai trong ca → không phải lỗi**: use case trả `QUEUED`, job báo Success.
  Retry cũng cho kết quả y hệt chừng nào chưa ai vào ca. Hội thoại nằm trong
  hàng đợi phòng; `post_close` và endpoint kéo tay là đường lấy việc ra.
- **Đẩy job lỗi thì nuốt, không ném**: hàng đợi hỏng không được làm job phân
  tích (đã thành công) bị tính là thất bại rồi retry — retry sẽ gọi lại LLM vô ích.
- **Hook #3 cũ giữ nguyên**: vẫn cần cho chế độ `QUEUE_ENABLED=false` và cho
  đường Manager phân phòng tay.

## Nguyên tắc rút ra

> **Khi chuyển một bước trong chuỗi hook từ đồng bộ sang nền, phải soát lại MỌI
> bước phía sau nó trong cùng chuỗi, không chỉ bước đang sửa.**

Thứ tự đăng ký hook là một **hợp đồng ngầm**: bước sau được phép thấy kết quả
của bước trước. Đẩy một bước sang hàng đợi là phá hợp đồng đó với mọi bước phía
sau cùng lúc — và phá trong im lặng, vì không có kiểu dữ liệu nào diễn đạt
"bước này đã chạy xong chưa".

Hệ quả thực hành:
1. Trước khi chuyển một hook sang nền, liệt kê mọi hook đăng ký sau nó và đọc
   xem chúng có đọc dữ liệu mà hook đó ghi không.
2. Với mỗi hook bị ảnh hưởng, quyết định rõ: nối lại vào đường nền, hay chấp
   nhận suy giảm (và ghi lại thành nợ, như #5 ở trên).
3. Test e2e chạy ở chế độ đồng bộ **không** bảo vệ đường nền. Cần test riêng đi
   qua chế độ thật.

## Hai lỗi phát sinh khi chạy thật (không test nào bắt được)

Đáng ghi lại vì cả hai chỉ lộ ra khi chạy end-to-end thật, sau khi mọi test đã xanh.

**1. `AppNotOpen` — đóng nhầm app của worker.** `day_job_tu_gan` mở app bằng
`async with app.open_async()` vô điều kiện. Trong worker app vốn đã mở, nên khi
thoát khối nó **đóng luôn app của worker**: job đang chạy không ghi nổi kết quả,
kẹt ở `doing`, worker chết. Sửa: thử `defer` trước, chỉ mở app khi bắt được
`AppNotOpen`.

**2. `NoReferencedTableError` — thiếu model lúc commit.** `chay_tu_gan` chết vì
SQLAlchemy không giải được `conversations.channel_id -> channels.id`: chưa module
nào nạp `ChannelModel`. `chay_phan_tich` thoát nạn chỉ vì các directory nó import
*tình cờ* kéo theo model — may mắn, không phải thiết kế.

Sửa: gom về `src/jobs/models_registry.py`, nạp một lần trong
`_lay_session_factory()` — điểm mọi job đều đi qua. Kèm test so metadata với
danh sách bảng thật trong PostgreSQL, nên thêm bảng mới mà quên khai sẽ đỏ ngay.

Đặt registry ở `src/jobs` chứ không `src/shared`: shared nằm *dưới* mọi module
nên không được biết tới chúng, dù import-linter hiện chưa cấm.

## Kiểm chứng

Bốn test khoá hành vi, mỗi test đã xác nhận **đỏ khi gỡ bản sửa, xanh khi có**:

| Test | Khoá điều gì |
|---|---|
| `test_job_phan_tich_phai_day_tiep_job_tu_gan` | Phân phòng xong phải đẩy job gán |
| `test_day_job_khi_app_DA_mo_khong_dong_app_lai` | Không đóng nhầm app của worker |
| `test_chay_tu_gan_giai_duoc_khoa_ngoai_trong_tien_trinh_sach` | Nạp đủ model để commit |
| `test_registry_nap_du_moi_bang_co_trong_database` | Registry không trôi khi thêm bảng |

Ba điều kiện bắt buộc để tái hiện lỗi khoá ngoại, đều phải trả giá mới biết:
tiến trình con sạch; hội thoại phải **tồn tại**; phải có nhân viên **đang trong
ca** (không ai nhận → `QUEUED` → không flush → lỗi lại ẩn đi).

**Chạy thật** (2026-09-15, hai lần liên tiếp, dữ liệu thật):

```
tin đến → HTTP 200 trong 1.0s
job 50 phan_tich_hoi_thoai → Gemini tin cậy 0.95 → Phòng Kinh doanh → Deferred 1 job
job 51 tu_gan_nhan_vien    → ASSIGNED → Nguyễn Hoài An
```

Đối chứng: hai hội thoại tạo **trước** bản sửa vẫn có phòng mà không có người phụ
trách — đúng triệu chứng của lỗi.

Toàn bộ: 943 test xanh, import-linter **16 kept / 0 broken**, mypy sạch.

## Ngưỡng xem lại

Xem lại quyết định này nếu:
- Số loại job vượt ~5: lúc đó cân nhắc một cơ chế mô tả chuỗi (workflow/DAG) thay
  vì để mỗi job tự biết job kế tiếp.
- Cần chạy #3 ngay lập tức sau #2 (độ trễ hiện tại ~1 giây là chấp nhận được).
- Nợ #5 được xử lý: nếu giải bằng job rollup nền thì nên xem lại cả ba job cùng lúc.
