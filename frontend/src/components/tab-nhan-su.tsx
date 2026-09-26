"use client";

/** Thanh tab khu Nhân sự: Ca làm việc · Đơn từ · KPI. Mọi vai thấy mọi tab. */

import { t } from "@/lib/i18n";
import { TabKhu } from "./ui/tab-khu";

export function TabNhanSu() {
  return (
    <TabKhu
      tieuDe={t("nhanSu.tieuDe")}
      tab={[
        { duongDan: "/nhan-su/ca-lam-viec", nhan: t("nhanSu.tabCa") },
        { duongDan: "/nhan-su/don-tu", nhan: t("nhanSu.tabDon") },
        { duongDan: "/nhan-su/kpi", nhan: t("nhanSu.tabKpi") },
      ]}
    />
  );
}
