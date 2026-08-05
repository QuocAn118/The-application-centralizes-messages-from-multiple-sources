"use client";

/**
 * Khung chat của một hội thoại (spec §4.2 cột phải).
 *
 * Luồng trả lời theo §4.4: khoá ô → `POST reply` → dùng tin từ response cập
 * nhật cache → mở khoá. Lỗi thì GIỮ nội dung đã gõ (IT-5) và refetch để đồng
 * bộ trạng thái thật khi server báo xung đột (409/422).
 */

import { useEffect, useRef, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { ApiError } from "@/lib/api-client";
import {
  khoaInbox,
  layChiTietHoiThoai,
  traLoiHoiThoai,
} from "@/lib/inbox-api";
import { chuCaiDau, tenKhach } from "@/lib/hien-thi";
import type { Conversation, Message } from "@/lib/types";
import { BadgeKenh, BadgeTrangThai } from "./badges";
import { BongBongTin } from "./bong-bong-tin";
import { OSoanTin } from "./o-soan-tin";

export function KhungChat({ conversationId }: { conversationId: string }) {
  const queryClient = useQueryClient();
  const [loiGui, setLoiGui] = useState<string | null>(null);

  const { data, isPending, isError, error, refetch } = useQuery({
    queryKey: khoaInbox.detail(conversationId),
    queryFn: ({ signal }) => layChiTietHoiThoai(conversationId, undefined, 0, signal),
  });

  const guiTraLoi = useMutation({
    mutationFn: (text: string) => traLoiHoiThoai(conversationId, text),
    onSuccess: (tinMoi: Message) => {
      setLoiGui(null);
      // Dùng thẳng tin từ response thay vì gọi lại API (RB-6): response đã là
      // trạng thái mới nhất của server.
      queryClient.setQueryData<Conversation>(
        khoaInbox.detail(conversationId),
        (cu) =>
          cu ? { ...cu, messages: [...cu.messages, tinMoi] } : cu,
      );
      // Dòng bên trái phải nhảy lên đầu và đổi mốc thời gian.
      void queryClient.invalidateQueries({ queryKey: khoaInbox.all });
    },
    onError: (err: unknown) => {
      if (err instanceof ApiError) {
        setLoiGui(err.message);
        // 409/422 nghĩa là trạng thái FE đang giữ đã cũ (ai đó vừa đóng hội
        // thoại chẳng hạn) — đọc lại để ô soạn khoá/mở cho đúng.
        if (err.isConflict || err.isForbidden) void refetch();
      } else {
        setLoiGui("Không gửi được tin. Kiểm tra kết nối rồi thử lại.");
      }
    },
  });

  if (isPending) {
    return (
      <div className="flex flex-1 items-center justify-center bg-surface">
        <p className="text-sm text-muted">Đang tải hội thoại…</p>
      </div>
    );
  }

  if (isError) {
    const la404 = error instanceof ApiError && error.isForbidden;
    return (
      <div className="flex flex-1 items-center justify-center bg-surface px-6">
        <div className="max-w-sm text-center">
          <p className="text-sm font-medium text-foreground">
            {la404 ? "Không xem được hội thoại này" : "Không tải được hội thoại"}
          </p>
          <p className="mt-1 text-xs text-muted">
            {error instanceof ApiError
              ? error.message
              : "Không kết nối được máy chủ."}
          </p>
          {!la404 && (
            <button
              type="button"
              onClick={() => void refetch()}
              className="mt-4 rounded-lg bg-primary px-3 py-1.5 text-xs font-semibold text-white transition hover:brightness-95"
            >
              Thử lại
            </button>
          )}
        </div>
      </div>
    );
  }

  return (
    <section className="flex min-w-0 flex-1 flex-col bg-surface">
      <HeaderHoiThoai hoiThoai={data} />

      <DanhSachTin messages={data.messages} />

      {loiGui && (
        <p
          role="alert"
          className="mx-4 mb-2 rounded-lg border border-danger-border bg-danger-bg px-3.5 py-2 text-xs text-danger-fg"
        >
          {loiGui}
        </p>
      )}

      <OSoanTin
        status={data.status}
        dangGui={guiTraLoi.isPending}
        onGui={async (text) => {
          // `mutateAsync` ném lại lỗi → OSoanTin không xoá nội dung đã gõ (IT-5).
          await guiTraLoi.mutateAsync(text);
        }}
      />
    </section>
  );
}

function HeaderHoiThoai({ hoiThoai }: { hoiThoai: Conversation }) {
  const ten = tenKhach(hoiThoai.customer_display_name);

  return (
    <header className="flex items-center gap-3 border-b border-border-subtle bg-white px-4 py-3">
      <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-full bg-surface text-sm font-semibold text-muted">
        {chuCaiDau(hoiThoai.customer_display_name)}
      </div>

      <div className="min-w-0 flex-1">
        <div className="flex flex-wrap items-center gap-2">
          <h2 className="truncate text-sm font-semibold text-foreground">{ten}</h2>
          <BadgeKenh platform={hoiThoai.platform} />
          <BadgeTrangThai status={hoiThoai.status} />
        </div>
        <p className="mt-0.5 text-xs text-muted">
          {hoiThoai.department_id ? "Đã phân phòng" : "Chưa phân phòng"}
          {" · "}
          {hoiThoai.assigned_user_id ? "Đang được xử lý" : "Chưa có người xử lý"}
        </p>
      </div>

      {/* Nút Nhận việc / Phân phòng / Đóng là GĐ4. */}
    </header>
  );
}

function DanhSachTin({ messages }: { messages: Message[] }) {
  const cuoiRef = useRef<HTMLDivElement>(null);

  // Chat mở ra phải ở tin mới nhất, và tự trôi xuống khi có tin mới.
  useEffect(() => {
    cuoiRef.current?.scrollIntoView({ block: "end" });
  }, [messages.length]);

  if (messages.length === 0) {
    return (
      <div className="flex flex-1 items-center justify-center px-6">
        <p className="text-xs text-muted">Chưa có tin nhắn nào trong hội thoại này.</p>
      </div>
    );
  }

  return (
    <div className="min-h-0 flex-1 space-y-3 overflow-y-auto px-4 py-4">
      {messages.map((m) => (
        <BongBongTin key={m.id} message={m} />
      ))}
      <div ref={cuoiRef} />
    </div>
  );
}
