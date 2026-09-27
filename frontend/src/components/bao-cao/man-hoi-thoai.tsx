"use client";

/**
 * Màn Báo cáo Hội thoại (#F5; redesign Phần 5 B1–B3).
 *
 * Thành màn **tổng quan**: 4 thẻ KPI → biểu đồ xu hướng theo ngày → bảng chi
 * tiết theo (phòng, kênh). Thẻ + biểu đồ lấy từ `GET /analytics/overview` (BE-8);
 * bảng giữ `GET /analytics/conversations` như cũ.
 *
 * `department_id=null` xuất hiện thật (hội thoại `CHO_PHAN` chưa phân phòng) →
 * `tenPhong` hiện "Chưa phân phòng", không để ô trắng.
 *
 * **B2:** dòng có tin vào mà 0 tin ra → nền cảnh báo + icon + câu chữ (không chỉ
 * dựa vào màu).
 */

import { useQuery } from "@tanstack/react-query";
import { CheckCheck, Clock3, MessageCircleReply, MessagesSquare, TriangleAlert } from "lucide-react";
import { t } from "@/lib/i18n";
import { chuaAiTraLoi, khoangThoiGian, soDem, tenPhong, tiLePhanTram } from "@/lib/hien-thi";
import { baoCaoHoiThoai, khoaBaoCao, tongQuan } from "@/lib/bao-cao-api";
import { thongDiepLoi } from "@/lib/loi-quan-tri";
import type { ConversationReportItem } from "@/lib/types";
import { BadgeKenh } from "@/components/badges";
import { Td, Th, Tr } from "@/components/ui/bang";
import { The } from "@/components/ui/the";
import { TrangThaiLoi, TrangThaiTai } from "@/components/ui/trang-thai";
import { KhungBaoCao, type ThamSoBaoCao } from "./khung-bao-cao";
import { BangBaoCao, DongTong } from "./bang-bao-cao";
import { BieuDoXuHuong } from "./bieu-do-xu-huong";
import { HangTheSo, TheSo } from "./the-so";
import { useTenMap } from "./use-ten-map";

function TongQuan({ khoang, phong }: ThamSoBaoCao) {
  const truyVan = useQuery({
    queryKey: khoaBaoCao.tongQuan(khoang, phong),
    queryFn: ({ signal }) => tongQuan(khoang, phong, signal),
  });

  if (truyVan.isPending)
    return (
      <The>
        <TrangThaiTai dong={2} />
      </The>
    );
  if (truyVan.isError)
    return (
      <The>
        <TrangThaiLoi thongDiep={thongDiepLoi(truyVan.error)} onThuLai={() => void truyVan.refetch()} />
      </The>
    );

  const d = truyVan.data;
  return (
    <>
      <HangTheSo nhan={t("baoCao.tongQuan")}>
        <TheSo
          icon={MessagesSquare}
          nhan={t("baoCao.theTinVao")}
          giaTri={soDem(d.totals.inbound_count)}
          phu={t("baoCao.theTinVaoPhu", { so: soDem(d.totals.outbound_count) })}
        />
        <TheSo
          icon={MessageCircleReply}
          nhan={t("baoCao.theTiLe")}
          giaTri={tiLePhanTram(d.response_rate)}
          phu={
            d.response_rate === null
              ? t("baoCao.theTiLeChuaDo")
              : t("baoCao.theTiLePhu", {
                  da: soDem(d.conversations_replied),
                  tong: soDem(d.conversations_with_inbound),
                })
          }
        />
        <TheSo
          icon={Clock3}
          nhan={t("baoCao.thePhanHoiDau")}
          giaTri={khoangThoiGian(d.avg_first_response_seconds)}
          phu={
            d.first_response_samples > 0
              ? t("baoCao.thePhanHoiDauPhu", { so: soDem(d.first_response_samples) })
              : t("baoCao.thePhanHoiDauChuaCo")
          }
        />
        <TheSo
          icon={CheckCheck}
          nhan={t("baoCao.theDaDong")}
          giaTri={soDem(d.totals.closed_count)}
          phu={t("baoCao.theDaDongPhu", { so: soDem(d.totals.opened_count) })}
        />
      </HangTheSo>
      <BieuDoXuHuong daily={d.daily} />
    </>
  );
}

