# ADR 2026-09-15 — Gemini làm nhà cung cấp LLM và hàng đợi Procrastinate cho #2

Trạng thái: **Chấp nhận / Đã làm** (2026-09-15). Bối cảnh: bật #2 bằng LLM thật.
Người dùng có khoá Google AI Studio (Gemini), không có khoá Anthropic. Đồng thời
trả nợ "hook gọi LLM đồng bộ trong webhook" đã ghi từ spec #2 §9 — nợ này chỉ
thành rủi ro thật khi LLM được bật, nên xử lý cùng đợt.

---

## A. Gemini qua REST `httpx`, KHÔNG cài SDK `google-generativeai`

### Vấn đề
Adapter Gemini có hai đường: gọi REST thẳng bằng `httpx` (đã là dependency), hay
cài SDK chính thức `google-generativeai`.

### Quyết định
**Gọi REST thẳng bằng `httpx`.**

Lý do:
- Adapter chỉ cần **đúng một endpoint** không streaming (`:generateContent`).
  Thêm SDK là thêm cả một cây phụ thuộc cho một lời gọi HTTP.
- `httpx` đã dùng cho cả ba adapter kênh (Zalo, Meta, Telegram), nên test bơm
  `MockTransport` theo đúng quy ước sẵn có, không cần cơ chế giả riêng.
- Không khoá vào vòng đời phát hành của SDK Google.

Ngưỡng xem lại: nếu cần streaming, function calling, hoặc file upload thì SDK
đáng giá hơn — lúc đó chỉ thay phần thân adapter, port không đổi.

### Hệ quả
- Khoá API đi qua header `x-goog-api-key`, **không** qua query string — query
  string hay bị ghi vào log của proxy/server. Có test khoá hành vi này.
