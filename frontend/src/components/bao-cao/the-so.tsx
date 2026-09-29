"use client";

/**
 * Thẻ số tóm tắt đầu trang báo cáo (B1 thẻ KPI, B4 thẻ tóm tắt).
 *
 * Số lớn là thứ mắt tìm trước; `phu` giải thích số đó đếm cái gì (mẫu số, số
 * mẫu) — một con số không kèm ngữ cảnh dễ đọc sai. Dùng `<dl>` để trình đọc
 * màn hình đọc thành cặp "nhãn — giá trị".
 */

import type { LucideIcon } from "lucide-react";
import { The } from "@/components/ui/the";

export function HangTheSo({ nhan, children }: { nhan: string; children: React.ReactNode }) {
  return (
    <dl aria-label={nhan} className="grid grid-cols-[repeat(auto-fit,minmax(15rem,1fr))] gap-4">
      {children}
    </dl>
  );
}

export function TheSo({
  icon: Icon,
  nhan,
  giaTri,
  phu,
}: {
  icon: LucideIcon;
  nhan: string;
  giaTri: string;
  phu?: string;
}) {
  return (
    <The as="div" className="flex flex-col gap-1 px-5 py-4">
      <dt className="flex items-center gap-2 text-xs font-bold uppercase tracking-wide text-ink-2">
        <Icon aria-hidden className="size-4" strokeWidth={2.5} />
        {nhan}
      </dt>
      <dd className="text-[28px] font-extrabold leading-tight tabular-nums text-ink">{giaTri}</dd>
      {phu && <dd className="text-xs text-ink-2">{phu}</dd>}
    </The>
  );
}
