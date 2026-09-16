"use client";

/**
 * Một dòng mục tiêu KPI, tự tải tiến độ của chính nó (#F3 task 3.3).
 *
 * **Vì sao mỗi dòng một truy vấn:** `GET /kpi-targets` chỉ trả *mục tiêu*, không
 * kèm thực đạt; thực đạt nằm ở `GET /kpi-progress` và endpoint đó nhận **đúng
 * một** đối tượng/chỉ số/kỳ mỗi lần gọi. Không có API lấy hàng loạt, nên N dòng
 * là N lời gọi. React Query gom cache theo khoá riêng từng dòng nên đổi kỳ hay
 * đặt lại mục tiêu chỉ tải lại phần đổi.
 *
 * **Tiến độ hỏng thì dòng vẫn còn.** Mục tiêu đã tải được rồi; để cả dòng biến
 * mất chỉ vì không tính được thực đạt là giấu mất thông tin đang có. Lỗi tiến
 * độ hiện thành dấu gạch tại chỗ.
 */

import { useQuery } from "@tanstack/react-query";
import { t } from "@/lib/i18n";
import {
  DAU_GACH,
  DON_VI_KPI,
  NHAN_CHI_SO_KPI,
  lopMucKpi,
  phanTramKpi,
  soKpi,
} from "@/lib/hien-thi";
import { khoaNhanSu, layTienDoKpi } from "@/lib/nhan-su-api";
import type { KpiTarget } from "@/lib/types";

export function HangKpi({
  mucTieu,
  tenDoiTuong,
  xemDuocTienDo,
  onSua,
}: {
  mucTieu: KpiTarget;
  tenDoiTuong: string;
  /**
   * Staff không xem được KPI cấp phòng (`KPI_FORBIDDEN`). Khi không xem được,
   * không gọi API — gọi rồi nuốt lỗi chỉ tạo 403 rác trong console.
   */
  xemDuocTienDo: boolean;
  onSua: (() => void) | null;
}) {
  const tienDo = useQuery({
    queryKey: khoaNhanSu.kpi.tienDo(
      mucTieu.subject_type,
      mucTieu.subject_id,
      mucTieu.metric_type,
      mucTieu.period_year,
      mucTieu.period_month,
    ),
    queryFn: ({ signal }) =>
      layTienDoKpi(
        {
          subject_type: mucTieu.subject_type,
          subject_id: mucTieu.subject_id,
          metric_type: mucTieu.metric_type,
          period_year: mucTieu.period_year,
          period_month: mucTieu.period_month,
        },
        signal,
      ),
    enabled: xemDuocTienDo,
    retry: false,
  });

  const donVi = DON_VI_KPI[mucTieu.metric_type];
  const chuaCoSoLieu = tienDo.data?.actual_value === null;

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
        {tienDo.isPending && xemDuocTienDo ? (
          <span className="text-xs text-muted">{t("kpi.dangTinh")}</span>
        ) : tienDo.data ? (
          <span title={chuaCoSoLieu ? t("kpi.chuaCoSoLieu") : undefined}>
            {soKpi(tienDo.data.actual_value)}
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
          tienDo.data ? lopMucKpi(tienDo.data.achievement_percent) : "text-muted"
        }`}
      >
        {tienDo.data ? phanTramKpi(tienDo.data.achievement_percent) : DAU_GACH}
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
