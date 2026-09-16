# Spec #F4 — Frontend Từ khoá & Phân tích AI

**Khác #F2/#F3 ở cách viết:** spec này soạn **sau khi gọi API thật**, không phải
trước. Ở #F3 tôi suy quy tắc từ code của module khác và **sai ba lần** (RB-4 viết
ngược, `PAST_SHIFT_DATE` bỏ sót, RB-3 thiếu một nửa) — mọi lần đều chỉ lộ ra khi
gọi thật. Nên lần này tôi dò trước 15 phép thử rồi mới viết. Mỗi mục dưới đây có
số hiệu phép thử đã xác nhận nó.

## 1. Phạm vi

Hai màn dưới khu **Cấu hình** (nơi #F2 đã có Người dùng · Phòng ban · Kênh ·
Nhật ký):

| Màn | Đường dẫn | Ai vào được |
|---|---|---|
| Từ khoá | `/quan-tri/tu-khoa` | **Mọi vai** — Staff xem, Manager/Admin sửa |
| Phân tích AI | `/quan-tri/phan-tich` | **Mọi vai** — chỉ đọc |

## 2. Quyền — đã đo, không suy

### RB-1 — Staff XEM ĐƯỢC, chỉ không SỬA ĐƯỢC

Đây là khác biệt lớn nhất so với khu quản trị của #F2 (nơi Staff bị chặn cửa):

| Thao tác | Staff | Manager | Admin | Mã lỗi khi bị chặn |
|---|---|---|---|---|
| `GET /keywords` | **200** | 200 | 200 | — |
| `GET /analyses` | **200** | 200 | 200 | — |
| `POST/PATCH/DELETE /keywords` | **403** | phòng mình | mọi phòng | `KEYWORD_MANAGER_REQUIRED` |
| Từ khoá phòng khác (Manager) | — | **403** | được | `KEYWORD_OUT_OF_SCOPE` |

*(phép thử 5, 9, 10, 11)*

Nên **không dùng `ChanTheoVai`** cho hai màn này — giống khu Nhân sự của #F3,
khác khu Cấu hình của #F2. Chặn ở cửa là chặn nhầm.

### RB-2 — Phạm vi dữ liệu do backend lọc

`pham_vi_phong_doc`: Admin `None` (tất cả); Manager/Staff đúng phòng mình; người
không thuộc phòng nào → rỗng. Đo thật: Admin 13 từ khoá, mgrA 1, mgrB 0, staffA
1 *(phép thử 9)*.

**FE không tự lọc lại.** Backend đã lọc; lọc chồng chỉ tạo cơ hội lệch.

## 3. Màn Từ khoá

### RB-3 — Chuẩn hoá là của backend, FE không đoán

`chuan_hoa()` bỏ dấu tiếng Việt, thường hoá, gộp khoảng trắng. Đo thật *(phép
thử 2, 3)*:

| Nhập | `normalized` | Kết quả khi đã có "Bảo Hành" |
|---|---|---|
| `Bảo Hành` | `bao hanh` | 201 |
| `bao hanh` | `bao hanh` | **409 `KEYWORD_DUPLICATE`** |
| `  Bảo    Hành  ` | `bao hanh` | **409 `KEYWORD_DUPLICATE`** |

**FE tuyệt đối không tự đoán trùng** bằng cách so chuỗi: `"Bảo Hành"` và
`"bao hanh"` trông khác nhau nhưng backend coi là một. Viết lại hàm bỏ dấu ở FE
là chép một thuật toán tinh tế sang chỗ thứ hai để hai bản lệch nhau sau này.
Gửi đi, nhận 409, hiện thẳng thông điệp server.

**Nhưng có hiện `normalized`** trên mỗi dòng: người dùng cần thấy vì sao
`"Bảo Hành"` bị báo trùng khi họ gõ `"bao hanh"`.

### RB-4 — `DELETE /keywords/{id}` trả **204**, không trả gì

*(phép thử 6)*. Giống `reset-password` của #F2 — khai sai kiểu trả về thì `tsc`
vẫn xanh (api-client trả `undefined as T`) còn UI vỡ lúc chạy. Khai `Promise<void>`.

### RB-5 — Ràng buộc nhập

`text`: `min_length=1`, `max_length=200`; rỗng hoặc 201 ký tự đều **422** *(phép
thử 8)*. Chặn ở FE bằng `maxLength` + nút Lưu khoá khi rỗng, vì cả hai đều biết
trước.

### RB-6 — `PATCH` chỉ nhận `text`

`UpdateKeywordRequest` chỉ có `text` — **không đổi được phòng** của từ khoá. Khi
sửa thì phòng hiện chỉ-đọc, như mẫu ca ở #F3.

## 4. Màn Phân tích AI

