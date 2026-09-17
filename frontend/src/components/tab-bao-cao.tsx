"use client";

/**
 * Thanh tab khu Báo cáo: Hội thoại · Nhân viên · Ca & KPI · Đơn từ.
 *
 * Giống `tab-nhan-su.tsx` về cấu trúc, nhưng khu này **chỉ Manager/Admin** vào
 * được (layout đã chặn bằng `ChanTheoVai`), nên không cần cờ theo vai ở đây.
 */

import Link from "next/link";
import { usePathname } from "next/navigation";
import { t, type KhoaChuoi } from "@/lib/i18n";

const TAB: { duongDan: string; nhan: KhoaChuoi }[] = [
  { duongDan: "/bao-cao/hoi-thoai", nhan: "baoCao.tabHoiThoai" },
  { duongDan: "/bao-cao/nhan-vien", nhan: "baoCao.tabNhanVien" },
  { duongDan: "/bao-cao/ca-kpi", nhan: "baoCao.tabCaKpi" },
  { duongDan: "/bao-cao/don-tu", nhan: "baoCao.tabDonTu" },
];

export function TabBaoCao() {
  const pathname = usePathname();

  return (
    <header className="shrink-0 border-b border-border-subtle bg-white px-6 pt-5">
      <h1 className="text-lg font-semibold text-foreground">{t("baoCao.tieuDe")}</h1>
      <nav className="mt-4 flex gap-1" aria-label={t("baoCao.tieuDe")}>
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