function ChiTiet({ khoang, phong }: ThamSoBaoCao) {
  const tenMap = useTenMap();
  const truyVan = useQuery({
    queryKey: khoaBaoCao.hoiThoai(khoang, phong),
    queryFn: ({ signal }) => baoCaoHoiThoai(khoang, phong, signal),
  });

  type KhoaDem = "inbound_count" | "outbound_count" | "opened_count" | "closed_count";
  const tong = (rows: ConversationReportItem[], key: KhoaDem) =>
    rows.reduce((s, r) => s + r[key], 0);

  return (
    <section aria-labelledby="bc-chi-tiet" className="flex flex-col gap-3">
      <h2 id="bc-chi-tiet" className="text-lg font-bold text-ink">
        {t("baoCao.chiTietTheoPhong")}
      </h2>
      <BangBaoCao
        truyVan={truyVan}
        nhan={t("baoCao.chiTietTheoPhong")}
        tieuDeCot={
          <>
            <Th>{t("baoCao.cotPhong")}</Th>
            <Th>{t("baoCao.cotKenh")}</Th>
            <Th className="text-right">{t("baoCao.cotDenVao")}</Th>
            <Th className="text-right">{t("baoCao.cotGuiRa")}</Th>
            <Th className="text-right">{t("baoCao.cotMoMoi")}</Th>
            <Th className="text-right">{t("baoCao.cotDaDong")}</Th>
          </>
        }
      >
        {(rows) => (
          <>
            {rows.map((r, i) => {
              const canhBao = chuaAiTraLoi(r);
              return (
                <Tr
                  key={`${r.department_id}-${r.channel_platform}-${i}`}
                  className={canhBao ? "bg-wait-bg hover:bg-wait-bg" : ""}
                >
                  <Td>
                    <span className="block font-bold">{tenPhong(tenMap.phong, r.department_id)}</span>
                    {canhBao && (
                      <span className="mt-0.5 flex items-center gap-1 text-xs font-bold text-wait">
                        <TriangleAlert aria-hidden className="size-3.5" strokeWidth={2.5} />
                        {t("baoCao.chuaAiTraLoi", { so: soDem(r.inbound_count) })}
                      </span>
                    )}
                  </Td>
                  <Td>
                    <BadgeKenh platform={r.channel_platform} />
                  </Td>
                  <Td className="text-right tabular-nums">{soDem(r.inbound_count)}</Td>
                  <Td className={`text-right tabular-nums ${canhBao ? "font-bold text-wait" : ""}`}>
                    {soDem(r.outbound_count)}
                  </Td>
                  <Td className="text-right tabular-nums">{soDem(r.opened_count)}</Td>
                  <Td className="text-right tabular-nums">{soDem(r.closed_count)}</Td>
                </Tr>
              );
            })}
            <DongTong>
              <Td colSpan={2}>{t("baoCao.tongCong")}</Td>
              <Td className="text-right tabular-nums">{soDem(tong(rows, "inbound_count"))}</Td>
              <Td className="text-right tabular-nums">{soDem(tong(rows, "outbound_count"))}</Td>
              <Td className="text-right tabular-nums">{soDem(tong(rows, "opened_count"))}</Td>
              <Td className="text-right tabular-nums">{soDem(tong(rows, "closed_count"))}</Td>
            </DongTong>
          </>
        )}
      </BangBaoCao>
    </section>
  );
}

export function ManHoiThoai() {
  return (
    <KhungBaoCao tieuDe={t("baoCao.tabHoiThoai")} moTa={t("baoCao.moTaHoiThoai")}>
      {(thamSo) => (
        <>
          <TongQuan {...thamSo} />
          <ChiTiet {...thamSo} />
        </>
      )}
    </KhungBaoCao>
  );
}