Chỉ đọc. `GET /analyses` trả `PageResponse` (`items`/`total`/`limit`/`offset`),
`limit` trần **100** — gửi 101 là 422 *(phép thử 3 của đợt sau)*.

### RB-7 — Ba `outcome`, ba hình dạng `null` KHÁC nhau

Đây là chỗ dễ vỡ nhất của màn này, và **dữ liệu thật chỉ có một nhánh**: cả 4
bản ghi đang có đều `AUTO_ASSIGNED`. Tôi đã gieo thêm hai bản ghi để nhìn thấy
hai nhánh kia *(phép thử 12–13)*:

| `outcome` | `suggested_department_id` | `confidence` | `extracted_terms` | Nghĩa |
|---|---|---|---|---|
| `AUTO_ASSIGNED` | có | có | có | LLM chọn được phòng, đủ tin cậy → đã tự phân |
| `AMBIGUOUS` | **`null`** | có | có | Đọc được nhu cầu nhưng không chọn được phòng |
| `NOT_ANALYZED` | **`null`** | **`null`** | **rỗng** | Không phân tích được (LLM lỗi/chưa đủ tin) |

Hệ quả bắt buộc cho UI:

- Cột "Phòng đề xuất" phải chịu được `null` → hiện dấu gạch, **không** hiện tên
  phòng rỗng hay `"undefined"`.
- Cột "Độ tin cậy" `null` → dấu gạch, **không** hiện `0%`. Cùng bài học RB-3 của
  #F3: `0%` nói "đã đo và bằng không", sai hẳn nghĩa.
- `extracted_terms` rỗng → câu giải thích, không phải ô trắng.

### RB-8 — `confidence` là `Decimal` 3 chữ số thập phân

Trả về dạng chuỗi `"0.950"`, `"1.000"`, `"0.310"`. Hiện dưới dạng phần trăm
(`95%`) cho người đọc, **không** đưa qua `Number` rồi làm tròn tuỳ tiện.

### RB-9 — Bảng tra theo enum phải phủ đủ (giữ từ #F2/#F3)

`AnalysisOutcome` có **3** giá trị. `Record<AnalysisOutcome, T>` + test liệt kê
tay cả ba, không đọc ngược từ chính bảng đang kiểm.

### RB-10 — Nút "Phân tích lại" tạm KHÔNG dựng

`POST /conversations/{id}/analyses` có tồn tại (Manager/Admin), nhưng:

1. Nó thuộc về **một hội thoại cụ thể**, hợp với màn Hộp thư (#F1) hơn là màn
   danh sách phân tích.
2. Docstring của chính endpoint ghi một **nợ phạm vi đã biết**: chỉ kiểm vai,
   **không kiểm phòng** — Manager kích hoạt lại được hội thoại `CHO_PHAN` bất kỳ
   và LLM phân về *bất kỳ* phòng nào.
3. Nó gọi LLM thật, tốn tiền, và chạy nền — kiểm chứng tốn kém.

Dựng nút này ở màn danh sách là mời người dùng dùng một đường đã biết là rộng
quá. Ghi thành nợ N5, để #F5 hoặc đợt sửa quyền định tuyến quyết định.

## 5. Kỹ thuật

Dùng lại nền #F1/#F2/#F3, không dựng lại: `HopThoai`, `HopXacNhan`, `NutChinh`,
`NutPhu`, `ThanhPhanTrang`, `thongDiepLoi`, `api-client`.

Thêm `lib/tu-khoa-api.ts` theo mẫu `nhan-su-api.ts`.

**Thanh tab Cấu hình** (`tab-quan-tri.tsx`) hiện có luật "ba tab chỉ Admin" —
hai tab mới phải hiện cho **mọi vai**, nên cần sửa component đó chứ không nhồi
cờ.

## 6. Tiêu chí nghiệm thu

1. Staff **vào được** cả hai màn, thấy dữ liệu phòng mình, **không** thấy nút sửa.
2. Manager tạo/sửa/xoá được từ khoá phòng mình; không thấy phòng khác.
3. Gõ từ khoá khác dấu/hoa-thường với từ đã có → hiện thông điệp trùng của server.
4. Xoá từ khoá chạy đúng (204, không vỡ UI).
5. Cả ba `outcome` hiện đúng; `null` ra dấu gạch, không ra `0%` hay `undefined`.
6. `npm test` xanh, `tsc`/`eslint`/`next build` sạch.
7. Kiểm chứng trình duyệt thật với cả ba vai.

## 7. Rủi ro

Màn Phân tích **chỉ đọc và dữ liệu thật rất lệch** (4/6 bản ghi cùng một
outcome, cùng một phòng). Rủi ro là viết UI chỉ đúng cho nhánh may mắn — đã giảm
bằng cách gieo sẵn hai nhánh còn lại trước khi viết dòng code nào.
