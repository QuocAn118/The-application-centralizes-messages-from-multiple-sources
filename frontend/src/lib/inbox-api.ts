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
}

/**
 * Khoá cache của React Query.
 *
 * `inbox.list(...)` phụ thuộc bộ lọc + trang; `inbox.all` là gốc chung để vô
 * hiệu hoá MỌI trang cùng lúc (dùng khi có tin mới, không biết nó nằm trang nào).
 */
export const khoaInbox = {
  all: ["inbox"] as const,
  list: (thamSo: ThamSoInbox) => ["inbox", "list", thamSo] as const,
  detail: (id: string) => ["inbox", "detail", id] as const,
};

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
