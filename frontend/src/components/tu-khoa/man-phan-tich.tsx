"use client";

/**
 * Màn Phân tích AI (#F4 GĐ2; trả nợ N6) — **mọi vai**, chỉ đọc.
 *
 * Không có nút nào sửa dữ liệu: kết quả do AI tự chạy nền khi có hội thoại mới.
 * (Endpoint chạy lại `POST /conversations/{id}/analyses` cố ý KHÔNG dựng ở đây
 * — xem RB-10: nó thuộc về màn Hộp thư, và có nợ phạm vi đã biết.)
 *
 * **Ba `outcome` có BA hình dạng `null` khác nhau** — chỗ dễ vỡ nhất của màn
 * này, vì dữ liệu thật gần như chỉ có một nhánh (`AUTO_ASSIGNED`). Đã gieo sẵn
 * hai nhánh kia vào DB dev để kiểm chứng được bằng trình duyệt:
 *
 * | outcome | phòng đề xuất | độ tin cậy | nhu cầu |
 * |---|---|---|---|
 * | `AUTO_ASSIGNED` | có | có | có |
 * | `AMBIGUOUS` | **null** | có | có |
 * | `NOT_ANALYZED` | **null** | **null** | **rỗng** |
 *
 * Nên mọi ô đều phải chịu được `null` và hiện dấu gạch — không hiện `0%` (sai
 * nghĩa: "đã đo và bằng không") cũng không hiện tên phòng rỗng.
 */

import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { t } from "@/lib/i18n";
import Link from "next/link";
import { MessageSquare, Sparkles, TriangleAlert } from "lucide-react";
import { NHAN_KET_QUA_PHAN_TICH, canXemLai, doTinCay, mocDayDu } from "@/lib/hien-thi";
import { mocTuongDoi } from "@/lib/hop-thu";
import { khoaQuanTri, layDanhSachPhongBan } from "@/lib/quan-tri-api";
import {
  KICH_THUOC_TRANG_PHAN_TICH,
  khoaTuKhoa,
  layDanhSachPhanTich,
} from "@/lib/tu-khoa-api";
import { thongDiepLoi } from "@/lib/loi-quan-tri";
import { ThanhPhanTrang } from "@/components/thanh-phan-trang";
import { Bang, Td, Th, Tr } from "@/components/ui/bang";
import { DauTrang } from "@/components/ui/dau-trang";
import { The } from "@/components/ui/the";
import { HuyHieu, type TongHuyHieu } from "@/components/ui/huy-hieu";
import { TrangThaiLoi, TrangThaiRong, TrangThaiTai } from "@/components/ui/trang-thai";
import type { AnalysisOutcome } from "@/lib/types";

/**
 * `AUTO_ASSIGNED` tốt (xanh); `AMBIGUOUS` cần người xem (vàng); `NOT_ANALYZED`
 * xám — KHÔNG đỏ: không phân tích được thường là chưa đủ tin nhắn, không phải lỗi.
 */
const TONG_KET_QUA: Record<AnalysisOutcome, TongHuyHieu> = {
  AUTO_ASSIGNED: "ok",
  AMBIGUOUS: "wait",
  NOT_ANALYZED: "trung",
};

