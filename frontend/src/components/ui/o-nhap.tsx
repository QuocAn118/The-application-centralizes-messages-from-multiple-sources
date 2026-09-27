"use client";

/**
 * Ô nhập, vùng nhập, ô chọn — viền 2px, nền ngà, không bóng (ô nhập không phải
 * thứ để "bấm" — theo quy tắc bóng (spec Phần 1 §3.2) nó không có bóng).
 *
 * `OChon` là **`<select>` native** có style, không phải Radix Select: native đã
 * có sẵn bàn phím, đọc màn hình và bộ chọn của hệ điều hành. Danh sách tuỳ chọn
 * không style được — chấp nhận, vì app dùng cả ngày cần nhanh và quen tay hơn
 * là đẹp. (ponytail: không thêm thư viện cho việc trình duyệt đã làm.)
 */

import { forwardRef } from "react";
import { ChevronDown } from "lucide-react";

const O =
  "w-full rounded-nb border-2 bg-card px-3 text-sm text-ink placeholder:text-ink-2 " +
  "disabled:cursor-not-allowed disabled:border-dashed disabled:bg-sunken disabled:text-ink-2";

const vien = (coLoi?: boolean) => (coLoi ? "border-bad" : "border-ink");

type PhanLoi = { coLoi?: boolean };

export const ONhap = forwardRef<
  HTMLInputElement,
  React.InputHTMLAttributes<HTMLInputElement> & PhanLoi
>(function ONhap({ coLoi, className = "", ...props }, ref) {
  return (
    <input
      ref={ref}
      aria-invalid={coLoi || undefined}
      className={`${O} h-10 ${vien(coLoi)} ${className}`}
      {...props}
    />
  );
});

export const VungNhap = forwardRef<
  HTMLTextAreaElement,
  React.TextareaHTMLAttributes<HTMLTextAreaElement> & PhanLoi
>(function VungNhap({ coLoi, className = "", ...props }, ref) {
  return (
    <textarea
      ref={ref}
      aria-invalid={coLoi || undefined}
      className={`${O} min-h-20 py-2 leading-relaxed ${vien(coLoi)} ${className}`}
      {...props}
    />
  );
});

export const OChon = forwardRef<
  HTMLSelectElement,
  React.SelectHTMLAttributes<HTMLSelectElement> & PhanLoi
>(function OChon({ coLoi, className = "", children, ...props }, ref) {
  return (
    <div className={`relative ${className}`}>
      <select
        ref={ref}
        aria-invalid={coLoi || undefined}
        className={`${O} h-10 appearance-none pr-9 font-medium ${vien(coLoi)}`}
        {...props}
      >
        {children}
      </select>
      <ChevronDown
        aria-hidden
        strokeWidth={2.5}
        className="pointer-events-none absolute right-3 top-1/2 size-4 -translate-y-1/2 text-ink"
      />
    </div>
  );
});
