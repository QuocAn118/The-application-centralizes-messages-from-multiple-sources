# ADR: Module khác đọc bảng `conversations` của inbox

Ngày: 2026-09-28 · Trạng thái: đã chấp nhận (ghi lại hiện trạng)

## Bối cảnh

`conversations` thuộc module **inbox**. Hai module khác đọc bảng này **trực tiếp
bằng SQL** (không qua API hay use case của inbox), nhưng theo **hai cách khác
nhau**. Cách thứ nhất không được import-linter nhìn thấy, nên phải ghi lại ở đây.

Cả hai cách đều **chỉ đọc**. Không module nào ngoài inbox ghi vào
`conversations`. Khi keyword phân phòng, nó gọi use case của inbox qua
`inbox_bridge/conversation_router.py`, không `UPDATE` bảng này.

## 1. keyword — đọc THEO TÊN BẢNG, không import

`backend/src/modules/keyword/infrastructure/repositories/analysis_repository.py`

```python
_HOI_THOAI = table("conversations", column("id"), column("department_id"))
```

| Cột | Dùng để |
|---|---|
| `id` | nối với `conversation_analyses.conversation_id` |
| `department_id` | `IS NULL` = hội thoại đang chờ phân phòng |

Có một truy vấn dùng hai cột này. BE-10 cho Manager thấy thêm các phân tích
của hội thoại chờ phân:
`conversation_id IN (SELECT id FROM conversations WHERE department_id IS NULL)`.

**Vì sao đọc theo tên:** import-linter cấm `keyword.presentation` phụ thuộc
inbox, kể cả gián tiếp. Chuỗi phụ thuộc là presentation → dependencies →
repository. Import `ConversationModel` vào repository sẽ phá hợp đồng đó. Tham
chiếu bảng theo tên là một phụ thuộc ở tầng dữ liệu, không phải tầng mã.

**Rủi ro:** đổi tên bảng hoặc cột thì mypy và import-linter đều **không** báo.
Lỗi chỉ lộ ra lúc chạy SQL.

## 2. analytics — đọc qua MODEL ORM của inbox (có import)

`backend/src/modules/analytics/infrastructure/sources/inbox_stats_source.py` và
`.../hooks/rollup_hooks.py` import `ConversationModel`, `MessageModel` và
`ChannelModel`. Hợp đồng import-linter cho phép tầng infrastructure của
analytics làm việc này.

Các cột của `conversations` đang dùng: `id`, `department_id`, `channel_id`,
`assigned_user_id`, `status`, `created_at`, `updated_at`, `closed_at`.
Cùng với đó là `messages.conversation_id`, `messages.direction`,
`messages.created_at`, `messages.sender_user_id` và `channels.id`,
`channels.platform`.

Đổi tên cột trong model thì mypy báo ngay, vì truy cập qua thuộc tính Python.
Đổi **ý nghĩa** của cột thì không báo; xem mục test bên dưới.

(`assignment` và `hrm` cũng đọc model inbox theo cách này:
`assignment/infrastructure/inbox_bridge/waiting_queue.py` và
`hrm/infrastructure/performance/inbox_performance_source.py`.)

## Test nào hỏng nếu `conversations` đổi

| Thay đổi | Test hỏng |
|---|---|
| Đổi tên bảng, hoặc tên cột `id`/`department_id` | `tests/unit/keyword/test_bang_conversations_theo_ten.py`: so `_HOI_THOAI` với `ConversationModel.__table__`, chạy trong vài mili giây, không cần DB. Lớp chặn thứ hai là e2e `tests/e2e/test_keyword_api.py::TestDanhSachPhanTichBe10`, chạy SQL thật trên Postgres |
| `department_id` thôi nhận `NULL` (bỏ trạng thái "chờ phân phòng") | cùng test unit trên (kiểm `nullable`), cùng `TestDanhSachPhanTichBe10::test_manager_thay_hang_cho_phan_nhung_khong_thay_phong_khac` |
| Đổi tên cột analytics đang dùng | mypy (`uv run mypy src`), trước cả khi chạy test |
| Đổi ý nghĩa cột analytics đang dùng (vd. `department_id` thành phòng lúc tạo thay vì phòng hiện tại) | `tests/integration/test_analytics_infra.py`, gồm `TestResponseRateSource`, và `tests/e2e/test_analytics_api.py` |

## Quy tắc khi đổi schema `conversations`

1. Chạy `rg -n '"conversations"|ConversationModel' backend/src` để thấy mọi chỗ
   đọc bảng.
2. Migration đổi tên hoặc cột phải sửa **cùng commit** chuỗi tên trong
   `analysis_repository.py`.
3. Nếu thêm module khác đọc theo tên bảng: bổ sung vào ADR này và vào test
   unit ở trên.
