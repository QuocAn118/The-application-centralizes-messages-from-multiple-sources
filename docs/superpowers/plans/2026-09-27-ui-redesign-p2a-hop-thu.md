# Phần 2a — Hộp thư mới + BE-3/2/1/9 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Hộp thư Neo-Brutalism (danh sách lọc theo người phụ trách, chưa đọc, thời gian chờ, đổi/gỡ người phụ trách, dòng hệ thống) trên 4 thay đổi backend đã duyệt.

**Architecture:** Backend thêm vào module `inbox` (Clean Architecture sẵn có): 2 bảng mới (`conversation_reads`, `conversation_events`), 1 partial index, 3 endpoint, vài trường phản hồi. `assignment_log` (module `assignment`) được ghi qua hook sau-giao-việc do `main.py` nối — không import chéo. Frontend thay ruột 3 cột Hộp thư bằng component design system.

**Tech Stack:** FastAPI, SQLAlchemy async, Alembic, pytest; Next.js 16, React Query v5 (`useInfiniteQuery`), Tailwind v4, vitest.

**Spec:** `docs/superpowers/specs/2026-09-27-ui-redesign-p2a-hop-thu.md`

## Global Constraints

- Mọi migration có `downgrade()`, thử up → down → up.
- Import-linter 16 hợp đồng giữ nguyên; inbox KHÔNG import identity/assignment.
- Không đổi quy tắc cũ: `assign_to_agent` vẫn "không cướp việc"; phạm vi theo vai giữ nguyên.
- `assignment_log` chỉ thêm dòng cho `ASSIGNED`/`REASSIGNED` (giao tay).
- Chỉ desktop; chữ ≥ 12px; không SVG vẽ tay (lucide + simple-icons); quy tắc bóng Phần 1.
- Đo hiệu năng ở DB riêng `omnichat_perf`; chậm thêm > 100 ms → DỪNG báo user.

## Review Focus

1. **Hai người đổi người phụ trách cùng lúc** (Manager A đổi sang B, Admin gỡ cùng lúc) → một trong hai thắng rõ ràng, không lệch `assigned_user_id` với timeline → test use case với trạng thái đã bị đổi trước khi lưu (optimistic: kiểm lại trong transaction).
2. **Tin mới đến khi tab trình duyệt ở nền** → KHÔNG được đánh dấu đã đọc → test hàm quyết định `nenDanhDauDaDoc(dangMo, coFocus)`.
3. **Khách nhắn nhiều tin liên tiếp** → `waiting_since` = tin ĐẦU, không phải tin cuối → test repository.
4. **Người đã bị vô hiệu hoá / chuyển phòng vẫn đang là người phụ trách** → tên vẫn hiện, ô chọn vẫn hiện đúng người hiện tại dù người đó không còn trong danh sách chọn → test FE (tuỳ chọn "người hiện tại" được giữ).
5. **Cuộn liên tục khi danh sách thay đổi giữa hai trang** (tin mới đẩy hội thoại lên đầu) → không trùng dòng → test hàm gộp trang loại trùng theo `conversation_id`.

---

### Task 0: Hạ tầng đo hiệu năng + số nền

**Files:** Create `backend/scripts/perf/gieo_perf.py` (dev), dùng DB `omnichat_perf`.

- [ ] Tạo DB `omnichat_perf` (psycopg `CREATE DATABASE`), `alembic upgrade head` với `DATABASE_URL` trỏ vào đó.
- [ ] Gieo: 3 phòng, 30 nhân viên, 3.000 hội thoại, ~20 tin mỗi hội thoại (xen vào/ra), 20% chưa có người, 10% đóng.
- [ ] Chạy backend `--port 8013` trên DB đó; đo `GET /inbox?limit=25` (Admin, Manager, Staff) 30 lần mỗi vai, lấy p50/p95 → ghi **số nền**.

### Task 1: BE-3 lọc `assignee`

**Files:** Modify `inbox/application/use_cases/list_inbox.py`, `infrastructure/repositories/conversation_repository.py` (`list_for_scope`, `count_for_scope`), `domain/repositories/conversation_repository.py`, `presentation/routers/inbox_router.py`; Test `tests/unit/inbox/test_list_inbox.py`, `tests/integration/test_inbox_repository.py`.

**Interfaces:** Produces `ListInbox.execute(..., assignee: Literal["me","none"] | None = None)`; query `assignee` enum.

- [ ] Test: `me` chỉ trả hội thoại của actor; `none` chỉ chưa ai nhận; kết hợp `status`; Staff dùng `none` vẫn không thấy phòng khác; giá trị lạ 422.
- [ ] Làm; chạy test; commit.

### Task 2: BE-1 chưa đọc + BE-9 thời gian chờ

**Files:** Create migration `xxxx_them_conversation_reads.py`, `infrastructure/models/conversation_read_model.py`, `infrastructure/repositories/read_repository.py`, `application/use_cases/mark_read.py`, `application/use_cases/count_unread.py`; Modify DTO `InboxItem` (+`unread_count`, `waiting_since`), list/detail queries, `reply_to_conversation.py` (ghi đã đọc), router (+`POST /inbox/{id}/read`, `GET /inbox/unread-count`), schemas.

**Interfaces:** `IReadRepository.mark_read(user_id, conversation_id, at)` (upsert `GREATEST`); `InboxItem.unread_count: int`, `InboxItem.waiting_since: datetime | None`.