export function ManPhanTich() {
  const [offset, setOffset] = useState(0);

  const truyVan = useQuery({
    queryKey: khoaTuKhoa.phanTich.trang(offset),
    queryFn: ({ signal }) =>
      layDanhSachPhanTich({ limit: KICH_THUOC_TRANG_PHAN_TICH, offset }, signal),
  });

  const truyVanPhongBan = useQuery({
    queryKey: khoaQuanTri.phongBan.all,
    queryFn: ({ signal }) => layDanhSachPhongBan(signal),
    retry: false,
  });

  const phongBan = truyVanPhongBan.data?.items ?? [];
  const danhSach = truyVan.data?.items ?? [];

  const bayGio = new Date();
  const soCanXemLai = danhSach.filter((pt) => canXemLai(pt.outcome)).length;

  return (
    <div className="mx-auto flex max-w-[1440px] flex-col gap-5 px-8 py-6">
      <DauTrang tieuDe={t("phanTich.tieuDe")} moTa={t("phanTich.chiDoc")} />

      {truyVan.isPending && (
        <The>
          <TrangThaiTai />
        </The>
      )}
      {truyVan.isError && (
        <The>
          <TrangThaiLoi thongDiep={thongDiepLoi(truyVan.error)} onThuLai={() => void truyVan.refetch()} />
        </The>
      )}
      {truyVan.data && danhSach.length === 0 && (
        <The>
          <TrangThaiRong icon={Sparkles} tieuDe={t("phanTich.chuaCo")} />
        </The>
      )}

      {/* A2 (phần làm được không cần backend): dòng cần người xem được tô và
          đếm trên trang. Lọc thật cần `GET /analyses?outcome=` — danh sách phân
          trang nên lọc tại client chỉ lọc được trang đang xem, sẽ nói dối. */}
      {soCanXemLai > 0 && (
        <p className="flex items-center gap-2 text-sm text-ink">
          <HuyHieu tong="wait">
            <TriangleAlert aria-hidden className="size-3.5" strokeWidth={2.5} />
            {t("phanTich.canXemLai")}
          </HuyHieu>
          {t("phanTich.demCanXemLai", { so: soCanXemLai })}
        </p>
      )}

      {danhSach.length > 0 && (
        <Bang aria-label={t("phanTich.tieuDe")}>
          <thead>
            <tr>
              <Th>{t("phanTich.cotKetQua")}</Th>
              <Th>{t("phanTich.cotPhongDeXuat")}</Th>
              <Th className="text-right">{t("phanTich.cotTinCay")}</Th>
              <Th>{t("phanTich.cotNhuCau")}</Th>
              <Th className="whitespace-nowrap">{t("phanTich.cotThoiDiem")}</Th>
              <Th>{t("phanTich.cotHoiThoai")}</Th>
            </tr>
          </thead>
          <tbody>
            {danhSach.map((pt) => {
              const phong =
                pt.suggested_department_id === null
                  ? null
                  : (phongBan.find((p) => p.id === pt.suggested_department_id)?.name ??
                    t("nhatKy.khongRo"));
              const xemLai = canXemLai(pt.outcome);
              return (
                <Tr key={pt.id} className={xemLai ? "bg-wait-bg/50" : ""}>
                  <Td>
                    <span className="flex flex-wrap items-center gap-1.5">
                      <HuyHieu tong={TONG_KET_QUA[pt.outcome]}>{NHAN_KET_QUA_PHAN_TICH[pt.outcome]}</HuyHieu>
                      {xemLai && <span className="sr-only">{t("phanTich.canXemLai")}</span>}
                    </span>
                  </Td>

                  {/* `null` = LLM không chọn được phòng. Hiện câu giải thích
                      thay vì ô trắng — ô trắng trông như lỗi tải. */}
                  <Td>
                    {phong === null ? (
                      <span className="text-ink-2">{t("phanTich.khongRoPhong")}</span>
                    ) : (
                      <span className="font-semibold">{phong}</span>
                    )}
                  </Td>

                  <Td className="text-right tabular-nums">{doTinCay(pt.confidence)}</Td>

                  {/* `NOT_ANALYZED` không trích được gì -> mảng RỖNG. */}
                  <Td>
                    {pt.extracted_terms.length === 0 ? (
                      <span className="text-xs text-ink-2">{t("phanTich.khongCoNhuCau")}</span>
                    ) : (
                      <div className="flex flex-wrap gap-1">
                        {/* Khoá theo vị trí: `normalized` KHÔNG bảo đảm duy nhất
                            trong một bản ghi (LLM có thể trả hai cụm khác chữ
                            nhưng cùng dạng chuẩn hoá), mà danh sách này chỉ đọc
                            nên vị trí là ổn định. */}
                        {pt.extracted_terms.map((term, i) => (
                          <span
                            key={`${pt.id}-${i}`}
                            className="rounded-[4px] border border-line bg-sunken px-2 py-0.5 text-xs text-ink"
                            title={term.normalized}
                          >
                            {term.text}
                          </span>
                        ))}
                      </div>
                    )}
                  </Td>

                  <Td className="whitespace-nowrap text-xs text-ink-2">
                    <time dateTime={pt.created_at} title={mocDayDu(pt.created_at)}>
                      {mocTuongDoi(pt.created_at, bayGio)}
                    </time>
                  </Td>

                  {/* A1: mở đúng hội thoại được phân tích. Quyền xem do Hộp thư
                      kiểm; ngoài phạm vi thì Hộp thư tự hiện lỗi. */}
                  <Td>
                    <Link
                      href={`/inbox/${pt.conversation_id}`}
                      aria-label={`${t("phanTich.moHoiThoai")} (${mocDayDu(pt.created_at)})`}
                      className="inline-flex items-center gap-1 whitespace-nowrap font-semibold text-ink underline decoration-2 underline-offset-2 hover:bg-accent"
                    >
                      <MessageSquare aria-hidden className="size-4" strokeWidth={2.25} />
                      {t("phanTich.moHoiThoai")}
                    </Link>
                  </Td>
                </Tr>
              );
            })}
          </tbody>
        </Bang>
      )}

      {truyVan.data && truyVan.data.total > 0 && (
        <ThanhPhanTrang
          offset={offset}
          limit={KICH_THUOC_TRANG_PHAN_TICH}
          total={truyVan.data.total}
          doiOffset={setOffset}
          dangTai={truyVan.isFetching}
        />
      )}
    </div>
  );
}
