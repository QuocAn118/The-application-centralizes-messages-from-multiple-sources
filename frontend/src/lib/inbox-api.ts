/**
 * Lời gọi API của module inbox + khoá cache dùng chung.
 *
 * Gom vào một chỗ để GĐ5 (realtime) biết chính xác cần vô hiệu hoá khoá nào
 * khi nhận tín hiệu WS — nếu khoá rải rác trong component thì việc đó rất dễ sót.
 */

import { api } from "./api-client";
import type {
  Conversation,
  Department,
  InboxItem,
  Message,
  PageResponse,
  ConversationStatus,
  CustomerNote,
  MauNhan,
  ReplyTemplate,
  Tag,
  UserResponse,
} from "./types";

/** Số hội thoại mỗi trang. Backend chặn trần ở 100. */
export const KICH_THUOC_TRANG = 25;

export interface ThamSoInbox {
  /** `undefined` = tất cả trạng thái người gọi được phép thấy. */
  status?: ConversationStatus;
  limit: number;
  offset: number;
  /** Tìm theo tên khách; backend bỏ dấu nên gõ không dấu vẫn khớp. */
  q?: string;
  /** "me" = của tôi, "none" = chưa ai nhận; `undefined` = tất cả (BE-3). */
  assignee?: LocNguoiPhuTrach;
  /** Lịch sử hội thoại của một khách (BE-4). */
  customer_id?: string;
}

export type LocNguoiPhuTrach = "me" | "none";

/**
 * Khoá cache của React Query.
 *
 * `inbox.list(...)` phụ thuộc bộ lọc + trang; `inbox.all` là gốc chung để vô
 * hiệu hoá MỌI trang cùng lúc (dùng khi có tin mới, không biết nó nằm trang nào).
 */
export const khoaInbox = {
  all: ["inbox"] as const,
  list: (thamSo: Omit<ThamSoInbox, "offset" | "limit">) => ["inbox", "list", thamSo] as const,
  detail: (id: string) => ["inbox", "detail", id] as const,
  /** Huy hiệu nav — nằm dưới `inbox` nên mọi lần vô hiệu hoá `all` cũng làm mới nó. */
  chuaDoc: ["inbox", "chua-doc"] as const,
  nguoiPhong: (departmentId: string) => ["inbox", "nguoi-phong", departmentId] as const,
  // 2b — panel khách. Nằm dưới `inbox` nên tín hiệu realtime làm mới cùng.
  lichSu: (customerId: string) => ["inbox", "lich-su", customerId] as const,
  ghiChu: (customerId: string) => ["inbox", "ghi-chu", customerId] as const,
  nhanKhach: (customerId: string) => ["inbox", "nhan-khach", customerId] as const,
};

/** Danh mục nhãn / mẫu trả lời: dùng chung, không phụ thuộc hội thoại. */
export const khoaNhan = (kemNgung: boolean) => ["nhan", kemNgung] as const;
export const khoaMau = ["mau-tra-loi"] as const;

/** Danh sách hội thoại. Server đã sắp theo `last_message_at` giảm dần. */
export function layDanhSachInbox(
  thamSo: ThamSoInbox,
  signal?: AbortSignal,
): Promise<PageResponse<InboxItem>> {
  return api.get<PageResponse<InboxItem>>(
    "/inbox",
    {
      status: thamSo.status,
      limit: thamSo.limit,
      offset: thamSo.offset,
      q: thamSo.q,
      assignee: thamSo.assignee,
      customer_id: thamSo.customer_id,
    },
    signal,
  );
}

/**
 * Số tin tải mỗi lần. Backend chặn trần ở 200.
 *
 * Nhỏ để mở hội thoại nhanh; phần cũ hơn tải thêm khi người dùng cuộn lên.
 */
export const SO_TIN_MOI_LAN = 30;

/**
 * Chi tiết một hội thoại kèm tin nhắn.
 *
 * Server trả `limit` tin MỚI NHẤT, xếp theo `created_at` tăng dần (cũ trước,
 * mới sau) — đúng chiều đọc của khung chat, nên FE giữ nguyên thứ tự. Hội thoại
 * dài hơn `limit` thì phần cũ hơn chưa tải (cuộn-để-tải-thêm là nợ sau).
 */
export function layChiTietHoiThoai(
  id: string,
  limit = SO_TIN_MOI_LAN,
  offset = 0,
  signal?: AbortSignal,
): Promise<Conversation> {
  return api.get<Conversation>(`/inbox/${id}`, { limit, offset }, signal);
}

/**
 * Gửi tin trả lời.
 *
 * Backend chỉ chấp nhận khi hội thoại `DANG_MO`; ngược lại trả 4xx và FE phải
 * đồng bộ lại trạng thái (RB-5, §7).
 */
export function traLoiHoiThoai(
  id: string,
  text: string,
  tep: File[] = [],
): Promise<Message> {
  // Không có tệp thì giữ nguyên JSON — nhẹ hơn và là đường đi đã chạy ổn định.
  if (tep.length === 0) {
    return api.post<Message>(`/inbox/${id}/reply`, { text });
  }

  const form = new FormData();
  if (text) form.append("text", text);
  for (const t of tep) form.append("files", t);
  return api.postForm<Message>(`/inbox/${id}/reply`, form);
}

// ---------------------------------------------------------------------------
// Hành động trên hội thoại (GĐ4)
//
// Cả ba trả về `Conversation` đã cập nhật — dùng thẳng response để làm mới
// cache thay vì gọi lại API (RB-6).
// ---------------------------------------------------------------------------

