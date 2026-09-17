"use client";

/**
 * Màn Báo cáo Nhân viên (#F5): hiệu suất theo nhân viên.
 *
 * Bẫy tên (đo thật): báo cáo trả `user_id` trần và có thể chứa người Manager
 * KHÔNG tra được tên — người ngoài phòng (`/users/{id}` → 403) hoặc Admin
 * `department_id=null`. `tenNguoi` khi đó trả mã rút gọn, không "undefined".
 *
 * `avg_*_seconds=null` = chưa có mẫu (xuất hiện thật cùng `handled_count>0`) →
 * dấu gạch, không "0 giây".
 */

import { useQuery } from "@tanstack/react-query";
import { t } from "@/lib/i18n";
import { khoangThoiGian, soDem, tenNguoi } from "@/lib/hien-thi";
import { baoCaoNhanVien, khoaBaoCao } from "@/lib/bao-cao-api";
import type { AgentReportItem } from "@/lib/types";
import { KhungBaoCao, type ThamSoBaoCao } from "./khung-bao-cao";
import { BangBaoCao } from "./bang-bao-cao";
import { useTenMap } from "./use-ten-map";

function Bang({ khoang, phong }: ThamSoBaoCao) {
  const tenMap = useTenMap();
  const truyVan = useQuery({
    queryKey: khoaBaoCao.nhanVien(khoang, phong),
    queryFn: ({ signal }) => baoCaoNhanVien(khoang, phong, signal),
  });

  const tong = (rows: AgentReportItem[], key: "handled_count" | "assigned_count") =>
    rows.reduce((s, r) => s + r[key], 0);

  return (
    <BangBaoCao
      truyVan={truyVan}
      tieuDeCot={
        <>
          <th scope="col" className="px-4 py-3">{t("baoCao.cotNhanVien")}</th>
          <th scope="col" className="px-4 py-3 text-right">{t("baoCao.cotXuLy")}</th>
          <th scope="col" className="px-4 py-3 text-right">{t("baoCao.cotDuocGan")}</th>
          <th scope="col" className="px-4 py-3 text-right whitespace-nowrap">{t("baoCao.cotPhanHoiDau")}</th>
          <th scope="col" className="px-4 py-3 text-right whitespace-nowrap">{t("baoCao.cotXuLyXong")}</th>
        </>
      }
    >
      {(rows) => (
        <>
          {rows.map((r) => (
            <tr key={r.user_id} className="border-b border-border-subtle last:border-0">
              <td className="px-4 py-3 text-sm text-foreground">{tenNguoi(tenMap.nguoi, r.user_id)}</td>
              <td className="px-4 py-3 text-right text-sm text-foreground">{soDem(r.handled_count)}</td>
              <td className="px-4 py-3 text-right text-sm text-foreground">{soDem(r.assigned_count)}</td>
              <td className="px-4 py-3 text-right text-sm text-foreground">{khoangThoiGian(r.avg_first_response_seconds)}</td>
              <td className="px-4 py-3 text-right text-sm text-foreground">{khoangThoiGian(r.avg_resolution_seconds)}</td>
            </tr>
          ))}
          <tr className="border-t-2 border-border-subtle bg-surface/40 text-sm font-semibold text-foreground">
            <td className="px-4 py-3">{t("baoCao.tongCong")}</td>
            <td className="px-4 py-3 text-right">{soDem(tong(rows, "handled_count"))}</td>
            <td className="px-4 py-3 text-right">{soDem(tong(rows, "assigned_count"))}</td>
            {/* Trung bình thời gian không cộng dồn được (mỗi người mẫu khác nhau). */}
            <td className="px-4 py-3" colSpan={2} />
          </tr>
        </>
      )}
    </BangBaoCao>
  );
}

export function ManNhanVien() {
  return <KhungBaoCao>{(thamSo) => <Bang {...thamSo} />}</KhungBaoCao>;
}
