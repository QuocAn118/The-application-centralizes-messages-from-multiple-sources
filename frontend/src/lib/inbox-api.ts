/**
 * Lời gọi API của module inbox + khoá cache dùng chung.
 *
 * Gom vào một chỗ để GĐ5 (realtime) biết chính xác cần vô hiệu hoá khoá nào
 * khi nhận tín hiệu WS — nếu khoá rải rác trong component thì việc đó rất dễ sót.
 */

import { api } from "./api-client";
import type {
  Conversation,
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
    },
    signal,
  );
}

/** Số tin tải mỗi lần xem hội thoại. Backend chặn trần ở 200. */
export const SO_TIN_MOI_LAN = 100;

/**
 * Chi tiết một hội thoại kèm tin nhắn.
 *
 * Server trả tin theo `created_at` TĂNG DẦN (cũ trước, mới sau) — đúng chiều
 * đọc của khung chat, nên FE giữ nguyên thứ tự.
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
export function traLoiHoiThoai(id: string, text: string): Promise<Message> {
  return api.post<Message>(`/inbox/${id}/reply`, { text });
}
