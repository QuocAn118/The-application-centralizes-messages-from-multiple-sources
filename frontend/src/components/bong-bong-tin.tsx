/**
 * Một bong bóng tin trong khung chat (mockup Stitch).
 *
 * INBOUND (khách) canh trái, nền trắng viền xám; OUTBOUND (nhân viên) canh
 * phải, nền xanh chữ trắng.
 */

import { mocDayDu, mocNgan } from "@/lib/hien-thi";
import type { Message } from "@/lib/types";

export function BongBongTin({ message }: { message: Message }) {
  const laKhach = message.direction === "INBOUND";

  return (
    <div className={`flex flex-col ${laKhach ? "items-start" : "items-end"}`}>
      <div
        className={`max-w-[min(560px,75%)] rounded-lg px-3.5 py-2.5 text-sm ${
          laKhach
            ? "border border-border-subtle bg-white text-foreground"
            : "bg-primary text-white"
        }`}
      >
        {message.text && (
          <p className="whitespace-pre-wrap break-words">{message.text}</p>
        )}

        {message.attachments.map((dinhKem) => (
          <OAnhTam key={dinhKem.id} laKhach={laKhach} />
        ))}

        {/* Tin không có cả text lẫn đính kèm gần như không xảy ra, nhưng nếu
            có thì phải hiện gì đó — bong bóng rỗng trông như lỗi giao diện. */}
        {!message.text && message.attachments.length === 0 && (
          <p className="italic opacity-70">(tin không có nội dung)</p>
        )}
      </div>

      <time
        dateTime={message.created_at}
        title={mocDayDu(message.created_at)}
        className="mt-1 px-1 text-[11px] text-muted-soft"
      >
        {mocNgan(message.created_at)}
      </time>
    </div>
  );
}

/**
 * Chỗ giữ cho tệp đính kèm.
 *
 * Backend trả `stored_path` nhưng CHƯA có route phục vụ ảnh (nợ spec §9b), nên
 * không thể dựng URL hiển thị. Vẽ ô xám thay vì `<img>` hỏng — người dùng biết
 * có ảnh và biết là chưa xem được, thay vì thấy icon ảnh vỡ.
 */
function OAnhTam({ laKhach }: { laKhach: boolean }) {
  return (
    <div
      className={`mt-2 flex items-center gap-2 rounded-md px-3 py-2 text-xs ${
        laKhach ? "bg-surface text-muted" : "bg-white/15 text-white/90"
      }`}
    >
      <svg
        width="16"
        height="16"
        viewBox="0 0 24 24"
        fill="none"
        stroke="currentColor"
        strokeWidth="2"
        aria-hidden
      >
        <rect x="3" y="3" width="18" height="18" rx="2" />
        <circle cx="8.5" cy="8.5" r="1.5" />
        <path d="m21 15-5-5L5 21" />
      </svg>
      [ảnh đính kèm]
    </div>
  );
}
