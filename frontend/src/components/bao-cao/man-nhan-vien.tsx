"use client";

/**
 * Màn Báo cáo Nhân viên (#F5; redesign Phần 5 B4): thẻ tóm tắt + bảng hiệu suất.
 *
 * Thẻ tóm tắt tính từ chính dữ liệu bảng đã tải (không gọi thêm API). Không có
 * thẻ "phản hồi TB" cho cả nhóm: báo cáo chỉ trả trung bình TỪNG người, không có
 * số mẫu, nên không gộp đúng được (trung bình của trung bình sẽ sai) — con số
 * đúng có sẵn ở thẻ "Phản hồi đầu TB" của tab Hội thoại (BE-8, có trọng số).
 */

import { useQuery } from "@tanstack/react-query";
import { Inbox, UserCheck, Users } from "lucide-react";
import { t } from "@/lib/i18n";
import { khoangThoiGian, soDem, tenNguoi } from "@/lib/hien-thi";
import { baoCaoNhanVien, khoaBaoCao } from "@/lib/bao-cao-api";
import type { AgentReportItem } from "@/lib/types";
import { Td, Th, Tr } from "@/components/ui/bang";
import { KhungBaoCao, type ThamSoBaoCao } from "./khung-bao-cao";
import { BangBaoCao, DongTong } from "./bang-bao-cao";
import { HangTheSo, TheSo } from "./the-so";
import { useTenMap } from "./use-ten-map";

const tong = (rows: AgentReportItem[], key: "handled_count" | "assigned_count") =>
  rows.reduce((s, r) => s + r[key], 0);

function NoiDung({ khoang, phong }: ThamSoBaoCao) {
  const tenMap = useTenMap();
  const truyVan = useQuery({
    queryKey: khoaBaoCao.nhanVien(khoang, phong),
    queryFn: ({ signal }) => baoCaoNhanVien(khoang, phong, signal),
  });
  const rows = truyVan.data ?? [];

  return (
    <>
      {rows.length > 0 && (
        <HangTheSo nhan={t("baoCao.tomTat")}>
          <TheSo icon={Inbox} nhan={t("baoCao.theDaXuLy")} giaTri={soDem(tong(rows, "handled_count"))} />
          <TheSo icon={UserCheck} nhan={t("baoCao.theDuocGan")} giaTri={soDem(tong(rows, "assigned_count"))} />
          <TheSo
            icon={Users}
            nhan={t("baoCao.theNhanVien")}
            giaTri={soDem(rows.length)}
            phu={t("baoCao.theNhanVienPhu")}
          />
        </HangTheSo>
      )}
      <BangBaoCao
        truyVan={truyVan}
        nhan={t("baoCao.tabNhanVien")}
        tieuDeCot={
          <>
            <Th>{t("baoCao.cotNhanVien")}</Th>
            <Th className="text-right">{t("baoCao.cotXuLy")}</Th>
            <Th className="text-right">{t("baoCao.cotDuocGan")}</Th>
            <Th className="whitespace-nowrap text-right">{t("baoCao.cotPhanHoiDau")}</Th>
            <Th className="whitespace-nowrap text-right">{t("baoCao.cotXuLyXong")}</Th>
          </>
        }
      >
        {(ds) => (
          <>
            {ds.map((r) => (
              <Tr key={r.user_id}>
                <Td className="font-bold">{tenNguoi(tenMap.nguoi, r.user_id)}</Td>
                <Td className="text-right tabular-nums">{soDem(r.handled_count)}</Td>
                <Td className="text-right tabular-nums">{soDem(r.assigned_count)}</Td>
                <Td className="text-right tabular-nums">{khoangThoiGian(r.avg_first_response_seconds)}</Td>
                <Td className="text-right tabular-nums">{khoangThoiGian(r.avg_resolution_seconds)}</Td>
              </Tr>
            ))}
            <DongTong>
              <Td>{t("baoCao.tongCong")}</Td>
              <Td className="text-right tabular-nums">{soDem(tong(ds, "handled_count"))}</Td>
              <Td className="text-right tabular-nums">{soDem(tong(ds, "assigned_count"))}</Td>
              {/* Trung bình thời gian không cộng dồn được (mỗi người mẫu khác nhau). */}
              <Td colSpan={2} />
            </DongTong>
          </>
        )}
      </BangBaoCao>
    </>
  );
}

export function ManNhanVien() {
  return (
    <KhungBaoCao tieuDe={t("baoCao.tabNhanVien")} moTa={t("baoCao.moTaNhanVien")}>
      {(thamSo) => <NoiDung {...thamSo} />}
    </KhungBaoCao>
  );
}