/** Nhận việc: gán chính mình. Backend đòi `DANG_MO` và chưa có ai nhận. */
export function nhanViec(id: string): Promise<Conversation> {
  return api.post<Conversation>(`/inbox/${id}/take`);
}

/** Đóng hội thoại. Backend đòi `DANG_MO`. */
export function dongHoiThoai(id: string): Promise<Conversation> {
  return api.post<Conversation>(`/inbox/${id}/close`);
}

/**
 * Phân hội thoại về một phòng. Backend đòi `CHO_PHAN` + vai Manager/Admin;
 * Manager còn bị giới hạn chỉ phân về phòng của chính mình.
 */
export function phanPhong(id: string, departmentId: string): Promise<Conversation> {
  return api.post<Conversation>(`/inbox/${id}/assign`, {
    department_id: departmentId,
  });
}

/**
 * Giao / đổi / gỡ (`userId = null`) người phụ trách (BE-2). Chỉ Manager (phòng
 * mình) / Admin; người được giao phải đang hoạt động và cùng phòng hội thoại.
 */
export function giaoNguoiPhuTrach(id: string, userId: string | null): Promise<Conversation> {
  return api.post<Conversation>(`/inbox/${id}/assign-user`, { user_id: userId });
}

/** Đánh dấu đã đọc tới bây giờ (BE-1). 204. */
export function danhDauDaDoc(id: string): Promise<void> {
  return api.post<void>(`/inbox/${id}/read`);
}

/** Số hội thoại có tin chưa đọc trong phạm vi người gọi — huy hiệu nav. */
export function layDemChuaDoc(signal?: AbortSignal): Promise<{ conversations: number }> {
  return api.get<{ conversations: number }>("/inbox/unread-count", undefined, signal);
}

/**
 * Người đang hoạt động của một phòng — cho ô chọn người phụ trách. Chỉ Manager/
 * Admin gọi (Staff bị 403 ở `/users`, và cũng không có ô chọn).
 */
export function layNguoiCuaPhong(
  departmentId: string,
  signal?: AbortSignal,
): Promise<PageResponse<UserResponse>> {
  return api.get<PageResponse<UserResponse>>(
    "/users",
    { department_id: departmentId, is_active: "true", limit: 100 },
    signal,
  );
}

/** Danh sách phòng ban đang hoạt động, cho dialog phân phòng. */
export function layPhongBanHoatDong(
  signal?: AbortSignal,
): Promise<PageResponse<Department>> {
  return api.get<PageResponse<Department>>(
    "/departments",
    { is_active: "true", limit: 100 },
    signal,
  );
}

export const khoaPhongBan = ["departments", "active"] as const;

// ---------------------------------------------------------------------------
// Panel khách + ô soạn (redesign 2b)
// ---------------------------------------------------------------------------

/** Các hội thoại của một khách trong phạm vi người gọi (BE-4). Khách gắn theo kênh. */
export function layLichSuKhach(
  customerId: string,
  signal?: AbortSignal,
): Promise<PageResponse<InboxItem>> {
  return layDanhSachInbox({ customer_id: customerId, limit: 20, offset: 0 }, signal);
}

/** Ghi chú của phòng mình (Admin: mọi phòng), mới trước (BE-5). */
export function layGhiChu(customerId: string, signal?: AbortSignal): Promise<CustomerNote[]> {
  return api.get<CustomerNote[]>(`/customers/${customerId}/notes`, undefined, signal);
}

export function vietGhiChu(customerId: string, body: string): Promise<CustomerNote> {
  return api.post<CustomerNote>(`/customers/${customerId}/notes`, { body });
}

/** Chỉ người viết hoặc Admin. 204. */
export function xoaGhiChu(noteId: string): Promise<void> {
  return api.delete<void>(`/notes/${noteId}`);
}

/** `kemNgung` chỉ có tác dụng với Manager/Admin (BE-6). */
export function layNhan(kemNgung = false, signal?: AbortSignal): Promise<Tag[]> {
  return api.get<Tag[]>("/tags", kemNgung ? { include_inactive: "true" } : undefined, signal);
}

export function taoNhan(name: string, color: MauNhan): Promise<Tag> {
  return api.post<Tag>("/tags", { name, color });
}

export function suaNhan(
  tagId: string,
  thayDoi: { name?: string; color?: MauNhan; is_active?: boolean },
): Promise<Tag> {
  return api.patch<Tag>(`/tags/${tagId}`, thayDoi);
}

export function layNhanKhach(customerId: string, signal?: AbortSignal): Promise<Tag[]> {
  return api.get<Tag[]>(`/customers/${customerId}/tags`, undefined, signal);
}

/** Thay TOÀN BỘ nhãn của khách. */
export function ganNhanKhach(customerId: string, tagIds: string[]): Promise<Tag[]> {
  return api.put<Tag[]>(`/customers/${customerId}/tags`, { tag_ids: tagIds });
}

/** Mẫu dùng chung + phòng mình (Admin: tất cả) (BE-7). */
export function layMau(signal?: AbortSignal): Promise<ReplyTemplate[]> {
  return api.get<ReplyTemplate[]>("/reply-templates", undefined, signal);
}

export function taoMau(duLieu: {
  department_id: string | null;
  title: string;
  body: string;
}): Promise<ReplyTemplate> {
  return api.post<ReplyTemplate>("/reply-templates", duLieu);
}

export function suaMau(
  templateId: string,
  thayDoi: { title?: string; body?: string },
): Promise<ReplyTemplate> {
  return api.patch<ReplyTemplate>(`/reply-templates/${templateId}`, thayDoi);
}

export function xoaMau(templateId: string): Promise<void> {
  return api.delete<void>(`/reply-templates/${templateId}`);
}
