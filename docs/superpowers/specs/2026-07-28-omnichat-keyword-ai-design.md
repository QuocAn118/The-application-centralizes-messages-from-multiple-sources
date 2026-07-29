# OmniChat Sub-project #2 — Keyword & AI Analysis: Thiết kế

> Nối tiếp [Foundation](2026-07-21-omnichat-foundation-design.md), [Inbox](2026-07-24-omnichat-inbox-design.md), [HRM](2026-07-26-omnichat-hrm-design.md) và [roadmap](2026-07-21-omnichat-roadmap.md). Phạm vi chốt qua brainstorm ngày 2026-07-28.

## 1. Mục tiêu

Cho mỗi phòng ban một danh mục **từ khoá đặc trưng** (Manager quản lý). Khi một khách mới nhắn tới một hội thoại **chưa thuộc phòng nào** (`CHO_PHAN`), dùng **LLM đọc vài tin đầu** để hiểu khách *đang cần gì*, đối chiếu với danh mục từ khoá các phòng, suy ra **phòng phù hợp**, rồi **tự phân hội thoại về phòng đó**. Đồng thời lưu lại nhãn/từ khoá phân tích được để #5 báo cáo nhu cầu khách hàng.

Không thuộc #2: routing nâng cao theo KPI + ca làm + hàng đợi (#3 dùng lại kết quả #2), báo cáo/dashboard (#5), phân tích ảnh/giọng nói. #2 **chừa sẵn** dữ liệu cho #3 (nhãn + phòng đề xuất + độ tin cậy trên hội thoại) và #5 (lịch sử phân tích).

## 2. Ràng buộc kiến trúc quyết định (đọc trước khi thiết kế chi tiết)

