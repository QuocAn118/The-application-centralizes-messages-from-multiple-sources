"use client";

/**
 * Thanh tab khu Từ khoá: Từ khoá · Phân tích AI.
 *
 * **Mọi vai thấy cả hai tab** — như `tab-nhan-su.tsx` của #F3, khác
 * `tab-quan-tri.tsx` (nơi ba tab chỉ Admin). Staff xem được cả hai màn, chỉ
 * không thấy nút sửa.
 */

import Link from "next/link";
import { usePathname } from "next/navigation";
import { t, type KhoaChuoi } from "@/lib/i18n";

const TAB: { duongDan: string; nhan: KhoaChuoi }[] = [
  { duongDan: "/tu-khoa/danh-sach", nhan: "quanTri.tabTuKhoa" },
  { duongDan: "/tu-khoa/phan-tich", nhan: "quanTri.tabPhanTich" },
];

export function TabTuKhoa() {
  const pathname = usePathname();

  return (
    <header className="shrink-0 border-b border-border-subtle bg-white px-6 pt-5">
      <h1 className="text-lg font-semibold text-foreground">{t("tuKhoa.tieuDeKhu")}</h1>
      <nav className="mt-4 flex gap-1" aria-label={t("tuKhoa.tieuDeKhu")}>
        {TAB.map((tab) => {
          const dangO = pathname.startsWith(tab.duongDan);
          return (
            <Link
              key={tab.duongDan}
              href={tab.duongDan}
              aria-current={dangO ? "page" : undefined}
              className={`-mb-px border-b-2 px-4 py-2 text-sm font-medium transition ${
                dangO
                  ? "border-primary text-primary"
                  : "border-transparent text-muted hover:text-foreground"
              }`}
            >
              {t(tab.nhan)}
            </Link>
          );
        })}
      </nav>
    </header>
  );
}
