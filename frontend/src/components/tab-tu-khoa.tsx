"use client";

/**
 * Thanh tab khu Từ khoá: Từ khoá · Phân tích AI (#F4, nợ N6). Mọi vai thấy cả hai
 * tab — Staff xem được, chỉ không sửa (quyền ở từng màn).
 */

import { t } from "@/lib/i18n";
import { TabKhu } from "./ui/tab-khu";

export function TabTuKhoa() {
  return (
    <TabKhu
      tieuDe={t("tuKhoa.tieuDeKhu")}
      tab={[
        { duongDan: "/tu-khoa/danh-sach", nhan: t("quanTri.tabTuKhoa") },
        { duongDan: "/tu-khoa/phan-tich", nhan: t("quanTri.tabPhanTich") },
      ]}
    />
  );
}