- `responseMimeType: "application/json"` ép Gemini trả JSON thuần, nhưng bước cắt
  fence ```json ở `prompt_parsing` vẫn giữ: đó là gợi ý, không phải bảo đảm.

## B. Tách phần trung lập ra `prompt_parsing.py`

### Vấn đề
Toàn bộ logic dựng prompt và parse/gác JSON (kẹp confidence về [0,1], UUID sai
→ `None`, cắt fence) nằm trong `claude_classifier.py`. Chép sang adapter Gemini
sẽ tạo hai bản dễ trôi khác nhau.

### Quyết định
Tách thành `prompt_parsing.py` dùng chung. `claude_classifier.py` và
`gemini_classifier.py` chỉ còn phần riêng: gọi API + bóc text khỏi response.

### Hệ quả
- Sửa prompt một chỗ, cả hai nhà cung cấp cùng đổi.
- Adapter Claude **giữ nguyên API công khai** — 10 test sẵn có của nó xanh không
  cần sửa một dòng, đó là bằng chứng refactor không đổi hành vi.
- `LLM_PROVIDER=gemini|claude|none` chọn nhà cung cấp; code Claude **không bị xoá**.

---

## C. Hàng đợi: Procrastinate (Postgres), không Redis/Celery, không BackgroundTasks

### Vấn đề
Hook #2 gọi LLM **đồng bộ trong request webhook** (`webhook_router.py:113`). Với
LLM thật, mỗi tin đến làm webhook chậm vài giây. Zalo/Meta/Telegram đều có timeout
ngắn và sẽ **gửi lại** khi quá hạn: tin không nhân đôi (idempotency giữ đúng)
nhưng mỗi lần gửi lại tốn thêm một lời gọi LLM — vừa chậm vừa tốn tiền.

### Ba phương án đã cân nhắc

| Phương án | Chịu restart | Hạ tầng thêm | Vì sao không/có chọn |
|---|---|---|---|
| **FastAPI `BackgroundTasks`** | ❌ Không | Không | Job nằm trong RAM tiến trình. Server restart giữa chừng (deploy, crash) là **mất job im lặng** — tin đã lưu nhưng không bao giờ được phân tích, không dấu vết |
| **Redis + Celery** | ✅ Có | Redis | Máy dev không cài được Redis (quá nặng). Thêm một dịch vụ phải vận hành, sao lưu, giám sát riêng |
| **Procrastinate (Postgres)** ✅ chọn | ✅ Có | Không | Chạy trên chính PostgreSQL đã có. `SELECT ... FOR UPDATE SKIP LOCKED` cho nhiều worker lấy job an toàn. Job nằm trong bảng nên sống sót restart |

### Quyết định
**Procrastinate.** Webhook tách làm hai phần:

- **Đồng bộ (trong request):** verify chữ ký → parse → lưu tin qua use case ingest
  hiện có → `defer` một job mang `conversation_id` → trả 200.
- **Bất đồng bộ (worker riêng):** gọi `IConversationClassifier` → tự phân phòng →
  hook auto-assign (#3) chạy tiếp theo kết quả.

Áp dụng cho **cả ba nền tảng** vì webhook router dùng chung một danh sách
`post_ingest_hooks`, không có nhánh riêng theo nền tảng.

### Ngưỡng xem lại
Procrastinate poll bảng `procrastinate_jobs` trong cùng PostgreSQL với dữ liệu
nghiệp vụ. Ở mức vài tin/giây thì không đáng kể. **Nếu vượt ~50 tin/giây liên
tục**, hoặc bảng job vượt vài triệu dòng, cần xem lại: tách DB riêng cho hàng
đợi, hoặc chuyển sang Redis/Celery thật.

---

## D. Schema Procrastinate bọc vào MỘT revision Alembic

### Vấn đề
Procrastinate có lệnh riêng `procrastinate schema --apply` để tạo bảng của nó.
Dùng lệnh đó sẽ tạo **hệ thống migration thứ hai** song song Alembic.

### Quyết định
**Bọc SQL của Procrastinate vào một revision Alembic** (`f6a7b8c9d0e1`), giữ
nguyên tắc "một nguồn sự thật cho schema" của dự án: `alembic upgrade head` vẫn
đủ để dựng một DB chạy được, không phải nhớ chạy đúng hai lệnh theo đúng thứ tự.

Đã kiểm chứng khả thi trước khi làm: `SchemaManager.get_schema()` trả toàn bộ SQL
dưới dạng chuỗi, nên `op.execute()` được.

SQL được **đọc lúc chạy migration** thay vì chép cứng vào file. Đánh đổi:
- *Lợi:* bản chép cứng sẽ âm thầm lệch khi nâng cấp Procrastinate.
- *Hại:* migration phụ thuộc phiên bản thư viện đang cài. **Nâng cấp Procrastinate
  cần một revision mới** để ghi lại thay đổi schema.

### Hệ quả
- Mọi đối tượng đều mang tiền tố `procrastinate_`, không đụng tên nào của ứng dụng.
- `downgrade` xoá sạch (đã kiểm chứng: bảng=0, hàm=0, kiểu=0 sau khi hạ). Job đang
  chờ sẽ mất — chấp nhận được vì hạ revision là thao tác chủ động, và phân tích lỡ
  mất có thể kích hoạt lại thủ công từ giao diện Manager.

## E. Procrastinate dùng pool kết nối RIÊNG, không dùng chung pool SQLAlchemy

### Vấn đề
App dùng SQLAlchemy async; Procrastinate nói chuyện với psycopg thuần. Có nên ép
hai bên dùng chung một pool?

### Quyết định
**Pool riêng.** Procrastinate cần `LISTEN/NOTIFY` và `SELECT ... FOR UPDATE SKIP
LOCKED` do chính nó phát; không có đường ghép mà không lách vào nội bộ của cả hai
thư viện.

Trùng lặp cấu hình được giữ ở mức tối thiểu: URL DB lấy thẳng từ `Settings`
(hàm `url_psycopg` chỉ bỏ tiền tố `+psycopg` của dialect SQLAlchemy), nên vẫn chỉ
có **một** nguồn cấu hình.

## F. Module `src.jobs` ở tầng composition

### Vấn đề
Task phân tích cần biết cả `keyword` (use case) lẫn `inbox` (tra hội thoại). Đặt
nó trong bất kỳ module nghiệp vụ nào cũng phá ranh giới `inbox ⊥ keyword` mà
import-linter đang giữ.

### Quyết định
Tạo `src/jobs/` — tầng composition, ngang hàng `main.py`. Các contract chỉ ràng
buộc `src.modules.*` nên `src.jobs` được phép biết nhiều module, đúng như
`main.py` vẫn làm.

**Không đặt logic nghiệp vụ ở đây:** task chỉ điều phối, mọi quyết định vẫn nằm
trong use case của module tương ứng.

### Hệ quả
`import-linter` giữ nguyên **16 kept, 0 broken** — không thêm, không sửa contract nào.

---

## G. Idempotency và fallback

**At-least-once:** Procrastinate có thể chạy lại một job nếu worker crash giữa
chừng. Guard đã có sẵn: `AnalyzeConversation` bỏ qua hội thoại đã có bản ghi phân
tích (RB-5 của spec #2), nên chạy lại không tạo phân tích trùng và không tự phân
phòng lần nữa. Task gọi với `force=False`.

**Retry:** `RetryStrategy(max_attempts=3, exponential_wait=8)` — chờ 8s → 16s →
32s cho lỗi tạm thời (mạng chập, quota 429, timeout).

> **Phát hiện khi kiểm chứng:** `max_attempts` đếm số lần **thử lại sau** lần chạy
> đầu, nên `max_attempts=3` nghĩa là tối đa **4 lần chạy**. Dễ hiểu nhầm thành
> "tổng cộng 3 lần" — đã ghi rõ trong code và khoá bằng test.

**Hết retry:** job thành `failed`, hội thoại **nằm yên ở `CHO_PHAN`** — chưa từng
bị đổi trạng thái, nên không kẹt ở trạng thái không xác định. Đúng bằng hành vi
khi thiếu API key: Manager phân tay như bình thường.

---

## Ghi nhận sai lệch giữa tài liệu và code thật

Spec #2 §10 ghi "LLM (Claude API)" như một quyết định chốt. Từ đợt này, nhà cung
cấp là **cấu hình** (`LLM_PROVIDER`), không còn cố định Claude — spec đã cập nhật.
Phần còn lại của §10 (gác kết quả LLM, không gọi lặp, lỗi thì bỏ qua) không đổi.

---

## Hệ quả phát hiện sau (cùng ngày)

Việc chuyển #2 sang nền đã **phá chuỗi hook `post_ingest`**: hook #3 (tự gán
nhân viên) đăng ký sau #2 và dựa vào giả định "#2 đã phân phòng xong", nên từ
đợt này nó không bao giờ gán được ai — trong im lặng.

Xem [ADR job riêng cho tự gán nhân viên](2026-09-15-job-rieng-cho-tu-gan-nhan-vien.md)
để biết cách sửa, kết quả audit cả chuỗi hook, và nguyên tắc rút ra.
