"use client";

/**
 * Khung chat của một hội thoại (`/inbox/[id]`).
 *
 * Các nút Nhận việc / Phân phòng / Đóng là GĐ4.
 */

import { useParams } from "next/navigation";
import { KhungChat } from "@/components/khung-chat";

export default function ChiTietHoiThoaiPage() {
  const params = useParams<{ id: string }>();

  // `key` để đổi hội thoại là dựng lại khung chat: không dùng thì nội dung
  // đang gõ dở của hội thoại cũ sẽ dính sang hội thoại mới.
  return <KhungChat key={params.id} conversationId={params.id} />;
}
