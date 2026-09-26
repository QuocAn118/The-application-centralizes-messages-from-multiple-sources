"use client";

/**
 * Thanh tab khu Báo cáo (#F5). Khu chỉ Manager/Admin vào được (layout đã chặn
 * bằng `ChanTheoVai`), nên không cần điều kiện vai ở đây.
 */

import { t } from "@/lib/i18n";
import { TabKhu } from "./ui/tab-khu";

export function TabBaoCao() {
  return (
    <TabKhu
      tieuDe={t("baoCao.tieuDe")}
      tab={[
        { duongDan: "/bao-cao/hoi-thoai", nhan: t("baoCao.tabHoiThoai") },
        { duongDan: "/bao-cao/nhan-vien", nhan: t("baoCao.tabNhanVien") },
        { duongDan: "/bao-cao/ca-kpi", nhan: t("baoCao.tabCaKpi") },
        { duongDan: "/bao-cao/don-tu", nhan: t("baoCao.tabDonTu") },
      ]}
    />
  );
}
