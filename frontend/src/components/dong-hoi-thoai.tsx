"use client";

/**
 * Một dòng trong danh sách Hộp thư (redesign 2a, GĐ1 I1–I6, I13).
 *
 * Hai tầng: **tên · mốc giờ** / **xem trước · số chưa đọc**. Huy hiệu chỉ khi
 * cần chú ý (Chờ phân, Chưa ai nhận, Chờ N phút) — không lặp "Đang mở" ở mọi dòng.
 * Kênh là logo ở góc avatar thay cho tag chữ.
 */

import Link from "next/link";
import { Clock } from "lucide-react";
import { Avatar } from "./ui/avatar";
import { HuyHieu } from "./ui/huy-hieu";
import { mocDayDu, tenKhach } from "@/lib/hien-thi";
import { hienSoChuaDoc, laChoLau, mocTuongDoi, nhanCho, phutCho } from "@/lib/hop-thu";
import type { InboxItem } from "@/lib/types";

export function DongHoiThoai({
  item,
  dangChon,
  bayGio,
  boLoc,
}: {
  item: InboxItem;
  dangChon: boolean;
  /** Đồng hồ chung của danh sách (nhịp 1 phút) — không gọi lại API. */
  bayGio: Date;
  /** Chuỗi query hiện tại (`loc`, `status`, `q`) — mở hội thoại không làm mất bộ lọc. */
  boLoc: string;
}) {
  const ten = tenKhach(item.customer_display_name);
  const soChuaDoc = hienSoChuaDoc(item.unread_count);
  const cho = phutCho(item.waiting_since, bayGio);

  return (
    <Link
      href={`/inbox/${item.conversation_id}${boLoc ? `?${boLoc}` : ""}`}
      aria-current={dangChon ? "true" : undefined}
      className={`flex gap-3 border-b-2 border-l-4 border-b-line px-4 py-3 outline-offset-[-3px] ${
        dangChon ? "border-l-ink bg-accent" : "border-l-transparent hover:bg-sunken"
      }`}
    >
      <Avatar id={item.customer_id} ten={item.customer_display_name} kenh={item.platform} />

      <div className="min-w-0 flex-1">
        <div className="flex items-baseline justify-between gap-2">
          <span className={`truncate text-sm text-ink ${soChuaDoc ? "font-extrabold" : "font-semibold"}`}>
            {ten}
          </span>
          <time
            dateTime={item.last_message_at}
            title={mocDayDu(item.last_message_at)}
            className={`shrink-0 text-xs ${soChuaDoc ? "font-bold text-ink" : "text-ink-2"}`}
          >
            {mocTuongDoi(item.last_message_at, bayGio)}
          </time>
        </div>

        <div className="mt-0.5 flex items-center justify-between gap-2">
          <p className={`truncate text-sm ${soChuaDoc ? "font-semibold text-ink" : "text-ink-2"}`}>
            {item.last_message_preview ?? " "}
          </p>
          {soChuaDoc && (
            <span
              aria-label={`${item.unread_count} tin chưa đọc`}
              className="inline-flex h-5 min-w-5 shrink-0 items-center justify-center rounded-full border-2 border-ink bg-accent px-1 text-xs font-extrabold text-ink"
            >
              {soChuaDoc}
            </span>
          )}
        </div>

        {(item.status === "CHO_PHAN" ||
          (item.status === "DANG_MO" && !item.assigned_user_id) ||
          cho !== null) && (
          <div className="mt-1.5 flex flex-wrap items-center gap-1.5">
            {item.status === "CHO_PHAN" && <HuyHieu tong="wait">Chờ phân</HuyHieu>}
            {item.status === "DANG_MO" && !item.assigned_user_id && (
              <HuyHieu tong="info">Chưa ai nhận</HuyHieu>
            )}
            {cho !== null && (
              <HuyHieu tong={laChoLau(cho) ? "bad" : "trung"}>
                <Clock aria-hidden className="size-3" strokeWidth={2.5} />
                {nhanCho(cho)}
              </HuyHieu>
            )}
          </div>
        )}
      </div>
    </Link>
  );
}
