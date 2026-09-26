"use client";

/**
 * Nút vuông chỉ có icon. `nhan` là **bắt buộc**: nó thành `aria-label` (trình
 * đọc màn hình) và tooltip (người dùng chuột). Nút icon không tên là nút câm.
 */

import { forwardRef } from "react";
import type { LucideIcon } from "lucide-react";
import { Nut, type BienTheNut, type CoNut, type PropsNut } from "./nut";
import { GoiY } from "./goi-y";

type PropsNutIcon = Omit<PropsNut, "icon" | "children" | "bienThe" | "co"> & {
  icon: LucideIcon;
  nhan: string;
  bienThe?: BienTheNut;
  co?: CoNut;
};

const VUONG: Record<CoNut, string> = { sm: "!w-8 !px-0", md: "!w-10 !px-0" };

export const NutIcon = forwardRef<HTMLButtonElement, PropsNutIcon>(function NutIcon(
  { icon, nhan, bienThe = "trong", co = "md", className = "", ...props },
  ref,
) {
  return (
    <GoiY noiDung={nhan}>
      <Nut
        ref={ref}
        icon={icon}
        bienThe={bienThe}
        co={co}
        aria-label={nhan}
        className={`${VUONG[co]} ${className}`}
        {...props}
      />
    </GoiY>
  );
});
