"use client";

/**
 * Một dòng mục tiêu KPI (#F3 task 3.3).
 *
 * **Tiến độ truyền từ trên xuống, dòng KHÔNG tự gọi API** (trả nợ N4). Trước
 * đây mỗi dòng tự tải `GET /kpi-progress` của chính nó, vì endpoint đó nhận
 * đúng một đối tượng mỗi lần; bảng 68 dòng của Admin thành 68 lời gọi và ~3,2
 * giây trước khi đầy đủ. Nay cả bảng lấy một lần qua `/kpi-progress-batch`.
 *
 * **Tiến độ hỏng thì dòng vẫn còn.** Mục tiêu đã tải được rồi; để cả dòng biến
 * mất chỉ vì không tính được thực đạt là giấu mất thông tin đang có. Không có
 * tiến độ thì hiện dấu gạch tại chỗ.
 */

import { t } from "@/lib/i18n";
import {
  DAU_GACH,
  DON_VI_KPI,
  NHAN_CHI_SO_KPI,
  lopMucKpi,
  phanTramKpi,
  soKpi,
} from "@/lib/hien-thi";
import type { KpiProgress, KpiTarget } from "@/lib/types";

export function HangKpi({
  mucTieu,
  tenDoiTuong,
  tienDo,
  dangTai,
  onSua,
}: {
  mucTieu: KpiTarget;
  tenDoiTuong: string;
  /** `undefined` = chưa có tiến độ cho dòng này (đang tải, hoặc lỗi). */
  tienDo: KpiProgress | undefined;
  dangTai: boolean;
  onSua: (() => void) | null;
}) {
  const donVi = DON_VI_KPI[mucTieu.metric_type];
  const chuaCoSoLieu = tienDo?.actual_value === null;

  return (
    <tr className="border-b border-border-subtle last:border-0">
      <td className="px-4 py-3">
        <span className="block truncate text-sm font-medium text-foreground">
          {tenDoiTuong}
        </span>
      </td>

      <td className="px-4 py-3 text-sm text-foreground">
        {NHAN_CHI_SO_KPI[mucTieu.metric_type]}
      </td>

      <td className="px-4 py-3 text-right text-sm font-medium text-foreground">
        {soKpi(mucTieu.target_value)}{" "}
        <span className="text-xs font-normal text-muted">{donVi}</span>
      </td>

      {/* Thực đạt: KHÔNG tô màu theo độ lớn. Với `AVG_RESPONSE_MINUTES` số lớn
          là xấu, số nhỏ là tốt — ngược với chỉ số kia. Chỉ phần trăm hoàn thành
          mới tô được, vì backend đã chuẩn hoá chiều (RB-8). */}
      <td className="px-4 py-3 text-right text-sm text-foreground">
        {dangTai ? (
          <span className="text-xs text-muted">{t("kpi.dangTinh")}</span>
        ) : tienDo ? (
          <span title={chuaCoSoLieu ? t("kpi.chuaCoSoLieu") : undefined}>
            {soKpi(tienDo.actual_value)}
            {!chuaCoSoLieu && (
              <span className="ml-1 text-xs font-normal text-muted">{donVi}</span>
            )}
          </span>
        ) : (
          <span className="text-muted" title={t("kpi.chuaCoSoLieu")}>
            {DAU_GACH}
          </span>
        )}
      </td>

      <td
        className={`px-4 py-3 text-right text-sm font-semibold ${
          tienDo ? lopMucKpi(tienDo.achievement_percent) : "text-muted"
        }`}
      >
        {tienDo ? phanTramKpi(tienDo.achievement_percent) : DAU_GACH}
      </td>

      <td className="px-4 py-3 text-right">
        {onSua && (
          <button
            type="button"
            onClick={onSua}
            className="whitespace-nowrap rounded-lg border border-border-subtle px-3 py-1.5 text-xs font-medium text-foreground transition hover:bg-surface"
          >
            {t("kpi.suaMucTieu")}
          </button>
        )}
      </td>
    </tr>
  );
}
