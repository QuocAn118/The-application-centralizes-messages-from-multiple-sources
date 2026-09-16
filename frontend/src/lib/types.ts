/**
 * Kiểu dữ liệu khớp schema backend (`/api/v1`).
 *
 * Đây là NGUỒN TYPE DUY NHẤT cho phản hồi API — mọi màn dùng lại từ đây.
 * Nếu backend đổi schema mà file này không đổi theo, đó là lỗi tích hợp: sửa
 * ngay thay vì ép kiểu ở nơi gọi.
 *
 * Đối chiếu:
 * - identity/presentation/schemas/auth_schemas.py
 * - inbox/presentation/schemas/inbox_schemas.py, common.py
 */

// ---------------------------------------------------------------------------
// Miền (khớp enum backend — dùng union chuỗi để so sánh trực tiếp giá trị JSON)
// ---------------------------------------------------------------------------

/** Vai trò người dùng. Quyết định nút hành động nào hiển thị (spec §3). */
export type Role = "STAFF" | "MANAGER" | "ADMIN";

/**
 * Kênh tin nhắn.
 *
 * `TELEGRAM` phục vụ test/demo nội bộ (thêm 2026-09-14), không thuộc phạm vi
 * đề bài gốc — nhưng vẫn hiện trong inbox như mọi kênh khác, nên mọi bảng tra
 * theo `Platform` phải phủ nó.
 */
export type Platform = "ZALO" | "FACEBOOK" | "INSTAGRAM" | "TELEGRAM";

/**
 * Trạng thái hội thoại.
 * - `CHO_PHAN`: chờ phân phòng — chỉ Manager/Admin thấy.
 * - `DANG_MO`: đang mở — trả lời được (điều kiện duy nhất cho reply, RB-5).
 * - `DA_DONG`: đã đóng.
 */
export type ConversationStatus = "CHO_PHAN" | "DANG_MO" | "DA_DONG";

/** Chiều tin nhắn: khách gửi vào hay nhân viên gửi ra. */
export type MessageDirection = "INBOUND" | "OUTBOUND";

// ---------------------------------------------------------------------------
// Auth
// ---------------------------------------------------------------------------

/**
 * Phản hồi của `/auth/login` và `/auth/refresh`.
 *
 * `expires_in` tính bằng GIÂY (không phải mốc thời gian tuyệt đối).
 */
export interface TokenResponse {
  access_token: string;
  refresh_token: string;
  token_type: string;
  expires_in: number;
  /** Nếu true, người dùng phải đổi mật khẩu trước khi làm việc. */
  must_change_password: boolean;
}

/** Người đang đăng nhập — `/auth/me`. Cố ý không có `password_hash`. */
export interface UserResponse {
  id: string;
  email: string;
  full_name: string;
  phone: string | null;
  role: Role;
  department_id: string | null;
  is_active: boolean;
  must_change_password: boolean;
  last_login_at: string | null;
  created_at: string;
}

// ---------------------------------------------------------------------------
// Inbox
// ---------------------------------------------------------------------------

/**
 * Tệp đính kèm.
 *
 * `url` là liên kết đã ký, hết hạn sau ít phút — dùng thẳng trong `<img>`.
 * `stored_path` là đường dẫn nội bộ của backend, giữ để truy vết; **không dựng
 * URL từ nó**. `url` có thể `null` với phản hồi cũ hoặc endpoint chưa cấp chữ ký.
 */
export interface Attachment {
  id: string;
  kind: string;
  stored_path: string;
  content_type: string | null;
  size: number | null;
  url: string | null;
}

export interface Message {
  id: string;
  direction: MessageDirection;
  text: string | null;
  created_at: string;
  sender_user_id: string | null;
  attachments: Attachment[];
}

/** Một dòng trong danh sách inbox (không kèm tin nhắn). */
export interface InboxItem {
  conversation_id: string;
  channel_id: string;
  platform: Platform;
  customer_id: string;
  customer_display_name: string | null;
  status: ConversationStatus;
  department_id: string | null;
  assigned_user_id: string | null;
  last_message_at: string;
  /** Trích ngắn tin cuối; `null` khi chưa có tin hoặc tin cuối chỉ có ảnh. */
  last_message_preview?: string | null;
}

/** Chi tiết hội thoại — như `InboxItem` nhưng kèm danh sách tin. */
export interface Conversation extends InboxItem {
  messages: Message[];
}

/** Một trang kết quả. */
export interface PageResponse<T> {
  items: T[];
  total: number;
  limit: number;
  offset: number;
}

/** Phòng ban — dùng ở dialog phân phòng (`GET /departments`). */
export interface Department {
  id: string;
  name: string;
  description: string | null;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

// ---------------------------------------------------------------------------
// Realtime (RB-2: WS chỉ đẩy TÍN HIỆU, không đẩy nội dung)
// ---------------------------------------------------------------------------

export type InboxChange = "new_message" | "status_changed";

/**
 * Tín hiệu từ `/ws/inbox`.
 *
 * Cố ý KHÔNG chứa nội dung tin: nhận tín hiệu rồi gọi lại REST để lấy dữ liệu
 * (server lọc theo phạm vi quyền ở đó). Không bao giờ render thẳng payload này.
 */
export interface InboxSignal {
  conversation_id: string;
  change: InboxChange;
  department_id: string | null;
}

// ---------------------------------------------------------------------------
// Lỗi
// ---------------------------------------------------------------------------

/** Thân lỗi chuẩn của backend (xem `main.py`). */
export interface ApiErrorBody {
  error: {
    code: string;
    message: string;
    details: unknown;
  };
  request_id: string | null;
}

// ---------------------------------------------------------------------------
// Quản trị (#F2)
// ---------------------------------------------------------------------------

/**
 * Hành động được ghi nhật ký — khớp `AuditAction` ở
 * `identity/domain/entities/audit_log.py`.
 *
 * Giá trị dạng `<đối tượng>.<hành động>` nên lọc theo tiền tố được.
 */
export type AuditAction =
  | "user.created"
  | "user.updated"
  | "user.deactivated"
  | "user.reactivated"
  | "user.role_changed"
  | "user.department_changed"
  | "user.password_reset"
  | "user.password_changed"
  | "department.created"
  | "department.updated"
  | "department.deactivated"
  | "auth.login_succeeded"
  | "auth.login_failed"
  | "auth.logout"
  | "auth.token_reuse_detected";

/** Một dòng nhật ký (`GET /audit-logs`). Chỉ đọc — backend không cho sửa/xoá. */
export interface AuditLogEntry {
  id: string;
  action: AuditAction;
  actor_id: string | null;
  resource_type: string;
  resource_id: string | null;
  changes: unknown;
  ip_address: string | null;
  created_at: string;
}

/** Kênh đã kết nối (`GET /channels`). KHÔNG bao giờ chứa credential. */
export interface Channel {
  id: string;
  platform: Platform;
  external_channel_id: string;
  name: string;
  department_id: string | null;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

/** Tham số lọc danh sách người dùng (`GET /users`). */
export interface ThamSoNguoiDung {
  search?: string;
  role?: Role;
  /** Manager gửi cũng vô ích: backend ép về phòng của chính họ. */
  department_id?: string;
  is_active?: boolean;
  limit: number;
  offset: number;
}
