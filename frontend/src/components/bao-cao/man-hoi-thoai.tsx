"use client";

/**
 * Màn Báo cáo Hội thoại (#F5): khối lượng tin theo (phòng, kênh).
 *
 * `department_id=null` xuất hiện thật (hội thoại `CHO_PHAN` chưa phân phòng) →
 * `tenPhong` hiện "Chưa phân phòng", không để ô trắng. Các count luôn là số.
 */

import { useQuery } from "@tanstack/react-query";
import { t } from "@/lib/i18n";
import { LOP_BADGE_KENH, NHAN_KENH, soDem, tenPhong } from "@/lib/hien-thi";
import { baoCaoHoiThoai, khoaBaoCao } from "@/lib/bao-cao-api";
import type { ConversationReportItem } from "@/lib/types";
import { KhungBaoCao, type ThamSoBaoCao } from "./khung-bao-cao";
import { BangBaoCao } from "./bang-bao-cao";
import { useTenMap } from "./use-ten-map";

function Bang({ khoang, phong }: ThamSoBaoCao) {
  const tenMap = useTenMap();
  const truyVan = useQuery({
    queryKey: khoaBaoCao.hoiThoai(khoang, phong),
    queryFn: ({ signal }) => baoCaoHoiThoai(khoang, phong, signal),
  });

  const tong = (rows: ConversationReportItem[], key: keyof ConversationReportItem) =>
    rows.reduce((s, r) => s + (r[key] as number), 0);

  return (
    <BangBaoCao
      truyVan={truyVan}
      tieuDeCot={
        <>
          <th scope="col" className="px-4 py-3">{t("baoCao.cotPhong")}</th>
          <th scope="col" className="px-4 py-3">{t("baoCao.cotKenh")}</th>
          <th scope="col" className="px-4 py-3 text-right">{t("baoCao.cotDenVao")}</th>
          <th scope="col" className="px-4 py-3 text-right">{t("baoCao.cotGuiRa")}</th>
          <th scope="col" className="px-4 py-3 text-right">{t("baoCao.cotMoMoi")}</th>
          <th scope="col" className="px-4 py-3 text-right">{t("baoCao.cotDaDong")}</th>
        </>
      }
    >
      {(rows) => (
        <>
          {rows.map((r, i) => (
            <tr key={`${r.department_id}-${r.channel_platform}-${i}`} className="border-b border-border-subtle last:border-0">
              <td className="px-4 py-3 text-sm text-foreground">{tenPhong(tenMap.phong, r.department_id)}</td>
              <td className="px-4 py-3">
                <span className={`whitespace-nowrap rounded-full px-2.5 py-1 text-xs font-medium ${LOP_BADGE_KENH[r.channel_platform]}`}>
                  {NHAN_KENH[r.channel_platform]}
                </span>
              </td>
              <td className="px-4 py-3 text-right text-sm text-foreground">{soDem(r.inbound_count)}</td>
              <td className="px-4 py-3 text-right text-sm text-foreground">{soDem(r.outbound_count)}</td>
              <td className="px-4 py-3 text-right text-sm text-foreground">{soDem(r.opened_count)}</td>
              <td className="px-4 py-3 text-right text-sm text-foreground">{soDem(r.closed_count)}</td>
            </tr>
          ))}
          <tr className="border-t-2 border-border-subtle bg-surface/40 text-sm font-semibold text-foreground">
            <td className="px-4 py-3" colSpan={2}>{t("baoCao.tongCong")}</td>
            <td className="px-4 py-3 text-right">{soDem(tong(rows, "inbound_count"))}</td>
            <td className="px-4 py-3 text-right">{soDem(tong(rows, "outbound_count"))}</td>
            <td className="px-4 py-3 text-right">{soDem(tong(rows, "opened_count"))}</td>
            <td className="px-4 py-3 text-right">{soDem(tong(rows, "closed_count"))}</td>
          </tr>
        </>
      )}
    </BangBaoCao>
  );
}

export function ManHoiThoai() {
  return <KhungBaoCao>{(thamSo) => <Bang {...thamSo} />}</KhungBaoCao>;
}