**RB-1 — keyword độc lập với identity, và inbox không phụ thuộc keyword.** Module `keyword` mới, song song các module khác, cùng bốn tầng. Tham chiếu User/Department/Conversation/Message **chỉ qua UUID thuần**; không import `identity.domain`, `inbox.domain`. Cần dữ liệu module khác thì gọi qua port do keyword tự định nghĩa; implementation ở infrastructure mới biết identity/inbox tồn tại. `import-linter` thêm contract cấm `keyword.{domain,application,presentation} → identity, inbox`. **Quan trọng: chiều ngược lại cũng cấm — `inbox` KHÔNG được phụ thuộc `keyword`** (giữ #1 nguyên vẹn, đã đóng băng).

**RB-2 — Phân tích chạy SAU khi tin đã lưu, không nhét vào ingest của #1.** `IngestInboundMessage` của #1 không đổi một dòng. Composition root (webhook router) sau khi ingest xong sẽ gọi tiếp use case phân tích của #2 trong **cùng request** nhưng **tách giao dịch/tách lỗi**: phân tích lỗi (kể cả LLM lỗi) **không** làm hỏng việc nhận tin. Tin đã lưu vẫn nguyên; hội thoại chỉ chưa được gợi ý phòng, có thể phân tích lại sau.

**RB-3 — LLM tự đọc hiểu và tự chọn phòng, sau một cổng.** Thay vì khớp chuỗi thủ công (dễ khớp bừa với keyword ngắn tiếng Việt), **LLM tự đọc vài tin đầu và tự chọn phòng phù hợp**, dựa trên danh mục từ khoá của từng phòng được bơm vào prompt. Đặt sau port `IConversationClassifier` (nhận nội dung tin + danh mục keyword các phòng, trả về phòng LLM chọn + độ tin cậy + cụm nhu cầu). Test dùng fake tất định; production dùng adapter Claude. LLM lỗi/timeout/quota → **bỏ qua, ghi log, không ném lên trên**. Không retry ở #2 (ghi nợ).

**RB-4 — Code vẫn GÁC kết quả LLM trước khi tự phân.** LLM chọn phòng nào là gợi ý, không phải lệnh. Use case kiểm: phòng LLM chọn phải **tồn tại và đang hoạt động** (qua `IWorkforceDirectory`), và độ tin cậy **đạt ngưỡng**. Đủ cả hai → tự phân (CHO_PHAN → DANG_MO qua cổng). LLM trả "không rõ" / chọn phòng không tồn tại / tin cậy thấp → **để nguyên CHO_PHAN** cho Manager phân tay (không phân bừa, LLM không "bịa" phòng làm phân sai). Việc đổi trạng thái đi qua cổng `IConversationRouter` (implementation gọi use case `AssignConversationToDepartment` của #1 với actor hệ thống), không để keyword đụng thẳng máy trạng thái inbox.

**RB-5 — Không gọi LLM lặp.** Một hội thoại đã có bản ghi phân tích thì không gọi LLM lại khi có tin mới (trừ khi Manager kích hoạt lại thủ công). Tiết kiệm token; hội thoại tự phân xong chuyển DANG_MO nên vốn không còn được phân tích, guard này chặn nốt trường hợp mơ hồ/lỗi nhận thêm tin.

## 3. Ngôn ngữ miền (domain)

| Khái niệm | Ý nghĩa |
|---|---|
| **Keyword** | Một từ/cụm từ đặc trưng của một phòng ban, do Manager định nghĩa. Thuộc đúng một phòng. Có dạng chuẩn hoá để khớp (bỏ dấu, thường hoá). |
| **KeywordMatch** | Kết quả LLM trích được một cụm nhu cầu từ tin, và cụm đó khớp (hoặc không) với keyword của phòng nào. |
| **ConversationAnalysis** | Bản ghi phân tích một hội thoại: các cụm nhu cầu LLM trích, phòng đề xuất (nếu có), độ tin cậy, đã tự phân hay chưa, thời điểm. Một hội thoại có thể phân tích lại → nhiều bản ghi (giữ lịch sử cho #5). |

### Vòng đời phân tích một hội thoại

```
  [tin đến, hội thoại CHO_PHAN, đủ N tin của khách]
        │
        ▼
  gọi IKeywordExtractor (LLM đọc vài tin đầu)  ──LLM lỗi──► log + bỏ qua (giữ CHO_PHAN)
        │ trả các cụm nhu cầu
        ▼
  khớp cụm nhu cầu ↔ danh mục keyword các phòng
        │
        ├── đúng 1 phòng, đủ tin cậy ──► tự phân về phòng (qua IConversationRouter) → DANG_MO
        │
        └── không khớp / mơ hồ ──► giữ CHO_PHAN, vẫn lưu ConversationAnalysis để Manager tham khảo
```

- Chỉ phân tích hội thoại **đang `CHO_PHAN`** (chưa có phòng). Hội thoại đã thuộc phòng thì không đụng.
- Kích hoạt khi có tin **inbound** mới và hội thoại còn `CHO_PHAN`. Đọc tối đa **N tin đầu của khách** (mặc định 3) — đủ hiểu nhu cầu, không tốn token vô ích.

## 4. Phân quyền (dùng lại RBAC #0)

| Hành động | Admin | Manager | Staff |
|---|---|---|---|
| CRUD keyword của phòng | ✓ (mọi phòng) | ✓ (phòng mình) | ✗ |
| Xem danh sách keyword | tất cả các phòng | phòng mình | ✗ |
| Xem phân tích của hội thoại | tất cả | phòng mình + hội thoại chờ-phân | phòng mình |
| Kích hoạt phân tích lại một hội thoại | ✓ | ✓ (phòng mình / chờ-phân) | ✗ |

Đề nêu rõ: Manager "CRUD danh sách từ khoá của phòng ban"; Admin "xem tất cả từ khoá do các Manager tạo". Quy tắc phạm vi trả ở tầng **use case** như các module trước.

## 5. Cổng (ports) mà domain/application định nghĩa

- `IConversationClassifier` — nhận nội dung vài tin đầu (text thuần) + **danh mục từ khoá của từng phòng**, cho LLM tự đọc hiểu và trả về **phòng LLM chọn** (hoặc "không rõ") + **độ tin cậy** + các **cụm nhu cầu** (cho #5). Implementation: adapter Claude API. Fake tất định cho test. LLM lỗi → ném `ClassifierError`; use case bắt và bỏ qua.
- `IConversationDirectory` — hỏi inbox gián tiếp: "hội thoại X có đang CHO_PHAN không", "lấy N tin inbound đầu của hội thoại X". Không import inbox vào keyword.domain.
- `IDepartmentKeywordSource` — lấy danh mục keyword của tất cả phòng đang hoạt động để khớp (đọc từ chính bảng keyword của #2).
- `IConversationRouter` — tự phân hội thoại về một phòng (implementation gọi use case phân của #1 với actor hệ thống). Đây là chỗ *duy nhất* keyword tác động ngược vào inbox, và đi qua use case chính thống của #1 (giữ máy trạng thái, phân quyền, realtime của #1 nguyên vẹn).
- `IWorkforceDirectory` — kiểm phòng tồn tại/đang hoạt động (cho CRUD keyword và khi tự phân).
- `IClock` — thời gian (dùng chung shared).

## 6. Use cases

### 6.1 Nhóm Keyword (CRUD, Manager/Admin)
- `CreateKeyword`, `UpdateKeyword`, `DeleteKeyword` — Manager phòng mình / Admin. Chuẩn hoá + chống trùng trong phòng.
- `ListKeywords` — theo phạm vi phòng (Manager phòng mình; Admin tất cả).

### 6.2 Nhóm phân tích
- `AnalyzeConversation` — use case lõi: điều kiện (hội thoại CHO_PHAN, đủ tin, chưa phân tích trừ khi `force`), gom danh mục keyword các phòng, gọi `IConversationClassifier` cho LLM tự chọn phòng, **gác** kết quả (phòng tồn tại + đủ tin cậy) rồi quyết định tự phân hay giữ, lưu `ConversationAnalysis`. Bắt mọi lỗi LLM → log + trả kết quả "không phân tích được", không ném.
- `ListConversationAnalyses` / `GetConversationAnalysis` — xem lịch sử/kết quả theo phạm vi quyền.

Webhook router (composition root) sau ingest gọi `AnalyzeConversation` cho hội thoại vừa nhận tin, trong khối try/except riêng (RB-2).

## 7. Mô hình lưu trữ (bảng mới, module keyword)

- `keywords` — id, department_id (UUID thuần), text (nguyên gốc), normalized (dạng khớp), created_at, updated_at. Unique (department_id, normalized).
- `conversation_analyses` — id, conversation_id (UUID thuần), extracted_terms (JSONB: các cụm nhu cầu LLM trả), suggested_department_id (UUID?, null nếu không suy ra), confidence (numeric?), auto_assigned (bool), created_at.

`department_id`/`conversation_id`/`suggested_department_id` là UUID thuần, **không** khoá ngoại sang identity/inbox (giữ module độc lập). Toàn vẹn đảm bảo ở use case qua port.

## 8. Tiêu chí thành công #2

1. Manager tạo/sửa/xoá keyword cho phòng mình; Admin xem keyword mọi phòng; Staff không CRUD được.
2. Khách mới nhắn (hội thoại `CHO_PHAN`) → hệ thống gọi LLM đọc vài tin đầu, trích nhu cầu.
3. Nhu cầu khớp đúng một phòng đủ tin cậy → hội thoại **tự phân** về phòng đó (`DANG_MO`), có bản ghi phân tích.
4. Nhu cầu mơ hồ/không khớp → hội thoại **giữ `CHO_PHAN`**, vẫn có bản ghi phân tích để Manager tham khảo.
5. LLM lỗi/timeout → tin nhắn vẫn nguyên vẹn, nhận tin không bị hỏng; ghi log; hội thoại giữ `CHO_PHAN`.
6. `import-linter`: `keyword` không phụ thuộc `identity`/`inbox`; **`inbox` không phụ thuộc `keyword`**; LLM sau port, đổi provider không đụng use case.

## 9. Giới hạn đã biết (ghi rõ, không giấu)

- **Trích chỉ từ text.** Ảnh/file/giọng nói không phân tích ở #2.
- **Phân tích đồng bộ trong request webhook.** Nếu LLM chậm làm webhook lâu, cần đẩy hàng đợi nền — ghi nợ (chưa có hạ tầng queue ở #0–#4), làm khi thấy chậm thật.
- **Không retry LLM.** Lỗi tạm thời → bỏ qua luôn; phân tích lại thủ công/khi có tin mới. Thêm retry sau nếu cần.
- **Khớp keyword theo danh mục phòng.** Nhu cầu mới chưa có trong danh mục nào sẽ không tự phân được (đúng ý: không phân bừa); các cụm đó vẫn lưu để #5 phát hiện nhu cầu mới.
- **Chi phí/độ trễ LLM.** Mỗi hội thoại mới tốn một lời gọi Claude; giới hạn đọc N tin đầu để kiểm soát. Cân nhắc cache/gộp ở #5.

## 10. Quyết định đã chốt (khép câu hỏi mở)

- **LLM (Claude API) tự đọc hiểu và tự chọn phòng** sau port `IConversationClassifier`, dựa trên danh mục keyword các phòng bơm vào prompt (không khớp chuỗi thủ công — tránh khớp bừa với keyword ngắn tiếng Việt); chạy **sau ingest**, tách lỗi khỏi nhận tin.
- **Danh mục keyword của Manager là ngữ cảnh cho LLM** để chọn phòng; cụm nhu cầu LLM trả được lưu lại (kể cả khi không phân được) cho #5.
- **Code vẫn gác kết quả LLM**: phòng LLM chọn phải tồn tại + đủ tin cậy mới tự phân, qua cổng `IConversationRouter` gọi use case phân của #1 (không đụng thẳng máy trạng thái). Không rõ / phòng không tồn tại / tin cậy thấp → giữ `CHO_PHAN`.
- **Không gọi LLM lặp**: hội thoại đã phân tích thì bỏ qua (trừ khi kích hoạt lại thủ công).
- **LLM lỗi → log + bỏ qua**, tin vẫn nguyên.
- **Độc lập module hai chiều:** keyword ⊥ identity/inbox, và inbox ⊥ keyword. `import-linter` thêm contract tương ứng.

## 11. Bước tiếp theo

Lập kế hoạch triển khai chi tiết cho #2 bằng skill `writing-plans`, chia giai đoạn domain → application → infrastructure (gồm adapter Claude) → presentation + wiring, mỗi giai đoạn review trước khi sang tiếp.
