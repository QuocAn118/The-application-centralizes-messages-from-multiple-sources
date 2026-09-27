"use client";

/**
 * Màn Báo cáo Đơn từ (#F5; redesign Phần 5 B4): thẻ tóm tắt + đơn theo (phòng,
 * loại, trạng thái) + thời gian duyệt.
 *
 * `avg_decision_seconds=null` khi chưa có đơn đã quyết (CHO_DUYET/DA_HUY) → dấu
 * gạch, không "0 giây". Thẻ "Duyệt TB" gộp **có trọng số theo số đơn**.
 */

import { useQuery } from "@tanstack/react-query";
import { FileText, Hourglass, Timer } from "lucide-react";
import { t } from "@/lib/i18n";
import {
  NHAN_LOAI_DON,
  NHAN_TRANG_THAI_DON,
  khoangThoiGian,
  soDem,
  tenPhong,
  trungBinhCoTrongSo,
} from "@/lib/hien-thi";
import { baoCaoDonTu, khoaBaoCao } from "@/lib/bao-cao-api";
import type { RequestReportItem } from "@/lib/types";
import { Td, Th, Tr } from "@/components/ui/bang";
import { HuyHieu } from "@/components/ui/huy-hieu";
import { TONG_TRANG_THAI_DON } from "@/components/nhan-su/bang-don";
import { KhungBaoCao, type ThamSoBaoCao } from "./khung-bao-cao";
import { BangBaoCao, DongTong } from "./bang-bao-cao";
import { HangTheSo, TheSo } from "./the-so";
import { useTenMap } from "./use-ten-map";

const tongSo = (rows: RequestReportItem[]) => rows.reduce((s, r) => s + r.count, 0);

function NoiDung({ khoang, phong }: ThamSoBaoCao) {
  const tenMap = useTenMap();
  const truyVan = useQuery({
    queryKey: khoaBaoCao.donTu(khoang, phong),
    queryFn: ({ signal }) => baoCaoDonTu(khoang, phong, signal),
  });
  const rows = truyVan.data ?? [];
  const dangCho = tongSo(rows.filter((r) => r.status === "CHO_DUYET"));
  const duyetTb = trungBinhCoTrongSo(
    rows.map((r) => ({ trungBinh: r.avg_decision_seconds, soLuong: r.count })),
  );

  return (
    <>
      {rows.length > 0 && (
        <HangTheSo nhan={t("baoCao.tomTat")}>
          <TheSo icon={FileText} nhan={t("baoCao.theTongDon")} giaTri={soDem(tongSo(rows))} />
          <TheSo
            icon={Hourglass}
            nhan={t("baoCao.theChoDuyet")}
            giaTri={soDem(dangCho)}
            phu={t("baoCao.theChoDuyetPhu")}
          />
          <TheSo
            icon={Timer}
            nhan={t("baoCao.theDuyetTB")}
            giaTri={khoangThoiGian(duyetTb)}
            phu={t("baoCao.theDuyetTBPhu")}
          />
        </HangTheSo>
      )}
      <BangBaoCao
        truyVan={truyVan}
        nhan={t("baoCao.tabDonTu")}
        tieuDeCot={
          <>
            <Th>{t("baoCao.cotPhong")}</Th>
            <Th>{t("baoCao.cotLoaiDon")}</Th>
            <Th>{t("baoCao.cotTrangThai")}</Th>
            <Th className="text-right">{t("baoCao.cotSoLuong")}</Th>
            <Th className="whitespace-nowrap text-right">{t("baoCao.cotDuyetTB")}</Th>
          </>
        }
      >
        {(ds) => (
          <>
            {ds.map((r, i) => (
              <Tr key={`${r.department_id}-${r.request_type}-${r.status}-${i}`}>
                <Td className="font-bold">{tenPhong(tenMap.phong, r.department_id)}</Td>
                <Td>{NHAN_LOAI_DON[r.request_type]}</Td>
                <Td>
                  <HuyHieu tong={TONG_TRANG_THAI_DON[r.status]}>{NHAN_TRANG_THAI_DON[r.status]}</HuyHieu>
                </Td>
                <Td className="text-right tabular-nums">{soDem(r.count)}</Td>
                <Td className="text-right tabular-nums">{khoangThoiGian(r.avg_decision_seconds)}</Td>
              </Tr>
            ))}
            <DongTong>
              <Td colSpan={3}>{t("baoCao.tongCong")}</Td>
              <Td className="text-right tabular-nums">{soDem(tongSo(ds))}</Td>
              <Td />
            </DongTong>
          </>
        )}
      </BangBaoCao>
    </>
  );
}

export function ManDonTu() {
  return (
    <KhungBaoCao tieuDe={t("baoCao.tabDonTu")} moTa={t("baoCao.moTaDonTu")}>
      {(thamSo) => <NoiDung {...thamSo} />}
    </KhungBaoCao>
  );
}
