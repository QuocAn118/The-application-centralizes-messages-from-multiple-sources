"use client";

/**
 * Khung hộp thoại dùng chung cho khu quản trị (#F2 task 1.3).
 *
 * Gom lại phần mọi hộp thoại đều phải làm đúng và rất dễ làm sót: Esc để
 * thoát, bấm nền để đóng (nhưng bấm trong hộp thì không), `role="dialog"` +
 * `aria-modal`, và đưa tiêu điểm vào hộp khi mở.
 *
 * Cố ý KHÔNG viết lại `dialog-phan-phong.tsx` của #F1 theo khung này: nó đang
 * chạy tốt và đây là sub-project frontend khác, sửa màn inbox là mở rộng phạm
 * vi ngoài plan. Nếu sau này gộp thì gộp trong một đợt trả nợ riêng.
 */

import { useEffect, useId, useRef } from "react";
import { t } from "@/lib/i18n";

export function HopThoai({
  tieuDe,
  moTa,
  loi,
  onDong,
  children,
  chanDuoi,
}: {
  tieuDe: string;
  moTa?: string;
  /** Thông điệp lỗi hiện ngay trên hàng nút. */
  loi?: string | null;
  /**
   * Đóng hộp thoại. Truyền `null` cho hộp **không được phép đóng tuỳ tiện**
   * (bước hiện mật khẩu tạm — đóng nhầm là mất mật khẩu): khi đó Esc, bấm nền
   * và nút "×" đều tắt, chỉ còn nút ở chân hộp.
   *
   * Cố ý không nhận hàm rỗng thay cho `null`: hàm rỗng vẫn để nút "×" hiện ra
   * và bấm vào không có gì xảy ra — một nút chết thì tệ hơn là không có nút.
   */
  onDong: (() => void) | null;
  children?: React.ReactNode;
  chanDuoi: React.ReactNode;
}) {
  const hopRef = useRef<HTMLDivElement>(null);
  const idTieuDe = useId();

  useEffect(() => {
    hopRef.current?.focus();
    if (!onDong) return;
    function xuLy(e: KeyboardEvent) {
      if (e.key === "Escape") onDong?.();
    }
    document.addEventListener("keydown", xuLy);
    return () => document.removeEventListener("keydown", xuLy);
  }, [onDong]);

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 px-4"
      onClick={(e) => {
        if (e.target === e.currentTarget) onDong?.();
      }}
    >
      <div
        ref={hopRef}
        tabIndex={-1}
        role="dialog"
        aria-modal="true"
        aria-labelledby={idTieuDe}
        className="max-h-[90vh] w-full max-w-[440px] overflow-y-auto rounded-lg bg-white p-6 shadow-xl outline-none"
      >
        <div className="flex items-start justify-between gap-4">
          <h2 id={idTieuDe} className="text-base font-bold text-foreground">
            {tieuDe}
          </h2>
          {onDong && (
            <button
              type="button"
              onClick={onDong}
              aria-label={t("chung.dong")}
              className="text-muted-soft transition hover:text-muted"
            >
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" aria-hidden>
                <path d="M18 6 6 18M6 6l12 12" />
              </svg>
            </button>
          )}
        </div>

        {moTa && <p className="mt-1 text-sm text-muted">{moTa}</p>}

        {children}

        {loi && (
          <p
            role="alert"
            className="mt-4 rounded-lg border border-danger-border bg-danger-bg px-3.5 py-2 text-xs text-danger-fg"
          >
            {loi}
          </p>
        )}

        <div className="mt-6 flex justify-end gap-2">{chanDuoi}</div>
      </div>
    </div>
  );
}

/**
 * Kiểu nút dùng chung.
 *
 * Bỏ `className` khỏi props: hai nút dưới đây tự đặt lớp, nên nhận `className`
 * rồi ghi đè lại là im lặng nuốt mất thứ nơi gọi truyền vào. Muốn kiểu khác thì
 * dùng `<button>` thường.
 */
type PropsNut = Omit<React.ButtonHTMLAttributes<HTMLButtonElement>, "className">;

/** Nút phụ (Huỷ) — gom lại để ba màn sau không đặt lại chuỗi lớp. */
export function NutPhu({ children, ...props }: PropsNut) {
  return (
    <button
      type="button"
      {...props}
      className="rounded-lg border border-border-subtle px-4 py-2 text-sm font-medium text-muted transition hover:bg-surface disabled:cursor-not-allowed disabled:opacity-50"
    >
      {children}
    </button>
  );
}

/** Nút chính. `nguyHiem` đổi sang màu cảnh báo cho thao tác khó hoàn tác. */
export function NutChinh({
  nguyHiem = false,
  children,
  ...props
}: PropsNut & { nguyHiem?: boolean }) {
  return (
    <button
      type="button"
      {...props}
      className={`rounded-lg px-4 py-2 text-sm font-semibold text-white transition hover:brightness-95 disabled:cursor-not-allowed disabled:opacity-50 ${
        nguyHiem ? "bg-danger-fg" : "bg-primary"
      }`}
    >
      {children}
    </button>
  );
}
