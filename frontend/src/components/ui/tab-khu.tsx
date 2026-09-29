"use client";

/**
 * Thanh tab của một khu (Nhân sự, Từ khoá & AI, Báo cáo, Cấu hình) — thay 4 bản chép
 * nhau trước đây (X10). Mỗi khu chỉ còn lo danh sách tab và điều kiện vai.
 *
 * Tab đang mở: nền vàng + viền, KHÔNG bóng (không phải thứ để bấm nữa). Tab khác
 * hiện viền + bóng nhỏ khi rê (quy tắc bóng, spec Phần 1 §3.2).
 *
 * Giữ nguyên cấu trúc `header > nav[aria-label] > a[aria-current="page"]`: các
 * kịch bản kiểm chứng #F2–#F5 dựa vào đó.
 */

import Link from "next/link";
import { usePathname } from "next/navigation";

export interface MucTab {
  duongDan: string;
  nhan: string;
}

export function TabKhu({ tieuDe, tab }: { tieuDe: string; tab: MucTab[] }) {
  const pathname = usePathname();

  return (
    <header className="shrink-0 border-b-2 border-ink bg-card px-8 pb-4 pt-5">
      {/* Tên khu là NHÃN, không phải h1: mỗi màn một h1 duy nhất = tên trang
          (DauTrang). Hai h1 ngang cỡ làm trình đọc màn hình không biết đâu là chính. */}
      <p className="text-xs font-bold uppercase tracking-wide text-ink-2">{tieuDe}</p>
      <nav className="mt-3 flex gap-2" aria-label={tieuDe}>
        {tab.map((muc) => {
          const dangO = pathname.startsWith(muc.duongDan);
          return (
            <Link
              key={muc.duongDan}
              href={muc.duongDan}
              aria-current={dangO ? "page" : undefined}
              className={`rounded-nb border-2 px-4 py-1.5 text-sm font-bold transition-[transform,box-shadow] duration-100 ${
                dangO
                  ? "border-ink bg-accent text-ink"
                  : "border-transparent text-ink-2 hover:border-ink hover:text-ink hover:shadow-nb-sm"
              }`}
            >
              {muc.nhan}
            </Link>
          );
        })}
      </nav>
    </header>
  );
}
