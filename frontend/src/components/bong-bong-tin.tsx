"use client";

/**
 * Một bong bóng tin trong khung chat (mockup Stitch).
 *
 * INBOUND (khách) canh trái, nền trắng viền xám; OUTBOUND (nhân viên) canh
 * phải, nền xanh chữ trắng.
 */

import { useState } from "react";
import { API_BASE_URL } from "@/lib/api-client";
import { mocDayDu, mocNgan } from "@/lib/hien-thi";
import type { Attachment, Message } from "@/lib/types";

/**
 * Ghép URL đính kèm thành đường dẫn tuyệt đối tới backend.
 *
 * Backend trả đường dẫn tương đối (`/api/v1/...`) vì nó không biết mình đứng
 * sau proxy hay tên miền nào — đoán origin ở đó sẽ sai khi triển khai thật.
 * FE thì biết chắc, nên ghép ở đây. Nếu backend đổi sang trả URL tuyệt đối,
 * hàm này giữ nguyên giá trị đó.
 */
function urlDayDu(url: string): string {
  if (/^https?:\/\//i.test(url)) return url;
  return `${API_BASE_URL}${url}`;
}

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
          <DinhKem key={dinhKem.id} dinhKem={dinhKem} laKhach={laKhach} />
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
 * Một tệp đính kèm.
 *
 * Ảnh hiển thị bằng URL đã ký backend cấp (hết hạn sau ít phút). Ba trường hợp
 * không vẽ được ảnh — không phải ảnh, thiếu URL, hoặc tải hỏng vì link hết hạn
 * — đều rơi về ô xám có nhãn, để người dùng biết có tệp thay vì thấy icon vỡ.
 */
function DinhKem({
  dinhKem,
  laKhach,
}: {
  dinhKem: Attachment;
  laKhach: boolean;
}) {
  const [loiTai, setLoiTai] = useState(false);
  const laAnh =
    dinhKem.kind?.toUpperCase() === "IMAGE" ||
    (dinhKem.content_type?.startsWith("image/") ?? false);

  if (laAnh && dinhKem.url && !loiTai) {
    const href = urlDayDu(dinhKem.url);
    return (
      <a href={href} target="_blank" rel="noopener noreferrer" className="mt-2 block">
        {/* Dùng <img> thường thay vì next/image: URL đã ký và hết hạn nhanh,
            không hợp với lớp tối ưu ảnh có cache của Next. */}
        {/* eslint-disable-next-line @next/next/no-img-element */}
        <img
          src={href}
          alt="Ảnh đính kèm"
          loading="lazy"
          onError={() => setLoiTai(true)}
          className="max-h-64 max-w-full rounded-md object-contain"
        />
      </a>
    );
  }

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
      {loiTai ? "[không tải được tệp — thử mở lại hội thoại]" : "[tệp đính kèm]"}
    </div>
  );
}
