"use client";

/**
 * Màn Báo cáo Ca & KPI (#F5; redesign Phần 5 B4): thẻ tóm tắt + bảng theo nhân viên.
 *
 * `kpi_percent`/`period` đi CẶP, ba hình dạng đo thật:
 * - `null`/`null` → chưa đặt target → dấu gạch cả hai ô.
 * - `0.0`/`"2026-09"` → đã đo, 0% → "0%" + kỳ.
 * - `>0`/`"2026-09"` → phần trăm + kỳ.
 * `period` là kỳ KPI (tháng của `to`), KHÔNG phải cả khoảng báo cáo — hiện riêng
 * một cột để không nhập nhằng.
 *
 * Thẻ "Đạt KPI" chỉ đếm trên người CÓ mục tiêu (null không phải "chưa đạt").
 */

import { useQuery } from "@tanstack/react-query";
import { CalendarDays, Clock3, Target } from "lucide-react";
import { t } from "@/lib/i18n";
import { DAU_GACH, khoangThoiGian, phanTramKpiSo, soDem, tenNguoi, thanhKpi } from "@/lib/hien-thi";
import { baoCaoCaKpi, khoaBaoCao } from "@/lib/bao-cao-api";
import { Td, Th, Tr } from "@/components/ui/bang";
import { KhungBaoCao, type ThamSoBaoCao } from "./khung-bao-cao";
import { BangBaoCao } from "./bang-bao-cao";
import { HangTheSo, TheSo } from "./the-so";
import { useTenMap } from "./use-ten-map";

function NoiDung({ khoang, phong }: ThamSoBaoCao) {
  const tenMap = useTenMap();
  const truyVan = useQuery({
    queryKey: khoaBaoCao.caKpi(khoang, phong),
    queryFn: ({ signal }) => baoCaoCaKpi(khoang, phong, signal),
  });
  const rows = truyVan.data ?? [];
  const coKpi = rows.filter((r) => r.kpi_percent !== null);
  const datKpi = coKpi.filter((r) => (r.kpi_percent ?? 0) >= 100);

  return (
    <>
      {rows.length > 0 && (
        <HangTheSo nhan={t("baoCao.tomTat")}>
          <TheSo
            icon={CalendarDays}
            nhan={t("baoCao.theSoCa")}
            giaTri={soDem(rows.reduce((s, r) => s + r.shift_count, 0))}
          />
          <TheSo
            icon={Clock3}
            nhan={t("baoCao.theGioCong")}
            giaTri={khoangThoiGian(rows.reduce((s, r) => s + r.worked_seconds, 0))}
          />
          <TheSo
            icon={Target}
            nhan={t("baoCao.theDatKpi")}
            giaTri={coKpi.length ? `${soDem(datKpi.length)}/${soDem(coKpi.length)}` : DAU_GACH}
            phu={coKpi.length ? t("baoCao.theDatKpiPhu") : t("baoCao.theDatKpiChuaCo")}
          />
        </HangTheSo>
      )}
      <BangBaoCao
        truyVan={truyVan}
        nhan={t("baoCao.tabCaKpi")}
        tieuDeCot={
          <>
            <Th>{t("baoCao.cotNhanVien")}</Th>
            <Th className="text-right">{t("baoCao.cotSoCa")}</Th>
            <Th className="text-right">{t("baoCao.cotGioCong")}</Th>
            <Th className="w-56 text-right">{t("baoCao.cotKpi")}</Th>
            <Th className="whitespace-nowrap">{t("baoCao.cotKy")}</Th>
          </>
        }
      >
        {(ds) =>
          ds.map((r) => {
            // null ≠ 0%: không có mục tiêu thì chỉ "—", không vẽ thanh rỗng (như màn KPI).
            const thanh = thanhKpi(r.kpi_percent);
            return (
              <Tr key={r.user_id}>
                <Td className="font-bold">{tenNguoi(tenMap.nguoi, r.user_id)}</Td>
                <Td className="text-right tabular-nums">{soDem(r.shift_count)}</Td>
                <Td className="text-right tabular-nums">{khoangThoiGian(r.worked_seconds)}</Td>
                <Td>
                  <div className="flex items-center justify-end gap-3">
                    {thanh && (
                      <span aria-hidden className="h-3 w-24 overflow-hidden rounded-[3px] border-2 border-ink bg-sunken">
                        <span className={`block h-full ${thanh.lop}`} style={{ width: `${thanh.rong}%` }} />
                      </span>
                    )}
                    <span className="w-12 text-right font-bold tabular-nums">{phanTramKpiSo(r.kpi_percent)}</span>
                  </div>
                </Td>
                <Td className="text-ink-2">{r.period ?? DAU_GACH}</Td>
              </Tr>
            );
          })
        }
      </BangBaoCao>
    </>
  );
}

export function ManCaKpi() {
  return (
    <KhungBaoCao tieuDe={t("baoCao.tabCaKpi")} moTa={t("baoCao.moTaCaKpi")}>
      {(thamSo) => <NoiDung {...thamSo} />}
    </KhungBaoCao>
  );
}
