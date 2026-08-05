"use client";

/**
 * Ô soạn tin trả lời (spec §4.2 footer, RB-5).
 *
 * Hai bất biến phải giữ:
 * - **RB-5/IT-2:** chỉ gõ được khi hội thoại `DANG_MO`; ngược lại khoá ô và nói
 *   rõ vì sao, thay vì để người dùng gõ xong mới báo lỗi.
 * - **IT-5:** gửi lỗi thì GIỮ NGUYÊN nội dung đã gõ. Xoá nội dung chỉ sau khi
 *   server xác nhận — mất một đoạn vừa soạn là hỏng việc thật sự.
 */

import { useEffect, useRef, useState } from "react";
import type { ConversationStatus } from "@/lib/types";

/** Giới hạn của `ReplyRequest` phía backend. */
export const DAI_TOI_DA = 8000;

/**
 * Vì sao ô bị khoá — `null` nghĩa là gõ được.
 *
 * Chỉ xét TRẠNG THÁI, không xét người đang xử lý: use case `ReplyToConversation`
 * của backend chỉ đòi đúng phòng + `DANG_MO`, không đòi người gọi phải là
 * `assigned_user_id`. Khoá thêm theo người xử lý sẽ chặn nhầm Manager và đồng
 * nghiệp cùng phòng vốn được phép trả lời.
 */
export function lyDoKhoa(status: ConversationStatus): string | null {
  if (status === "DANG_MO") return null;
  if (status === "CHO_PHAN") {
    return "Hội thoại chưa được phân phòng — hãy phân phòng hoặc nhận việc để trả lời.";
  }
  return "Hội thoại đã đóng — không thể gửi tin mới.";
}

export function OSoanTin({
  status,
  dangGui,
  onGui,
}: {
  status: ConversationStatus;
  dangGui: boolean;
  onGui: (text: string) => Promise<void>;
}) {
  const [noiDung, setNoiDung] = useState("");
  const oRef = useRef<HTMLTextAreaElement>(null);
  const khoa = lyDoKhoa(status);
  const trong = noiDung.trim().length === 0;

  // Chiều cao ô co giãn theo nội dung, chặn trần để không nuốt hết khung chat.
  useEffect(() => {
    const o = oRef.current;
    if (!o) return;
    o.style.height = "auto";
    o.style.height = `${Math.min(o.scrollHeight, 160)}px`;
  }, [noiDung]);

  async function gui() {
    if (khoa || trong || dangGui) return;
    const text = noiDung.trim();
    await onGui(text);
    // Chỉ xoá khi onGui KHÔNG ném lỗi — người gọi ném lại nếu server từ chối,
    // nhờ vậy nội dung vừa gõ còn nguyên để thử lại (IT-5).
    setNoiDung("");
  }

  function xuLyPhim(e: React.KeyboardEvent<HTMLTextAreaElement>) {
    // Enter gửi, Shift+Enter xuống dòng — thói quen của mọi ứng dụng chat.
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      void gui();
    }
  }

  if (khoa) {
    return (
      <div className="border-t border-border-subtle bg-white px-4 py-3">
        <p className="mb-2 flex items-center gap-1.5 text-xs text-muted">
          <IconThongTin />
          {khoa}
        </p>
        <div className="flex gap-2">
          <div className="flex-1 cursor-not-allowed rounded-lg bg-da-dong-bg px-3.5 py-2.5 text-sm text-muted-soft">
            Không thể nhập
          </div>
          <button
            type="button"
            disabled
            className="cursor-not-allowed rounded-lg bg-da-dong-bg px-4 text-sm font-semibold text-muted-soft"
          >
            Gửi
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="border-t border-border-subtle bg-white px-4 py-3">
      <div className="flex items-end gap-2">
        <span
          title="Gửi kèm ảnh sẽ có ở phiên bản sau"
          className="mb-1.5 cursor-not-allowed text-muted-soft/50"
          aria-hidden
        >
          <IconGhim />
        </span>

        <textarea
          ref={oRef}
          rows={1}
          value={noiDung}
          maxLength={DAI_TOI_DA}
          disabled={dangGui}
          onChange={(e) => setNoiDung(e.target.value)}
          onKeyDown={xuLyPhim}
          placeholder="Nhập nội dung trả lời…"
          aria-label="Nội dung trả lời"
          className="flex-1 resize-none rounded-lg border border-border-subtle px-3.5 py-2.5 text-sm outline-none transition focus:border-primary focus:ring-2 focus:ring-primary/20 disabled:bg-surface"
        />

        <button
          type="button"
          onClick={() => void gui()}
          disabled={trong || dangGui}
          className="mb-0.5 rounded-lg bg-primary px-4 py-2.5 text-sm font-semibold text-white transition hover:brightness-95 disabled:cursor-not-allowed disabled:opacity-50"
        >
          {dangGui ? "Đang gửi…" : "Gửi"}
        </button>
      </div>

      {noiDung.length > DAI_TOI_DA - 500 && (
        <p className="mt-1 text-right text-[11px] text-muted-soft">
          {noiDung.length}/{DAI_TOI_DA}
        </p>
      )}
    </div>
  );
}

function IconThongTin() {
  return (
    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" aria-hidden>
      <circle cx="12" cy="12" r="10" />
      <path d="M12 16v-4M12 8h.01" />
    </svg>
  );
}

function IconGhim() {
  return (
    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" aria-hidden>
      <path d="M21.44 11.05l-9.19 9.19a6 6 0 0 1-8.49-8.49l9.19-9.19a4 4 0 0 1 5.66 5.66l-9.2 9.19a2 2 0 0 1-2.83-2.83l8.49-8.48" />
    </svg>
  );
}
