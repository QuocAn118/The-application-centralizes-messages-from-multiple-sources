"use client";

/**
 * Khung cho màn quản lý Nhãn / Mẫu trả lời — CÙNG một nội dung, hai chỗ đặt
 * (redesign Phần 6, xem lại quyết định 2b):
 * - `trang`: tab trong Cấu hình (Manager + Admin) — chỗ chính, tìm được từ nav;
 * - hộp thoại: lối tắt ngay trong Hộp thư, quản lý giữa lúc đang trả lời khách
 *   mà không rời hội thoại.
 */

import { CircleAlert } from "lucide-react";
import { HopThoai, NutPhu } from "./hop-thoai";
import { DauTrang } from "./ui/dau-trang";
import { The } from "./ui/the";

export function KhungQuanLy({
  trang,
  tieuDe,
  moTa,
  loi,
  onDong,
  children,
}: {
  trang: boolean;
  tieuDe: string;
  moTa: string;
  loi: string | null;
  /** Bắt buộc khi là hộp thoại. */
  onDong?: () => void;
  children: React.ReactNode;
}) {
  if (!trang && onDong) {
    return (
      <HopThoai tieuDe={tieuDe} moTa={moTa} loi={loi} onDong={onDong} chanDuoi={<NutPhu onClick={onDong}>Xong</NutPhu>}>
        {children}
      </HopThoai>
    );
  }
  return (
    <div className="mx-auto flex max-w-[960px] flex-col gap-5 px-8 py-6">
      <DauTrang tieuDe={tieuDe} moTa={moTa} />
      <The className="p-5">
        {loi && (
          <p
            role="alert"
            className="mb-4 flex items-start gap-2 rounded-nb border-2 border-bad bg-bad-bg px-3 py-2.5 text-sm font-semibold text-bad"
          >
            <CircleAlert aria-hidden className="mt-0.5 size-4 shrink-0" strokeWidth={2.5} />
            {loi}
          </p>
        )}
        {children}
      </The>
    </div>
  );
}
