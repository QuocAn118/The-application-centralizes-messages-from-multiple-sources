"use client";

/**
 * Một bong bóng tin trong khung chat (mockup Stitch).
 *
 * INBOUND (khách) canh trái, nền ngà viền mực; OUTBOUND (nhân viên) canh phải,
 * nền xanh chữ trắng. Không bóng — bong bóng không phải thứ để bấm.
 */

import { useState } from "react";
import { t } from "@/lib/i18n";
import { API_BASE_URL } from "@/lib/api-client";
import { ImageIcon } from "lucide-react";
import { mocDayDu } from "@/lib/hien-thi";
import { gioPhut } from "@/lib/hop-thu";
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

export function BongBongTin({
  message,
  dauNhom = true,
  cuoiNhom = true,
}: {
  message: Message;
  /** Tin đầu nhóm có khoảng cách trên rộng hơn; trong nhóm các tin sát nhau. */
  dauNhom?: boolean;
  /** Chỉ tin cuối nhóm hiện giờ (GĐ1 I8). */
  cuoiNhom?: boolean;
}) {
  const laKhach = message.direction === "INBOUND";

  return (
    <div className={`flex flex-col ${laKhach ? "items-start" : "items-end"} ${dauNhom ? "mt-3" : "mt-1"}`}>
      <div
        className={`max-w-[min(560px,75%)] rounded-nb border-2 border-ink px-3.5 py-2.5 text-sm ${
          laKhach ? "bg-card text-ink" : "bg-accent-2 text-white"
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
          <p className="italic opacity-80">{t("chat.tinKhongCoNoiDung")}</p>
        )}
      </div>

      {cuoiNhom && (
        <time
          dateTime={message.created_at}
          title={mocDayDu(message.created_at)}
          className="mt-1 px-1 text-xs text-ink-2"
        >
          {gioPhut(message.created_at)}
        </time>
      )}
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
          alt={t("chat.anhDinhKem")}
          loading="lazy"
          onError={() => setLoiTai(true)}
          className="max-h-64 max-w-full rounded-[4px] object-contain"
        />
      </a>
    );
  }

  return (
    <div
      className={`mt-2 flex items-center gap-2 rounded-md px-3 py-2 text-xs ${
        laKhach ? "bg-sunken text-ink-2" : "bg-white/15 text-white"
      }`}
    >
      <ImageIcon aria-hidden className="size-4 shrink-0" />
      {loiTai ? t("chat.loiTaiTep") : t("chat.tepDinhKem")}
    </div>
  );
}
