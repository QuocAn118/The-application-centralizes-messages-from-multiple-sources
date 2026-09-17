"use client";

/**
 * Màn Báo cáo Ca & KPI (#F5): số ca, giờ công, %KPI theo nhân viên.
 *
 * `kpi_percent`/`period` đi CẶP, ba hình dạng đo thật:
 * - `null`/`null` → chưa đặt target → dấu gạch cả hai ô.
 * - `0.0`/`"2026-09"` → đã đo, 0% → "0%" + kỳ.
 * - `>0`/`"2026-09"` → phần trăm + kỳ.
 * `period` là kỳ KPI (tháng của `to`), KHÔNG phải cả khoảng báo cáo — hiện riêng
 * một cột để không nhập nhằng.
 */

import { useQuery } from "@tanstack/react-query";
import { t } from "@/lib/i18n";
import { DAU_GACH, khoangThoiGian, phanTramKpiSo, soDem, tenNguoi } from "@/lib/hien-thi";
import { baoCaoCaKpi, khoaBaoCao } from "@/lib/bao-cao-api";
import { KhungBaoCao, type ThamSoBaoCao } from "./khung-bao-cao";
import { BangBaoCao } from "./bang-bao-cao";
import { useTenMap } from "./use-ten-map";

function Bang({ khoang, phong }: ThamSoBaoCao) {
  const tenMap = useTenMap();
  const truyVan = useQuery({
    queryKey: khoaBaoCao.caKpi(khoang, phong),
    queryFn: ({ signal }) => baoCaoCaKpi(khoang, phong, signal),
  });

  return (
    <BangBaoCao
      truyVan={truyVan}
      tieuDeCot={
        <>
          <th scope="col" className="px-4 py-3">{t("baoCao.cotNhanVien")}</th>
          <th scope="col" className="px-4 py-3 text-right">{t("baoCao.cotSoCa")}</th>
          <th scope="col" className="px-4 py-3 text-right">{t("baoCao.cotGioCong")}</th>
          <th scope="col" className="px-4 py-3 text-right">{t("baoCao.cotKpi")}</th>
          <th scope="col" className="px-4 py-3 whitespace-nowrap">{t("baoCao.cotKy")}</th>
        </>
      }
    >
      {(rows) => (
        <>
          {rows.map((r) => (
            <tr key={r.user_id} className="border-b border-border-subtle last:border-0">
              <td className="px-4 py-3 text-sm text-foreground">{tenNguoi(tenMap.nguoi, r.user_id)}</td>
              <td className="px-4 py-3 text-right text-sm text-foreground">{soDem(r.shift_count)}</td>
              <td className="px-4 py-3 text-right text-sm text-foreground">{khoangThoiGian(r.worked_seconds)}</td>
              <td className="px-4 py-3 text-right text-sm text-foreground">{phanTramKpiSo(r.kpi_percent)}</td>
              {/* period null <=> kpi null (chưa có target); hiện dấu gạch, không ô trắng. */}
              <td className="px-4 py-3 text-sm text-muted">{r.period ?? DAU_GACH}</td>
            </tr>
          ))}
        </>
      )}
    </BangBaoCao>
  );
}

export function ManCaKpi() {
  return <KhungBaoCao>{(thamSo) => <Bang {...thamSo} />}</KhungBaoCao>;
}
