"use client";

/**
 * Một trường form: nhãn TRÊN ô, gợi ý và lỗi DƯỚI ô, nối với ô bằng
 * `aria-describedby` để trình đọc màn hình đọc cả gợi ý lẫn lỗi.
 *
 * Nhận `children` là hàm để trao cho ô nhập đúng `id` + thuộc tính ARIA, thay vì
 * bắt nơi gọi tự nối tay (dễ quên, và quên thì lỗi không được đọc ra).
 */

import { useId } from "react";

export type ThuocTinhO = {
  id: string;
  "aria-describedby"?: string;
  coLoi?: boolean;
};

export function Truong({
  nhan,
  goiY,
  loi,
  batBuoc = false,
  children,
}: {
  nhan: string;
  goiY?: string;
  loi?: string | null;
  batBuoc?: boolean;
  children: (o: ThuocTinhO) => React.ReactNode;
}) {
  const id = useId();
  const idGoiY = `${id}-goi-y`;
  const idLoi = `${id}-loi`;
  const moTa = [goiY && idGoiY, loi && idLoi].filter(Boolean).join(" ") || undefined;

  return (
    <div className="flex flex-col gap-1.5">
      <label htmlFor={id} className="text-sm font-semibold text-ink">
        {nhan}
        {batBuoc && (
          <span className="ml-0.5 text-bad" aria-hidden>
            *
          </span>
        )}
      </label>
      {children({ id, "aria-describedby": moTa, coLoi: Boolean(loi) })}
      {goiY && (
        <p id={idGoiY} className="text-xs text-ink-2">
          {goiY}
        </p>
      )}
      {loi && (
        <p id={idLoi} className="text-xs font-semibold text-bad">
          {loi}
        </p>
      )}
    </div>
  );
}
