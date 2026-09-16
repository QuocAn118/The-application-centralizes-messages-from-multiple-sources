"use client";

/**
 * Thanh tab khu Nhân sự: Ca làm việc · Đơn từ · KPI.
 *
 * Khác `tab-quan-tri.tsx`: ở đây **mọi vai thấy mọi tab**, vì Staff cũng vào
 * được cả ba màn (chỉ thấy ít dữ liệu hơn — backend lọc theo phạm vi). Vì vậy
 * không nhồi thêm điều kiện vào component của #F2: nó có luật riêng (ba tab chỉ
 * Admin), gộp lại sẽ thành một mớ cờ khó đọc.
 */

import Link from "next/link";
import { usePathname } from "next/navigation";
import { t, type KhoaChuoi } from "@/lib/i18n";

const TAB: { duongDan: string; nhan: KhoaChuoi }[] = [
  { duongDan: "/nhan-su/ca-lam-viec", nhan: "nhanSu.tabCa" },
  { duongDan: "/nhan-su/don-tu", nhan: "nhanSu.tabDon" },
  { duongDan: "/nhan-su/kpi", nhan: "nhanSu.tabKpi" },
];

export function TabNhanSu() {
  const pathname = usePathname();

  return (
    <header className="shrink-0 border-b border-border-subtle bg-white px-6 pt-5">
      <h1 className="text-lg font-semibold text-foreground">{t("nhanSu.tieuDe")}</h1>
      <nav className="mt-4 flex gap-1" aria-label={t("nhanSu.tieuDe")}>
        {TAB.map((tab) => {
          const dangO = pathname.startsWith(tab.duongDan);
          return (
            <Link
              key={tab.duongDan}
              href={tab.duongDan}
              // GĐ3 chưa dựng `/nhan-su/kpi`; Next prefetch mọi <Link> trong
              // tầm nhìn nên sẽ bắn 404 vào console. Bỏ dòng này khi màn KPI
              // ra đời.
              prefetch={tab.duongDan === "/nhan-su/kpi" ? false : undefined}
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
