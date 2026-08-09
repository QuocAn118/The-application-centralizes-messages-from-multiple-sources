"use client";

/**
 * Nối tín hiệu WebSocket vào lớp cache (spec §4.3, RB-2).
 *
 * Tín hiệu chỉ nói "hội thoại X vừa đổi" — component này **vô hiệu hoá cache
 * rồi để React Query gọi lại REST**, chứ không lấy gì từ payload WS làm nội
 * dung. Đó là lý do file này không đọc trường nào của tín hiệu ngoài
 * `conversation_id`.
 *
 * Không render gì; đặt trong layout của `/inbox` để sống suốt phiên làm việc.
 */

import { useCallback } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { useAuth } from "@/lib/auth-context";
import { khoaInbox } from "@/lib/inbox-api";
import { useInboxSocket } from "@/lib/use-inbox-socket";
import type { InboxSignal } from "@/lib/types";

export function CauNoiRealtime() {
  const queryClient = useQueryClient();
  const { user } = useAuth();

  const xuLyTinHieu = useCallback(
    (tin_hieu: InboxSignal) => {
      // Danh sách luôn phải làm mới: hội thoại có tin mới sẽ nhảy lên đầu, và
      // đổi trạng thái có thể khiến nó rơi khỏi bộ lọc đang xem.
      void queryClient.invalidateQueries({ queryKey: khoaInbox.all });

      // Chi tiết: chỉ làm mới nếu hội thoại đó đang có trong cache — tránh gọi
      // REST cho hội thoại người dùng không mở.
      const khoa = khoaInbox.detail(tin_hieu.conversation_id);
      if (queryClient.getQueryData(khoa)) {
        void queryClient.invalidateQueries({ queryKey: khoa });
      }
    },
    [queryClient],
  );

  // Chưa đăng nhập thì không có token để mở WS.
  useInboxSocket({ onSignal: xuLyTinHieu, enabled: Boolean(user) });

  return null;
}
