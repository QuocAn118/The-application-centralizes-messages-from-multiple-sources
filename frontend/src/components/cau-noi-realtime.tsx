"use client";

/**
 * Nối tín hiệu WebSocket vào lớp cache (spec §4.3, RB-2).
 *
 * Tín hiệu chỉ nói "hội thoại X vừa đổi" — component này **vô hiệu hoá cache
 * rồi để React Query gọi lại REST**, chứ không lấy gì từ payload WS làm nội
 * dung. Riêng hai tín hiệu gửi RIÊNG (BE-2) thì hiện thêm thông báo ngắn trong
 * vùng `aria-live` — người dùng cần biết mình vừa được giao / bị gỡ việc.
 *
 * Đặt trong layout `/inbox` để sống suốt phiên làm việc.
 */

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import { useQueryClient } from "@tanstack/react-query";
import { useAuth } from "@/lib/auth-context";
import { khoaInbox } from "@/lib/inbox-api";
import { useInboxSocket } from "@/lib/use-inbox-socket";
import type { InboxSignal } from "@/lib/types";

const THOI_GIAN_HIEN_MS = 6_000;

export function CauNoiRealtime() {
  const queryClient = useQueryClient();
  const { user } = useAuth();
  const [thongBao, setThongBao] = useState<{ chu: string; id: string } | null>(null);

  const xuLyTinHieu = useCallback(
    (tin_hieu: InboxSignal) => {
      // Danh sách + huy hiệu luôn làm mới: hội thoại có tin mới nhảy lên đầu, đổi
      // trạng thái có thể rơi khỏi bộ lọc đang xem.
      void queryClient.invalidateQueries({ queryKey: ["inbox", "list"] });
      void queryClient.invalidateQueries({ queryKey: khoaInbox.chuaDoc });

      // Chi tiết: chỉ khi hội thoại đó đang trong cache (người dùng đã mở).
      const khoa = khoaInbox.detail(tin_hieu.conversation_id);
      if (queryClient.getQueryData(khoa)) void queryClient.invalidateQueries({ queryKey: khoa });

      if (tin_hieu.change === "assigned_to_you") {
        setThongBao({ chu: "Bạn vừa được giao một hội thoại.", id: tin_hieu.conversation_id });
      } else if (tin_hieu.change === "unassigned_from_you") {
        setThongBao({ chu: "Bạn không còn phụ trách một hội thoại.", id: tin_hieu.conversation_id });
      }
    },
    [queryClient],
  );

  useEffect(() => {
    if (!thongBao) return;
    const hen = setTimeout(() => setThongBao(null), THOI_GIAN_HIEN_MS);
    return () => clearTimeout(hen);
  }, [thongBao]);

  // Chưa đăng nhập thì không có token để mở WS.
  useInboxSocket({ onSignal: xuLyTinHieu, enabled: Boolean(user) });

  // Vùng live luôn có mặt (rỗng) để trình đọc màn hình đọc được nội dung chèn vào.
  return (
    <div aria-live="polite" className="pointer-events-none fixed bottom-5 left-1/2 z-50 -translate-x-1/2">
      {thongBao && (
        <p className="pointer-events-auto flex items-center gap-3 rounded-nb border-2 border-ink bg-accent px-4 py-2.5 text-sm font-bold text-ink shadow-nb">
          {thongBao.chu}
          <Link href={`/inbox/${thongBao.id}`} className="underline underline-offset-2">
            Mở
          </Link>
        </p>
      )}
    </div>
  );
}