- [ ] Test repository: không có dòng → đếm mọi tin vào; sau `mark_read` → 0; tin vào mới → 1; `DA_DONG` → 0; `mark_read` lùi thời gian không làm tăng lại; `waiting_since` = tin vào ĐẦU sau tin ra cuối; tin cuối là tin ra → `null`.
- [ ] Test use case: `POST read` người không có quyền xem → 403/404 như GET; trả lời → người trả lời có `unread_count = 0`.
- [ ] Migration có downgrade; thử up/down/up.
- [ ] **Đo lại trên `omnichat_perf`** (Task 0). > 100 ms thêm → DỪNG, báo user.
- [ ] Commit.

### Task 3: BE-2 đổi/gỡ người phụ trách + timeline + tên + realtime

**Files:** Modify `domain/entities/conversation.py` (+`chuyen_nguoi_phu_trach`); Create migration `xxxx_them_conversation_events.py`, `conversation_event_model.py`, `event_repository.py`, `use_cases/change_assignee.py`; Modify `take_conversation.py`, `assign_conversation_to_agent.py` (ghi event), `domain/ports.py` (`AgentInfo.full_name`, `IWorkforceDirectory.get_names`, `IRealtimeNotifier.notify_user`, hook `IPostAssignHook`), `infrastructure/directory/workforce_directory.py`, `infrastructure/realtime/ws_notifier.py` (lưu `user_id`), router (`POST /inbox/{id}/assign-user`), DTO/schema (+`assigned_user_name`, `customer_external_id`, `events`); `src/main.py` (nối hook → `assignment_log`).

- [ ] Test domain: đổi sang người khác trả người cũ; đổi sang chính người đó → lỗi; gỡ khi chưa có ai → lỗi; ngoài `DANG_MO` → lỗi.
- [ ] Test use case: Manager phòng A không đổi được hội thoại phòng B; người nhận khác phòng → 403; người nhận vô hiệu → 404; Staff gọi → 403; thành công ghi event đúng `kind`/from/to; hook được gọi với người MỚI cho ASSIGNED/REASSIGNED, không gọi khi UNASSIGNED.
- [ ] Test Review Focus #1 (đua): hội thoại bị đổi trước khi lưu → lỗi xung đột, không ghi event.
- [ ] Test tích hợp: hook ghi đúng 1 dòng `assignment_log`; `TAKEN` không ghi.
- [ ] Test notifier: tín hiệu riêng chỉ tới kết nối có đúng `user_id`.
- [ ] Migration up/down/up; import-linter; commit.

### Task 4: FE thư viện — kiểu, API, hàm hiển thị

**Files:** Modify `lib/types.ts`, `lib/inbox-api.ts`, `lib/hien-thi.ts`, `lib/use-inbox-socket.ts`; Create `lib/hop-thu.ts` + `lib/hop-thu.test.ts`.

**Interfaces (hop-thu.ts):** `mocTuongDoi(iso, now)`, `phutCho(waitingSince, now) → number | null`, `laChoLau(phut) → boolean` (`NGUONG_CHO_PHUT = 15`), `gopTrang(trang[]) → InboxItem[]` (loại trùng), `dungDongChat(messages, events) → DongChat[]` (vạch ngày + nhóm tin + dòng hệ thống), `nenDanhDauDaDoc(dangMo, coFocus)`, `hienSoChuaDoc(n) → "99+"…`.

- [ ] Test từng hàm (đủ các ca ở Review Focus #2, #3, #5, và vạch ngày qua nửa đêm).
- [ ] Commit.

### Task 5: FE danh sách hội thoại

**Files:** Rewrite `components/danh-sach-inbox.tsx`, `components/dong-hoi-thoai.tsx`.
- [ ] Tab Của tôi / Chưa ai nhận / Tất cả + ô chọn trạng thái + tìm; mặc định theo vai; giữ URL.
- [ ] Dòng 2 tầng, avatar + logo, chưa đọc, huy hiệu cần chú ý, "Chờ N phút".
- [ ] Cuộn liên tục; `TrangThaiTai/Rong/Loi`.
- [ ] tsc/eslint/test; commit.

### Task 6: FE khung chat

**Files:** Rewrite `components/khung-chat.tsx`, `components/bong-bong-tin.tsx`, `components/o-soan-tin.tsx` (giao diện; giữ logic gửi), `components/dialog-phan-phong.tsx` (dùng `HopThoai`).
- [ ] Header + ô chọn người phụ trách (Review Focus #4) + "⋯" Đóng có xác nhận.
- [ ] Vạch ngày, nhóm tin, dòng hệ thống; ô soạn mới + gợi ý phím.
- [ ] Đánh dấu đã đọc khi mở + tin mới có focus.
- [ ] tsc/eslint/test; commit.

### Task 7: FE panel khách, realtime, huy hiệu nav

**Files:** Create `components/panel-khach.tsx`; Modify `app/inbox/layout.tsx`, `components/cau-noi-realtime.tsx`, `components/nav-rail.tsx`.
- [ ] Panel tối giản, thu gọn được (nhớ `localStorage` có try/catch).
- [ ] Tín hiệu `assigned_to_you`/`unassigned_from_you` → làm mới + thông báo `aria-live`.
- [ ] Huy hiệu chưa đọc trên nav.
- [ ] Commit.

### Task 8: Kiểm chứng + ảnh chụp

- [ ] `seed_kiem_chung` → 12 kịch bản cũ; sửa kịch bản inbox cũ nếu hỏng do đổi UI có chủ đích (ghi lý do).
- [ ] Kịch bản mới `ui-p2a.mjs`: tab lọc, chưa đọc về 0 khi mở, đổi/gỡ người phụ trách + dòng hệ thống, Đóng có xác nhận, Enter gửi.
- [ ] Playwright MCP 1440px trước/sau; tự xem ảnh; focus + tương phản.
- [ ] Báo cáo số hiệu năng trước/sau. Dừng trước Phần 2b.
