# OmniChat #2 Keyword & AI Analysis — Implementation Plan

> **For agentic workers:** dùng subagent-driven-development, thực hiện task-by-task. Steps dùng checkbox (`- [ ]`). Mỗi task xong: test xanh + ruff/format/mypy/import-linter sạch, commit.

**Goal:** Danh mục từ khoá theo phòng (Manager CRUD); LLM đọc vài tin đầu của khách trong hội thoại `CHO_PHAN`, suy nhu cầu, khớp danh mục, **tự phân** hội thoại về phòng phù hợp (qua use case phân của #1). LLM lỗi không làm hỏng nhận tin. Module `keyword` độc lập hai chiều với identity/inbox.

**Spec:** [2026-07-28-omnichat-keyword-ai-design.md](../specs/2026-07-28-omnichat-keyword-ai-design.md)

**Tech Stack:** kế thừa #0–#4 (Python 3.13 · FastAPI · SQLAlchemy 2.0 async · psycopg 3 · PostgreSQL 17 · Alembic · Pydantic v2 · uv · pytest · ruff · mypy · import-linter). **Thêm:** `anthropic` SDK (gọi Claude API cho `IKeywordExtractor`) — chỉ dùng ở tầng infrastructure của keyword.

## Global Constraints

Kế thừa toàn bộ Global Constraints của #0–#4 (event loop Windows, UUID v7 qua `new_id()`, `timestamptz` UTC, tên test tiếng Việt không dấu, mọi lệnh qua `uv run` trong `backend/`, coverage domain+application ≥ 90%). Bổ sung riêng cho #2:

- **Module mới `keyword` độc lập identity VÀ inbox — hai chiều.** `keyword.{domain,application,presentation}` **không import** identity/inbox. VÀ **inbox không import keyword** (giữ #1 đóng băng). `import-linter` thêm: keyword.domain vào contract "Domain..."; keyword.application vào "Application..."; layer keyword một chiều; **forbidden mới** cấm `keyword.{domain,application,presentation} → identity, inbox`; và bổ sung `inbox.*` vào một forbidden cấm `→ keyword` (chiều ngược).
- **Phân tích chạy sau ingest, tách lỗi.** `IngestInboundMessage` của #1 KHÔNG đổi. Webhook router gọi `AnalyzeConversation` trong try/except riêng, sau khi tin đã commit. Lỗi phân tích (gồm LLM) không ảnh hưởng nhận tin.
- **LLM sau port, thất bại nuốt gọn.** `IKeywordExtractor` là port; adapter Claude ở infrastructure. LLM lỗi → use case bắt, log, trả "không phân tích được", không ném lên webhook.
- **Tự phân chỉ khi đúng 1 phòng + đủ tin cậy**, qua `IConversationRouter` (gọi use case `AssignConversationToDepartment` của #1 với actor hệ thống). Mơ hồ → giữ CHO_PHAN.
- **API key Claude là bí mật** — đọc từ `.env` (`ANTHROPIC_API_KEY`), không commit, không log.

## Bản đồ file (module keyword)

| Đường dẫn | Trách nhiệm |
|---|---|
| `src/modules/keyword/domain/entities/keyword.py` | `Keyword` (chuẩn hoá normalized) |
| `src/modules/keyword/domain/entities/conversation_analysis.py` | `ConversationAnalysis` |
| `src/modules/keyword/domain/value_objects/extracted_term.py` | `ExtractedTerm`, `AnalysisOutcome` |
| `src/modules/keyword/domain/repositories/` | `IKeywordRepository`, `IAnalysisRepository` |
| `src/modules/keyword/domain/ports.py` | `IKeywordExtractor`, `IConversationDirectory`, `IConversationRouter`, `IWorkforceDirectory`, `ExtractionResult` |
| `src/modules/keyword/application/actor.py` | `KeywordActor` (trung lập) |
| `src/modules/keyword/application/authorization.py` | Quy tắc phạm vi phòng |
| `src/modules/keyword/application/use_cases/keyword_use_cases.py` | CRUD keyword |
| `src/modules/keyword/application/use_cases/analyze_conversation.py` | Use case lõi |
| `src/modules/keyword/application/use_cases/analysis_read.py` | List/Get phân tích |
| `src/modules/keyword/application/dto/keyword_dto.py` | DTO |
| `src/modules/keyword/infrastructure/models/` | ORM `keywords`, `conversation_analyses` |
| `src/modules/keyword/infrastructure/mappers/` | ORM ↔ domain |
| `src/modules/keyword/infrastructure/repositories/` | Repo implementations |
| `src/modules/keyword/infrastructure/classifier/claude_classifier.py` | Adapter Claude (`IConversationClassifier`) |
| `src/modules/keyword/infrastructure/directory/workforce_directory.py` | `IdentityWorkforceDirectory` (chạm identity) |
| `src/modules/keyword/infrastructure/inbox_bridge/conversation_directory.py` | `InboxConversationDirectory` (đọc hội thoại/tin — chạm inbox) |
| `src/modules/keyword/infrastructure/inbox_bridge/conversation_router.py` | `InboxConversationRouter` (gọi use case phân của #1) |
| `src/modules/keyword/presentation/routers/keyword_router.py` | REST CRUD keyword |
| `src/modules/keyword/presentation/routers/analysis_router.py` | REST xem/kích hoạt phân tích |
| `src/modules/keyword/presentation/schemas/` | Pydantic |
| `src/modules/keyword/presentation/dependencies.py` | DI, get_actor, factory các cầu nối |

## Danh sách Task

Thực hiện tuần tự. Mỗi giai đoạn review trước khi sang giai đoạn sau.

### Giai đoạn 1 — Domain keyword (thuần, không I/O)

| Task | Nội dung | Deliverable |
|---|---|---|
| 1 | `Keyword` (chuẩn hoá normalized: bỏ dấu, thường hoá, trim) + value objects `ExtractedTerm`/`AnalysisOutcome` | Unit test: chuẩn hoá đúng; keyword rỗng bị chặn |
| 2 | `ConversationAnalysis` (cụm nhu cầu + phòng đề xuất? + confidence? + auto_assigned) | Unit test bất biến |
| 3 | Repository interfaces (`IKeywordRepository`, `IAnalysisRepository`) + ports (`IKeywordExtractor`, `IConversationDirectory`, `IConversationRouter`, `IWorkforceDirectory`) + fakes | Fake dùng được; import-linter cấm keyword→identity/inbox + inbox→keyword |

### Giai đoạn 2 — Use case (application, dùng fake)

| Task | Nội dung | Deliverable |
|---|---|---|
| 4 | `KeywordActor` + authorization + CRUD keyword use cases (Create/Update/Delete/List) | Unit test: Manager phòng mình, Admin all, Staff bị từ chối; chống trùng normalized |
| ~~5~~ | ~~keyword_matcher~~ — **BỎ**: LLM tự chọn phòng (review GĐ2), không khớp chuỗi thủ công | — |
| 6 | `AnalyzeConversation` (điều kiện CHO_PHAN + đủ tin + guard chưa-phân-tích; gom danh mục phòng; gọi `IConversationClassifier` cho LLM tự chọn phòng; **gác** phòng tồn tại + đủ tin cậy; tự phân qua router hoặc giữ; lưu analysis; **nuốt lỗi LLM**) | Unit test: tự phân khi LLM chọn phòng hợp lệ đủ tin cậy; giữ CHO_PHAN khi không rõ/tin cậy thấp/**LLM bịa phòng không tồn tại**; guard lặp; LLM ném lỗi → không ném ra |
| 7 | `ListConversationAnalyses` + `GetConversationAnalysis` (phạm vi quyền) | Unit test phạm vi |

### Giai đoạn 3 — Hạ tầng lưu trữ + adapter LLM + cầu nối ✅ XONG

| Task | Nội dung | Deliverable |
|---|---|---|
| 8 ✅ | ORM `keywords` (unique `(department_id, normalized)`) + `conversation_analyses` (JSONB `terms`) + Alembic migration `dff8571b18ef` | Integration: schema + unique chặn trùng trên PostgreSQL thật |
| 9 ✅ | Mappers (`KeywordMapper`, `ConversationAnalysisMapper` — JSONB terms) + repo (`SqlAlchemyKeywordRepository`, `SqlAlchemyAnalysisRepository`) | Integration round-trip + list/count theo scope |
| 10 ✅ | `IdentityWorkforceDirectory` + `InboxConversationDirectory` (chỉ tin **INBOUND** có text — F3) + `InboxConversationRouter` (gọi `AssignConversationToDepartment` của #1 với actor hệ thống ADMIN; nuốt lỗi phân → `False`) | Integration: snapshot CHO_PHAN + tin đầu; router phân được + phân lại trả False |
| 11 ✅ | `ClaudeConversationClassifier` (adapter `anthropic`; client bơm vào để test; prompt gồm N tin + danh mục keyword phòng; parse JSON, cắt `{...}` khỏi ```json; kẹp confidence [0,1]; id sai → None; lỗi → `ClassifierError`) | Unit test với client giả (không ra mạng): parse, kẹp, các nhánh lỗi |

### Giai đoạn 4 — HTTP + wiring + tích hợp webhook ✅ XONG

| Task | Nội dung | Deliverable |
|---|---|---|
| 12 ✅ | `dependencies.py` (get_actor qua directory factory; get_directory), CRUD router (`POST/GET/PATCH/DELETE /keywords`), schemas | e2e: Manager CRUD keyword phòng mình; Staff 403; Manager phòng khác 403 |
| 13 ✅ | Analysis router: `GET /analyses` (phân trang, theo phạm vi), `GET /conversations/{id}/analyses`, `POST /conversations/{id}/analyses` (kích hoạt lại `force=True`, Manager/Admin) | e2e: kích hoạt lại tự phân; Staff 403 |
| 14 ✅ | **Wiring + móc webhook (giải RB webhook):** `_wire_keyword` trong main.py; **hook post-ingest qua `app.state.post_ingest_hooks`** — webhook router (inbox.presentation) chỉ gọi callable, KHÔNG import keyword (import-linter 10 kept giữ inbox⊥keyword). Hook chạy trên **session riêng sau commit**, tra `conversation_id` từ external ids (không đổi hợp đồng #1), nuốt mọi lỗi. Config `ANTHROPIC_API_KEY`/`anthropic_model`; không key → classifier vô hiệu (NOT_ANALYZED). conftest TRUNCATE thêm keyword tables. | e2e: khách nhắn hội thoại CHO_PHAN + keyword + LLM giả chọn phòng → **tự phân** (DANG_MO); LLM giả **lỗi** → tin vẫn vào, giữ CHO_PHAN |

## Ghi chú thực hiện

- **Điểm tích hợp webhook (rủi ro nhất):** `IngestInboundMessage.execute` trả `MessageView | None`, KHÔNG có `conversation_id`. Để `AnalyzeConversation` biết hội thoại nào, chọn một trong: (a) `AnalyzeConversation` nhận `conversation_id` — webhook router phải lấy được nó; (b) thêm `conversation_id` vào `MessageView` (đổi #1 — tránh); (c) `IConversationDirectory` tra hội thoại đang mở theo (channel, customer) như ingest làm. **Ưu tiên (c)** hoặc cho ingest trả thêm id qua một kiểu kết quả riêng của webhook — quyết ở Giai đoạn 4, không đổi hợp đồng công khai của #1 nếu tránh được. Ghi rõ khi làm task 14.
- **Ranh giới ngược inbox⊥keyword:** webhook router thuộc `inbox.presentation` — KHÔNG được import `keyword`. Cách giữ: composition root (main.py) chèn một *hook* vào `app.state` mà webhook router gọi (kiểu `app.state.post_ingest_hooks`), hook do `_wire_keyword` đăng ký. Nếu không khả thi gọn, cân nhắc một router webhook mỏng ở tầng composition. Quyết ở task 14 — đây là chỗ import-linter sẽ bắt nếu làm sai, như Phase 4 của #1.
- **Actor hệ thống khi tự phân:** `InboxConversationRouter` gọi `AssignConversationToDepartment` cần một `InboxActor` quyền phân. Dùng một actor hệ thống vai ADMIN (không thuộc phòng) — ghi rõ đây là hành động tự động của #2, không phải người thật.
- **LLM tất định trong test:** fake `IConversationClassifier` trả kết quả cố định; `ClaudeConversationClassifier` nhận client bơm vào nên unit test dùng client giả (không ra mạng) cho prompt + parse. Test tích hợp Claude thật để cuối, thủ công, không vào CI.
- **Nợ (spec §9):** chỉ text; phân tích đồng bộ trong webhook (nợ queue); không retry LLM; khớp theo danh mục phòng; chi phí LLM mỗi hội thoại mới.
- **Nợ chốt sau review GĐ3:**
  - *(F1)* `InboxConversationDirectory` quét `_MESSAGE_SCAN_LIMIT=20` tin đầu rồi lọc INBOUND-có-text. Nếu khách gửi >20 tin CHỈ-ẢNH trước tin text đầu → snapshot rỗng, giữ CHO_PHAN (an toàn). Cực hiếm với CHO_PHAN (chưa có OUTBOUND). Không sửa; muốn chắc thì thêm truy vấn "N tin INBOUND có text đầu" vào `IMessageRepository` #1.
  - *(F2)* `conversation_analyses.confidence` là `Numeric(4,3)` → làm tròn về 3 chữ số thập phân khi lưu. Gác tự phân so ngưỡng TRƯỚC khi lưu (full precision) nên không ảnh hưởng; #3/#5 đọc lại thấy giá trị đã tròn — đã ghi rõ trong docstring model. Không sửa.
- **Chỗ móc cho #3:** `conversation_analyses.suggested_department_id` + `confidence` + `extracted_terms` chính là dữ liệu #3 (auto-assignment) dùng để tinh chỉnh routing theo KPI/ca làm.

Chi tiết từng task (Files/Interfaces/Steps + code) viết khi bắt đầu từng giai đoạn, theo cách #0–#4 đã làm.
