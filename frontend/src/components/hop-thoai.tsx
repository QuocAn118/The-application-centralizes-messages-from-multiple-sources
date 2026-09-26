"use client";

/**
 * Khung hộp thoại dùng chung (#F2 task 1.3) — nay chạy trên Radix Dialog
 * (redesign Phần 1). API giữ nguyên nên 15 hộp thoại đang gọi không phải sửa.
 *
 * Radix lo phần trước đây tự viết tay và dễ sót: bẫy focus trong hộp (Tab không
 * chạy ra trang phía sau), trả focus về nút đã mở hộp khi đóng, Esc, `aria-modal`,
 * khoá cuộn trang nền.
 *
 * Hộp chỉ được render khi đang mở (nơi gọi tự mount/unmount), nên `open` luôn
 * `true`; đóng = gọi `onDong` để nơi gọi gỡ hộp ra.
 */

import * as Dialog from "@radix-ui/react-dialog";
import { useRef } from "react";
import { X } from "lucide-react";
import { t } from "@/lib/i18n";
import { Nut } from "./ui/nut";
import { NutIcon } from "./ui/nut-icon";

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
  // Chặn mọi đường đóng "ngầm" khi hộp không được phép đóng tuỳ tiện.
  const chanDong = onDong ? undefined : (e: Event) => e.preventDefault();

  return (
    <Dialog.Root
      open
      onOpenChange={(mo) => {
        if (!mo) onDong?.();
      }}
    >
      <Dialog.Portal>
        <Dialog.Overlay className="fixed inset-0 z-50 bg-ink/45" />
        <Dialog.Content
          ref={hopRef}
          // Không có mô tả: báo Radix là cố ý (khỏi cảnh báo). CÓ mô tả thì KHÔNG
          // truyền prop này — truyền `undefined` sẽ đè mất liên kết Radix tự nối.
          {...(moTa ? {} : { "aria-describedby": undefined })}
          onEscapeKeyDown={chanDong}
          onPointerDownOutside={chanDong}
          onInteractOutside={chanDong}
          // Đưa focus vào CHÍNH hộp (như bản cũ), không nhảy vào nút × vốn đứng
          // đầu hộp — mở form ra mà focus nằm ở nút đóng thì lạ tay.
          onOpenAutoFocus={(e) => {
            e.preventDefault();
            hopRef.current?.focus();
          }}
          className="fixed left-1/2 top-1/2 z-50 max-h-[90vh] w-[calc(100%-2rem)] max-w-[480px] -translate-x-1/2 -translate-y-1/2 overflow-y-auto rounded-nb border-2 border-ink bg-card p-6 shadow-nb outline-none"
        >
          <div className="flex items-start justify-between gap-4">
            <Dialog.Title className="text-lg font-extrabold leading-tight text-ink">
              {tieuDe}
            </Dialog.Title>
            {onDong && (
              <Dialog.Close asChild>
                <NutIcon icon={X} nhan={t("chung.dong")} co="sm" className="-mr-1 -mt-1" />
              </Dialog.Close>
            )}
          </div>

          {moTa ? (
            <Dialog.Description className="mt-1 text-sm text-ink-2">{moTa}</Dialog.Description>
          ) : null}

          {children}

          {loi && (
            <p
              role="alert"
              className="mt-4 rounded-nb border-2 border-bad bg-bad-bg px-3.5 py-2 text-sm font-semibold text-bad"
            >
              {loi}
            </p>
          )}

          <div className="mt-6 flex justify-end gap-2">{chanDuoi}</div>
        </Dialog.Content>
      </Dialog.Portal>
    </Dialog.Root>
  );
}

/**
 * Kiểu nút dùng chung — nay bọc `Nut` của design system (redesign Phần 1).
 *
 * Giữ nguyên API cũ (`nguyHiem`, không nhận `className`) để 15 hộp thoại đang
 * gọi không phải sửa gì mà vẫn đổi sang giao diện mới.
 */
type PropsNutCu = Omit<React.ButtonHTMLAttributes<HTMLButtonElement>, "className">;

/** Nút phụ (Huỷ). */
export function NutPhu({ children, ...props }: PropsNutCu) {
  return (
    <Nut bienThe="phu" {...props}>
      {children}
    </Nut>
  );
}

/** Nút chính. `nguyHiem` đổi sang kiểu cảnh báo cho thao tác khó hoàn tác. */
export function NutChinh({
  nguyHiem = false,
  children,
  ...props
}: PropsNutCu & { nguyHiem?: boolean }) {
  return (
    <Nut bienThe={nguyHiem ? "nguyHiem" : "chinh"} {...props}>
      {children}
    </Nut>
  );
}
