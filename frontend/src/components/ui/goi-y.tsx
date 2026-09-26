"use client";

/**
 * Tooltip (Radix). Dùng cho nút chỉ-có-icon và cho chữ bị rút gọn.
 *
 * Mỗi `GoiY` tự mang `Provider` của nó: đơn giản hơn một provider toàn app, và
 * trang không có tooltip thì không tốn gì.
 */

import * as Tooltip from "@radix-ui/react-tooltip";

export function GoiY({
  noiDung,
  children,
  phia = "top",
}: {
  noiDung: React.ReactNode;
  /** Phần tử kích hoạt — phải nhận được ref + focus (nút, link). */
  children: React.ReactElement;
  phia?: "top" | "right" | "bottom" | "left";
}) {
  return (
    <Tooltip.Provider delayDuration={300}>
      <Tooltip.Root>
        <Tooltip.Trigger asChild>{children}</Tooltip.Trigger>
        <Tooltip.Portal>
          <Tooltip.Content
            side={phia}
            sideOffset={6}
            className="z-50 max-w-xs rounded-nb border-2 border-ink bg-ink px-2.5 py-1.5 text-xs font-semibold text-card"
          >
            {noiDung}
          </Tooltip.Content>
        </Tooltip.Portal>
      </Tooltip.Root>
    </Tooltip.Provider>
  );
}
