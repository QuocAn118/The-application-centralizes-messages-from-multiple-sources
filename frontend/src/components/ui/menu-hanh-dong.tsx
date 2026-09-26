"use client";

/**
 * Menu "⋯" cho thao tác trên một dòng (X5) — thay dãy nút Sửa/Xoá/Ngừng lặp ở
 * mọi dòng. Radix DropdownMenu lo bàn phím (mũi tên, Enter, Esc) và ARIA.
 *
 * Mục `nguyHiem` (Xoá, Ngừng, Ngắt) **tự dời xuống cuối**, ngăn bằng vạch, chữ
 * màu `bad`: người dùng không bấm nhầm khi nhắm mục đầu. Menu KHÔNG tự xác nhận —
 * nơi gọi mở `HopXacNhan` trong `onChon` (thao tác huỷ hoại luôn phải xác nhận).
 */

import * as DropdownMenu from "@radix-ui/react-dropdown-menu";
import { Ellipsis, type LucideIcon } from "lucide-react";
import { NutIcon } from "./nut-icon";

export interface MucMenu {
  nhan: string;
  icon?: LucideIcon;
  nguyHiem?: boolean;
  /** Ẩn mục (vd. không đủ quyền) — gọn hơn lọc mảng ở nơi gọi. */
  an?: boolean;
  onChon: () => void;
}

const LOP_MUC =
  "flex cursor-pointer items-center gap-2 rounded-[4px] px-2.5 py-2 text-sm font-semibold outline-none " +
  "data-[highlighted]:bg-accent data-[highlighted]:text-ink";

export function MenuHanhDong({ nhan, muc }: { nhan: string; muc: MucMenu[] }) {
  const hien = muc.filter((m) => !m.an);
  if (hien.length === 0) return null;

  const thuong = hien.filter((m) => !m.nguyHiem);
  const nguyHiem = hien.filter((m) => m.nguyHiem);

  const ve = (m: MucMenu) => (
    <DropdownMenu.Item
      key={m.nhan}
      onSelect={m.onChon}
      className={`${LOP_MUC} ${m.nguyHiem ? "text-bad" : "text-ink"}`}
    >
      {m.icon && <m.icon aria-hidden className="size-4 shrink-0" strokeWidth={2.25} />}
      {m.nhan}
    </DropdownMenu.Item>
  );

  return (
    <DropdownMenu.Root>
      <DropdownMenu.Trigger asChild>
        <NutIcon icon={Ellipsis} nhan={nhan} co="sm" />
      </DropdownMenu.Trigger>
      <DropdownMenu.Portal>
        <DropdownMenu.Content
          align="end"
          sideOffset={6}
          className="z-50 min-w-44 rounded-nb border-2 border-ink bg-card p-1 shadow-nb"
        >
          {thuong.map(ve)}
          {thuong.length > 0 && nguyHiem.length > 0 && (
            <DropdownMenu.Separator className="my-1 h-px bg-line" />
          )}
          {nguyHiem.map(ve)}
        </DropdownMenu.Content>
      </DropdownMenu.Portal>
    </DropdownMenu.Root>
  );
}
