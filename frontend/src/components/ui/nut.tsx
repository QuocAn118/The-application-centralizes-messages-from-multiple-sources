"use client";

/**
 * Nút Neo-Brutalism — nút gốc của cả app.
 *
 * **Quy tắc bóng (spec Phần 1 §3.2):** nút = bóng NHỎ + PHẢN HỒI (rê dịch 2px,
 * nhấn dịch hết và bóng về 0). Card/bảng/khung cũng có bóng nhưng KHÔNG phản
 * hồi. Huy hiệu KHÔNG có bóng — đó là cách phân biệt nút với nhãn (sửa lỗi
 * "Đang dùng" trông như nút bấm).
 *
 * Nút vô hiệu: nền lõm, viền đứt, bỏ bóng, chữ `ink-2` (vẫn 7,5:1). Cố ý KHÔNG
 * làm mờ bằng `opacity` như trước: nút mờ nhạt trông như trang tải lỗi.
 */

import { forwardRef } from "react";
import { LoaderCircle, type LucideIcon } from "lucide-react";

export type BienTheNut = "chinh" | "phu" | "nguyHiem" | "trong";
export type CoNut = "sm" | "md";

const NEN =
  "inline-flex items-center justify-center gap-2 whitespace-nowrap rounded-nb font-semibold " +
  "transition-[transform,box-shadow,background-color] duration-100 " +
  "disabled:cursor-not-allowed disabled:border-dashed disabled:bg-sunken disabled:text-ink-2 " +
  "disabled:shadow-none disabled:translate-x-0 disabled:translate-y-0";

/** Hiệu ứng ấn: rê dịch 2px, nhấn dịch 4px (tổng) và bóng về 0. */
const AN_BONG =
  "hover:translate-x-[2px] hover:translate-y-[2px] " +
  "active:translate-x-[4px] active:translate-y-[4px] active:shadow-none";

const BIEN_THE: Record<BienTheNut, string> = {
  chinh: `border-[3px] border-ink bg-accent text-ink shadow-nb hover:shadow-nb-sm ${AN_BONG}`,
  phu: `border-2 border-ink bg-card text-ink shadow-nb-sm hover:shadow-none ${AN_BONG}`,
  nguyHiem: `border-2 border-bad bg-card text-bad shadow-[2px_2px_0_var(--bad)] hover:shadow-none ${AN_BONG}`,
  trong: "border-2 border-transparent bg-transparent text-ink hover:bg-sunken",
};

const CO: Record<CoNut, string> = {
  sm: "h-8 px-3 text-xs",
  md: "h-10 px-4 text-sm",
};

export type PropsNut = React.ButtonHTMLAttributes<HTMLButtonElement> & {
  bienThe?: BienTheNut;
  co?: CoNut;
  /** Icon lucide đứng trước chữ. */
  icon?: LucideIcon;
  /** Đang gửi: hiện vòng quay, khoá nút, báo `aria-busy`. */
  dangChay?: boolean;
};

export const Nut = forwardRef<HTMLButtonElement, PropsNut>(function Nut(
  { bienThe = "phu", co = "md", icon: Icon, dangChay = false, className = "", children, disabled, type = "button", onClick, ...props },
  ref,
) {
  const IconHien = dangChay ? LoaderCircle : Icon;
  return (
    <button
      ref={ref}
      type={type}
      // Đang chạy KHÔNG dùng `disabled`: nút đang làm việc không được trông như
      // nút không dùng được (viền đứt, nền xám). Giữ nguyên kiểu, chặn bấm lặp
      // bằng `aria-disabled` + chặn cả chuột lẫn bàn phím trong onClick.
      disabled={disabled}
      aria-disabled={dangChay || undefined}
      aria-busy={dangChay || undefined}
      onClick={(e) => {
        if (dangChay) {
          e.preventDefault();
          return;
        }
        onClick?.(e);
      }}
      className={`${NEN} ${BIEN_THE[bienThe]} ${CO[co]} ${dangChay ? "cursor-wait" : ""} ${className}`}
      {...props}
    >
      {IconHien && (
        <IconHien
          aria-hidden
          strokeWidth={2.25}
          className={`${co === "sm" ? "size-3.5" : "size-4"} shrink-0 ${dangChay ? "animate-spin" : ""}`}
        />
      )}
      {children}
    </button>
  );
});
