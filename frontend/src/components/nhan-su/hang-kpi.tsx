"use client";

/**
 * Một dòng mục tiêu KPI (#F3 task 3.3, redesign Phần 3 K1/K2).
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

import { Pencil } from "lucide-react";
import { t } from "@/lib/i18n";
import {
  DAU_GACH,
  DON_VI_KPI,
  NHAN_CHI_SO_KPI,
  lopMucKpi,
  phanTramKpi,
  soKpi,
  thanhKpi,
} from "@/lib/hien-thi";
import type { KpiProgress, KpiTarget } from "@/lib/types";
import { Td, Tr } from "@/components/ui/bang";
import { MenuHanhDong } from "@/components/ui/menu-hanh-dong";

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
  const thanh = tienDo ? thanhKpi(tienDo.achievement_percent) : null;

  return (
    <Tr>
      <Td>
        <span className="block truncate font-bold">{tenDoiTuong}</span>
      </Td>

      <Td>{NHAN_CHI_SO_KPI[mucTieu.metric_type]}</Td>

      <Td className="text-right tabular-nums">
        <span className="font-semibold">{soKpi(mucTieu.target_value)}</span>{" "}
        <span className="text-xs text-ink-2">{donVi}</span>
      </Td>

      {/* Thực đạt: KHÔNG tô màu theo độ lớn. Với `AVG_RESPONSE_MINUTES` số lớn
          là xấu, số nhỏ là tốt — ngược với chỉ số kia. Chỉ phần trăm hoàn thành
          mới tô được, vì backend đã chuẩn hoá chiều (RB-8). */}
      <Td className="text-right tabular-nums">
        {dangTai ? (
          <span className="text-xs text-ink-2">{t("kpi.dangTinh")}</span>
        ) : tienDo ? (
          <span title={chuaCoSoLieu ? t("kpi.chuaCoSoLieu") : undefined}>
            {soKpi(tienDo.actual_value)}
            {!chuaCoSoLieu && <span className="ml-1 text-xs text-ink-2">{donVi}</span>}
          </span>
        ) : (
          <span className="text-ink-2" title={t("kpi.chuaCoSoLieu")}>
            {DAU_GACH}
          </span>
        )}
      </Td>

      {/* K1: thanh tiến độ. null ≠ 0%: không có số thì chỉ "—", không vẽ thanh rỗng. */}
      <Td>
        <div className="flex items-center justify-end gap-3">
          {thanh && (
            <span
              aria-hidden
              className="h-3 w-28 overflow-hidden rounded-[3px] border-2 border-ink bg-sunken"
            >
              <span className={`block h-full ${thanh.lop}`} style={{ width: `${thanh.rong}%` }} />
            </span>
          )}
          <span
            className={`w-14 text-right text-sm font-bold tabular-nums ${
              tienDo ? lopMucKpi(tienDo.achievement_percent) : "text-ink-2"
            }`}
          >
            {tienDo ? phanTramKpi(tienDo.achievement_percent) : DAU_GACH}
          </span>
        </div>
      </Td>

      <Td className="text-right">
        {onSua && (
          <MenuHanhDong
            nhan={`Thao tác với mục tiêu của ${tenDoiTuong}`}
            muc={[{ nhan: t("kpi.suaMucTieu"), icon: Pencil, onChon: onSua }]}
          />
        )}
      </Td>
    </Tr>
  );
}
