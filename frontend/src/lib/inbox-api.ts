/**
 * Lời gọi API của module inbox + khoá cache dùng chung.
 *
 * Gom vào một chỗ để GĐ5 (realtime) biết chính xác cần vô hiệu hoá khoá nào
 * khi nhận tín hiệu WS — nếu khoá rải rác trong component thì việc đó rất dễ sót.
 */

import { api } from "./api-client";
import type { Conversation, InboxItem, PageResponse, ConversationStatus } from "./types";

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

/** Chi tiết một hội thoại kèm tin nhắn (dùng ở GĐ3). */
export function layChiTietHoiThoai(
  id: string,
  limit = 50,
  offset = 0,
  signal?: AbortSignal,
): Promise<Conversation> {
  return api.get<Conversation>(`/inbox/${id}`, { limit, offset }, signal);
}
