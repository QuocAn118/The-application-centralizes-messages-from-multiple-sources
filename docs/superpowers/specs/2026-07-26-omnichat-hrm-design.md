# OmniChat Sub-project #4 — HRM: Thiết kế

> Nối tiếp [Foundation](2026-07-21-omnichat-foundation-design.md), [Inbox](2026-07-24-omnichat-inbox-design.md) và [roadmap](2026-07-21-omnichat-roadmap.md). Phạm vi chốt qua brainstorm ngày 2026-07-26.

## 1. Mục tiêu

Cung cấp lớp **quản lý nhân sự vận hành** cho doanh nghiệp: quản lý **ca làm việc và lịch phân ca**, **KPI nhân viên/phòng ban**, và **biểu mẫu đơn từ nội bộ với luồng phê duyệt**. Đây là sub-project được roadmap đưa lên sớm (thứ tự `0 → 1 → 4 → 2 → 3 → 5`) vì Auto-Assignment (#3) cần dữ liệu ca làm và KPI của #4, còn #4 chỉ phụ thuộc #0 nên làm song song #1 được.

Không thuộc #4: routing/auto-assignment (#3), báo cáo đa chiều & dashboard (#5), phân tích keyword (#2). #4 **cung cấp dữ liệu** cho #3 (ai đang trong ca, KPI phòng nào còn dư) và cho #5 (đơn từ, ca, KPI để thống kê), nhưng không tự làm hai việc đó.

## 2. Ràng buộc kiến trúc quyết định (đọc trước khi thiết kế chi tiết)

**RB-1 — hrm độc lập với identity và inbox.** Module `hrm` mới, song song `identity` và `inbox`, cùng bốn tầng. hrm tham chiếu User/Department **chỉ qua UUID thuần**; không import `identity.domain` hay `inbox.*`. Cần biết "user X thuộc phòng nào, phòng có tồn tại không" thì gọi qua port `IWorkforceDirectory` (đã có ở inbox — hrm định nghĩa port riêng của mình cùng hình dạng; **không** dùng chung class, chỉ dùng chung ý tưởng). `import-linter` thêm contract cấm `hrm → identity` và `hrm → inbox`.

**RB-2 — KPI thật nhưng không phá ranh giới module.** Người dùng chốt KPI phải phản ánh **hiệu suất thật từ Inbox** (số hội thoại đã đóng, thời gian phản hồi), không phải con số nhập tay. Nhưng hrm **không được** import inbox. Giải: hrm.application định nghĩa port **`IPerformanceSource`** — "cho tôi số liệu hiệu suất của user/phòng trong khoảng thời gian T". Implementation ở `hrm.infrastructure` (hoặc ở composition root) mới truy vấn dữ liệu inbox. Đây chính là mẫu `IWorkforceDirectory` của #1 áp cho quan hệ hrm→inbox. Trade-off ghi ở mục 10.

**RB-3 — Thời gian là hạng công dân bậc nhất.** Ca làm việc, lịch phân ca, khoảng nghỉ phép đều là bài toán thời gian. Mọi mốc lưu `timestamptz` UTC (nền tảng #0 đã chốt vì lý do này). Chồng lấn ca (overlap) và tính hợp lệ khoảng thời gian là **business rule ở domain**, không phải validation ở router.

**RB-4 — Đơn từ và phê duyệt là máy trạng thái có kiểm toán.** Một đơn từ đi qua các trạng thái rõ ràng; mỗi lần chuyển trạng thái là một sự kiện cần ghi lại (ai duyệt, khi nào, lý do từ chối). Dùng lại `AuditLog` của #0 cho dấu vết hệ thống; bản thân đơn từ giữ lịch sử quyết định của chính nó.

## 3. Ngôn ngữ miền (domain)

| Khái niệm | Ý nghĩa |
|---|---|
| **Shift** (Ca làm việc) | Một mẫu ca: tên + khung giờ (giờ bắt đầu/kết thúc trong ngày). Ví dụ "Ca sáng 08:00–12:00". Thuộc một phòng ban. Là *khuôn*, không phải một buổi làm cụ thể. |
| **ShiftAssignment** (Phân ca) | Gán một `Shift` cho một nhân viên vào một **ngày** cụ thể. Đây là "buổi làm thật": nhân viên A làm Ca sáng ngày 2026-08-01. |
| **KpiTarget** (Mục tiêu KPI) | Chỉ tiêu cho một nhân viên (hoặc phòng ban) trong một **kỳ** (tháng): loại chỉ số + giá trị mục tiêu. Ví dụ "đóng 200 hội thoại trong tháng 8". |
| **KpiMetricType** | Loại chỉ số đo được: `CONVERSATIONS_CLOSED`, `AVG_RESPONSE_MINUTES` (mở rộng được). Giá trị **thực đạt** lấy qua `IPerformanceSource`, không lưu tay. |
| **LeaveRequest / Request** (Đơn từ) | Yêu cầu nội bộ do Staff gửi: nghỉ phép, tăng lương, khác. Có loại, nội dung (lý do text + khoảng thời gian nếu là nghỉ phép), và trạng thái phê duyệt. |
| **RequestType** | Loại đơn cố định: `NGHI_PHEP`, `TANG_LUONG`, `KHAC` (mở rộng được). Chỉ `NGHI_PHEP` bắt buộc có khoảng thời gian. |

### Trạng thái ShiftAssignment

Một buổi phân ca không cần máy trạng thái phức tạp ở #4: nó tồn tại (đã phân) hoặc bị huỷ. Chấm công thực tế (check-in/out) **không** thuộc #4 — ghi nợ ở mục 10. #3 chỉ cần biết "hôm nay ai được phân ca nào" để suy ra ai đang trong giờ làm.

### Trạng thái LeaveRequest

```
  [Staff gửi]
       │
       ▼
   CHO_DUYET ──── Manager duyệt ────► DA_DUYET
       │
       ├───────── Manager từ chối ───► TU_CHOI   (kèm lý do)
       │
       └───────── Staff tự thu hồi ──► DA_HUY   (chỉ khi còn CHO_DUYET)
```

- `CHO_DUYET`: vừa gửi, chờ Manager phòng đó xử lý.
- `DA_DUYET` / `TU_CHOI`: quyết định cuối; **bất biến** (không sửa lại). Từ chối bắt buộc kèm lý do.
- `DA_HUY`: Staff rút đơn khi chưa ai duyệt. Sau khi có quyết định thì không huỷ được.

Đơn đã ở trạng thái cuối là bất biến — muốn thay đổi thì gửi đơn mới. Giữ lịch sử phê duyệt sạch, khớp tinh thần "email/audit không có hai danh tính trùng" của #0.

## 4. Phân quyền (dùng lại RBAC #0)

| Hành động | Admin | Manager | Staff |
|---|---|---|---|
| CRUD Shift (mẫu ca) | ✓ | ✓ (phòng mình) | ✗ |
| Phân ca cho nhân viên | ✓ | ✓ (nhân viên phòng mình) | ✗ |
| Xem lịch phân ca | tất cả | phòng mình | của mình |
| Đặt/sửa mục tiêu KPI | ✓ | ✓ (phòng mình) | ✗ |
| Xem KPI (mục tiêu + thực đạt) | tất cả | phòng mình | của mình |
| Gửi đơn từ | ✓ | ✓ | ✓ |
| Duyệt/từ chối đơn | ✓ (đơn của Manager) | ✓ (đơn Staff phòng mình) | ✗ |
| Xem đơn | tất cả | phòng mình + đơn mình gửi | của mình |
| Thu hồi đơn của chính mình | ✓ | ✓ | ✓ |

Quy tắc "ai xem/duyệt được gì" trả lời ở tầng **use case** (phụ thuộc dữ liệu: đơn/ca này thuộc phòng nào, do ai gửi), đúng như #0 và #1 đã làm. Route guard chỉ chặn role tối thiểu.

**Đơn của Manager duyệt bởi ai:** Manager gửi đơn thì **Admin** duyệt (Manager không tự duyệt đơn của mình, và không có Manager cấp trên trong mô hình phẳng của đề). Đơn của Staff thì Manager phòng đó duyệt.

## 5. Cổng (ports) mà domain/application định nghĩa

- `IWorkforceDirectory` — hỏi identity gián tiếp: "user X thuộc phòng nào", "phòng Y tồn tại/active không", "ai là Manager của phòng Y" (để định tuyến đơn tới người duyệt). Implementation ở infrastructure gọi sang identity; domain hrm không biết identity tồn tại. *Cùng hình dạng port của #1, khai báo lại trong hrm — không import chéo module.*
- `IPerformanceSource` — cung cấp **giá trị KPI thực đạt**: `get_metrics(user_id | department_id, metric_type, period) -> value`. Implementation truy vấn dữ liệu inbox (số hội thoại đóng, thời gian phản hồi). Đổi nguồn (thêm #2/#5) sau không đụng use case KPI.
- `IClock` — thời gian hiện tại (đã có mẫu ở #0/#1); cần để kiểm "ngày phân ca không ở quá khứ", "kỳ KPI".

Không có adapter nền tảng ngoài trong #4 — hrm thuần nội bộ.

## 6. Use cases

### 6.1 Nhóm Shift & phân ca
- `CreateShift`, `UpdateShift`, `DeactivateShift`, `ListShifts` — Manager (phòng mình) / Admin.
- `AssignShift` — gán Shift cho nhân viên vào một ngày; từ chối nếu **chồng ca** (nhân viên đã có ca giao khung giờ trùng ngày đó) hoặc ngày ở quá khứ.
- `CancelShiftAssignment` — huỷ một buổi phân ca.
- `ListShiftAssignments` — lọc theo nhân viên / phòng / khoảng ngày; phạm vi theo quyền.

### 6.2 Nhóm KPI
- `SetKpiTarget` — đặt/cập nhật mục tiêu KPI cho nhân viên hoặc phòng trong một kỳ.
- `ListKpiTargets` — mục tiêu theo phạm vi quyền.
- `GetKpiProgress` — trả **mục tiêu + thực đạt** (thực đạt lấy qua `IPerformanceSource`) + % hoàn thành.

### 6.3 Nhóm đơn từ
- `SubmitRequest` — Staff/Manager gửi đơn; validate theo loại (NGHI_PHEP cần khoảng thời gian hợp lệ).
- `ApproveRequest` / `RejectReject` (RejectRequest, kèm lý do) — người duyệt đúng phạm vi; đơn phải đang `CHO_DUYET`.
- `CancelRequest` — người gửi thu hồi khi còn `CHO_DUYET`.
- `ListRequests` / `GetRequest` — theo phạm vi quyền.

Route guard (tầng 1) chặn role tối thiểu; use case (tầng 2) chặn theo phòng/chủ sở hữu; domain entity (tầng 3) giữ bất biến trạng thái (không duyệt đơn đã quyết, không chồng ca).

## 7. Mô hình lưu trữ (bảng mới, module hrm)

- `shifts` — id, department_id (UUID, tham chiếu identity qua ID), name, start_time (time), end_time (time), is_active, timestamps. `end_time > start_time` (không hỗ trợ ca qua nửa đêm ở #4 — ghi nợ).
- `shift_assignments` — id, shift_id (FK shifts), user_id (UUID thuần), work_date (date), status, timestamps. Unique/kiểm chồng ca xử lý ở use case + ràng buộc DB (xem dưới).
- `kpi_targets` — id, subject_type (`USER`/`DEPARTMENT`), subject_id (UUID thuần), metric_type, period_year, period_month, target_value (numeric), timestamps. Unique (subject_type, subject_id, metric_type, period_year, period_month).
- `requests` — id, requester_id (UUID thuần), department_id (UUID thuần, chụp lại lúc gửi), request_type, reason (text), leave_start (date?), leave_end (date?), status, decided_by (UUID?), decided_at (timestamptz?), decision_reason (text?), created_at, updated_at.

`department_id`/`user_id`/`requester_id`/`subject_id`/`decided_by` là UUID thuần, **không** foreign key sang bảng của identity (giữ độc lập module; toàn vẹn tham chiếu đảm bảo ở use case qua `IWorkforceDirectory`). `shift_assignments.shift_id` **là** FK nội bộ trong module hrm — cho phép vì cùng module.

**Ràng buộc DB quan trọng:**
- `shift_assignments`: index hỗ trợ truy vấn chồng ca theo (user_id, work_date). Bất biến "không chồng ca" đảm bảo chính ở use case (đọc-kiểm-ghi trong một transaction/UoW); ghi nợ nếu cần ràng buộc DB chặt hơn cho race condition (mục 10).
- `kpi_targets`: partial/plain unique index chặn trùng mục tiêu cùng (subject, metric, kỳ).
- `requests.status` lưu VARCHAR + CHECK (không dùng ENUM Postgres — nhất quán #0).

## 8. Tiêu chí thành công #4

1. Manager tạo được mẫu ca cho phòng mình và phân ca cho nhân viên theo ngày; phân ca chồng khung giờ bị từ chối.
2. Nhân viên xem được lịch ca của mình; Manager xem được cả phòng; Admin xem tất cả.
3. Manager đặt được mục tiêu KPI; `GetKpiProgress` trả về mục tiêu **và** giá trị thực đạt lấy từ nguồn hiệu suất (Inbox), kèm % hoàn thành.
4. Staff gửi đơn nghỉ phép/tăng lương; Manager phòng đó duyệt hoặc từ chối (kèm lý do); Staff nhận biết kết quả.
5. Đơn đã duyệt/từ chối không sửa/duyệt lại được; đơn `CHO_DUYET` Staff tự thu hồi được.
6. Manager chỉ thao tác được trong phòng mình; Staff không truy cập endpoint quản trị ca/KPI.
7. `import-linter`: `hrm` không phụ thuộc `identity` lẫn `inbox`; KPI thực đạt vào qua port, không import chéo.

## 9. Realtime & thông báo

Đề bài yêu cầu Staff "nhận thông báo khi yêu cầu được phê duyệt hoặc từ chối". #1 đã có hạ tầng WebSocket tín hiệu. #4 **phát tín hiệu thay đổi đơn từ** qua cùng cơ chế (một port notifier trung lập, giống #1), client lấy chi tiết qua REST. Không nhân đôi hạ tầng WS; nếu tái dùng bộ WS của #1 thì đi qua một port `INotifier` do hrm định nghĩa, wiring ở composition root — không import inbox. Nếu thấy phức tạp, #4 làm tối thiểu: trả trạng thái qua REST polling và ghi nợ realtime (mục 10).

## 10. Giới hạn đã biết (ghi rõ, không giấu)

- **KPI qua port, không realtime tức thời.** `IPerformanceSource` truy vấn theo yêu cầu (khi gọi `GetKpiProgress`), không cache/không stream. Nếu truy vấn Inbox nặng, cân nhắc materialized view hoặc snapshot định kỳ ở #5 — ghi nợ. Trade-off của việc giữ ranh giới module: HRM không thấy trực tiếp bảng Inbox, đổi lại `import-linter` xanh và #5 sau này thay nguồn không đụng use case.
- **Không chấm công thực tế.** #4 chỉ phân ca (kế hoạch), không check-in/check-out. Giờ công thật để iteration sau; #3 dùng lịch phân ca (dự kiến) là đủ để biết ai trong ca.
- **Ca không qua nửa đêm.** `end_time > start_time` trong cùng ngày. Ca đêm bắc cầu hai ngày để sau.
- **Phê duyệt một cấp.** Staff→Manager, Manager→Admin. Không có chuỗi duyệt nhiều bước / uỷ quyền — đề không yêu cầu.
- **Loại đơn cố định + lý do tự do.** Không có form builder động; thêm loại đơn là thêm enum + validate, không phải cấu hình runtime.
- **Chồng ca chặn ở use case.** Nếu cần chống race condition tuyệt đối khi hai Manager phân ca đồng thời, thêm ràng buộc DB (exclusion constraint trên khoảng giờ) — ghi nợ, làm khi thấy cần.
- **KPI chỉ tổng hợp theo user/phòng theo tháng.** Không realtime, không đa chiều — đa chiều là việc của #5 Analytics.

## 11. Quyết định đã chốt (khép câu hỏi mở)

- **Nguồn KPI:** hiệu suất **thật từ Inbox** qua port `IPerformanceSource`, không nhập tay. Mục tiêu (target) do Manager đặt; thực đạt (actual) do hệ thống tính. Giữ ranh giới module bằng port thay vì import inbox.
- **Luồng phê duyệt:** **một cấp**. Đơn Staff → Manager phòng đó; đơn Manager → Admin. Từ chối bắt buộc kèm lý do. Đơn ở trạng thái cuối là bất biến.
- **Biểu mẫu đơn:** **loại cố định** (`NGHI_PHEP`, `TANG_LUONG`, `KHAC`) + trường lý do text; `NGHI_PHEP` thêm khoảng thời gian bắt buộc và hợp lệ (`leave_end >= leave_start`, không ở quá khứ). Không form builder.
- **Độc lập module:** `hrm` không import `identity` hay `inbox`; mọi tham chiếu chéo qua UUID + port. `import-linter` thêm contract tương ứng.

## 12. Bước tiếp theo

Lập kế hoạch triển khai chi tiết cho #4 bằng skill `writing-plans`, chia giai đoạn domain → application → infrastructure → presentation như #0 và #1, mỗi giai đoạn review trước khi sang giai đoạn sau.
