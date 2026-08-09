"use client";

/** Một dòng trong danh sách inbox (mockup Stitch: cột trái). */

import Link from "next/link";
import { BadgeKenh, BadgeTrangThai } from "./badges";
import { chuCaiDau, mocDayDu, mocNgan, tenKhach } from "@/lib/hien-thi";
import type { InboxItem } from "@/lib/types";

export function DongHoiThoai({
  item,
  dangChon,
}: {
  item: InboxItem;
  dangChon: boolean;
}) {
  const ten = tenKhach(item.customer_display_name);

  return (
    <Link
      href={`/inbox/${item.conversation_id}`}
      aria-current={dangChon ? "true" : undefined}
      className={`flex gap-3 border-l-2 px-4 py-3 transition ${
        dangChon
          ? "border-l-primary bg-primary-soft"
          : "border-l-transparent hover:bg-surface"
      }`}
    >
      <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-full bg-surface text-sm font-semibold text-muted">
        {chuCaiDau(item.customer_display_name)}
      </div>

      <div className="min-w-0 flex-1">
        <div className="flex items-baseline justify-between gap-2">
          <span className="truncate text-sm font-semibold text-foreground">
            {ten}
          </span>
          <time
            dateTime={item.last_message_at}
            title={mocDayDu(item.last_message_at)}
            className="shrink-0 text-[11px] text-muted-soft"
          >
            {mocNgan(item.last_message_at)}
          </time>
        </div>

        {item.last_message_preview && (
          <p className="mt-0.5 truncate text-xs text-muted">
            {item.last_message_preview}
          </p>
        )}

        <div className="mt-1.5 flex flex-wrap items-center gap-1.5">
          <BadgeKenh platform={item.platform} />
          <BadgeTrangThai status={item.status} />
        </div>
      </div>
    </Link>
  );
}
