"use client";

/**
 * Màn Báo cáo Đơn từ (#F5): đơn theo (phòng, loại, trạng thái) + thời gian duyệt.
 *
 * `avg_decision_seconds=null` khi chưa có đơn đã quyết (CHO_DUYET/DA_HUY) → dấu
 * gạch, không "0 giây". Dùng lại badge loại/trạng thái của #F3.
 */

import { useQuery } from "@tanstack/react-query";
import { t } from "@/lib/i18n";
import {
  LOP_BADGE_TRANG_THAI_DON,
  NHAN_LOAI_DON,
  NHAN_TRANG_THAI_DON,
  khoangThoiGian,
  soDem,
  tenPhong,
} from "@/lib/hien-thi";
import { baoCaoDonTu, khoaBaoCao } from "@/lib/bao-cao-api";
import type { RequestReportItem } from "@/lib/types";
import { KhungBaoCao, type ThamSoBaoCao } from "./khung-bao-cao";
import { BangBaoCao } from "./bang-bao-cao";
import { useTenMap } from "./use-ten-map";

function Bang({ khoang, phong }: ThamSoBaoCao) {
  const tenMap = useTenMap();
  const truyVan = useQuery({
    queryKey: khoaBaoCao.donTu(khoang, phong),
    queryFn: ({ signal }) => baoCaoDonTu(khoang, phong, signal),
  });

  const tongSo = (rows: RequestReportItem[]) => rows.reduce((s, r) => s + r.count, 0);

  return (
    <BangBaoCao
      truyVan={truyVan}
      tieuDeCot={
        <>
          <th scope="col" className="px-4 py-3">{t("baoCao.cotPhong")}</th>
          <th scope="col" className="px-4 py-3">{t("baoCao.cotLoaiDon")}</th>
          <th scope="col" className="px-4 py-3">{t("baoCao.cotTrangThai")}</th>
          <th scope="col" className="px-4 py-3 text-right">{t("baoCao.cotSoLuong")}</th>
          <th scope="col" className="px-4 py-3 text-right whitespace-nowrap">{t("baoCao.cotDuyetTB")}</th>
        </>
      }
    >
      {(rows) => (
        <>
          {rows.map((r, i) => (
            <tr key={`${r.department_id}-${r.request_type}-${r.status}-${i}`} className="border-b border-border-subtle last:border-0">
              <td className="px-4 py-3 text-sm text-foreground">{tenPhong(tenMap.phong, r.department_id)}</td>
              <td className="px-4 py-3 text-sm text-foreground">{NHAN_LOAI_DON[r.request_type]}</td>
              <td className="px-4 py-3">
                <span className={`whitespace-nowrap rounded-full px-2.5 py-1 text-xs font-medium ${LOP_BADGE_TRANG_THAI_DON[r.status]}`}>
                  {NHAN_TRANG_THAI_DON[r.status]}
                </span>
              </td>
              <td className="px-4 py-3 text-right text-sm text-foreground">{soDem(r.count)}</td>
              <td className="px-4 py-3 text-right text-sm text-foreground">{khoangThoiGian(r.avg_decision_seconds)}</td>
            </tr>
          ))}
          <tr className="border-t-2 border-border-subtle bg-surface/40 text-sm font-semibold text-foreground">
            <td className="px-4 py-3" colSpan={3}>{t("baoCao.tongCong")}</td>
            <td className="px-4 py-3 text-right">{soDem(tongSo(rows))}</td>
            <td className="px-4 py-3" />
          </tr>
        </>
      )}
    </BangBaoCao>
  );
}

export function ManDonTu() {
  return <KhungBaoCao>{(thamSo) => <Bang {...thamSo} />}</KhungBaoCao>;
}
