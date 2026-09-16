"use client";

/**
 * Màn Phân tích AI (#F4 GĐ2) — chỉ đọc.
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
import {
  LOP_BADGE_KET_QUA_PHAN_TICH,
  NHAN_KET_QUA_PHAN_TICH,
  doTinCay,
  mocNgan,
  mocDayDu,
} from "@/lib/hien-thi";
import { khoaQuanTri, layDanhSachPhongBan } from "@/lib/quan-tri-api";
import {
  KICH_THUOC_TRANG_PHAN_TICH,
  khoaTuKhoa,
  layDanhSachPhanTich,
} from "@/lib/tu-khoa-api";
import { thongDiepLoi } from "@/lib/loi-quan-tri";
import { ThanhPhanTrang } from "@/components/thanh-phan-trang";

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

  return (
    <div className="space-y-4 px-6 py-6">
      <section className="overflow-hidden rounded-lg border border-border-subtle bg-white">
        <div className="flex flex-wrap items-center justify-between gap-3 border-b border-border-subtle px-5 py-3">
          <h2 className="text-base font-semibold text-foreground">{t("phanTich.tieuDe")}</h2>
          <span className="text-xs text-muted">{t("phanTich.chiDoc")}</span>
        </div>

        {truyVan.isPending && (
          <p className="px-5 py-8 text-center text-sm text-muted">{t("chung.dangTai")}</p>
        )}
        {truyVan.isError && (
          <p className="px-5 py-8 text-center text-sm text-danger-fg">
            {thongDiepLoi(truyVan.error)}
          </p>
        )}
        {truyVan.data && danhSach.length === 0 && (
          <p className="px-5 py-8 text-center text-sm text-muted">{t("phanTich.chuaCo")}</p>
        )}

        {danhSach.length > 0 && (
          <div className="overflow-x-auto">
            <table className="w-full border-collapse text-left">
              <thead>
                <tr className="border-b border-border-subtle bg-surface/60 text-[11px] font-bold uppercase tracking-wider text-muted">
                  <th scope="col" className="px-4 py-3">
                    {t("phanTich.cotKetQua")}
                  </th>
                  <th scope="col" className="px-4 py-3">
                    {t("phanTich.cotPhongDeXuat")}
                  </th>
                  <th scope="col" className="px-4 py-3 text-right">
                    {t("phanTich.cotTinCay")}
                  </th>
                  <th scope="col" className="px-4 py-3">
                    {t("phanTich.cotNhuCau")}
                  </th>
                  <th scope="col" className="px-4 py-3 whitespace-nowrap">
                    {t("phanTich.cotThoiDiem")}
                  </th>
                </tr>
              </thead>
              <tbody>
                {danhSach.map((pt) => {
                  const phong =
                    pt.suggested_department_id === null
                      ? null
                      : (phongBan.find((p) => p.id === pt.suggested_department_id)?.name ??
                        t("nhatKy.khongRo"));
                  return (
                    <tr key={pt.id} className="border-b border-border-subtle last:border-0">
                      <td className="px-4 py-3">
                        <span
                          className={`whitespace-nowrap rounded-full px-2.5 py-1 text-xs font-medium ${
                            LOP_BADGE_KET_QUA_PHAN_TICH[pt.outcome]
                          }`}
                        >
                          {NHAN_KET_QUA_PHAN_TICH[pt.outcome]}
                        </span>
                      </td>

                      {/* `null` = LLM không chọn được phòng. Hiện câu giải
                          thích thay vì ô trắng — ô trắng trông như lỗi tải. */}
                      <td className="px-4 py-3 text-sm">
                        {phong === null ? (
                          <span className="text-muted">{t("phanTich.khongRoPhong")}</span>
                        ) : (
                          <span className="text-foreground">{phong}</span>
                        )}
                      </td>

                      <td className="px-4 py-3 text-right text-sm text-foreground">
                        {doTinCay(pt.confidence)}
                      </td>

                      {/* `NOT_ANALYZED` không trích được gì -> mảng RỖNG. */}
                      <td className="px-4 py-3">
                        {pt.extracted_terms.length === 0 ? (
                          <span className="text-xs text-muted">
                            {t("phanTich.khongCoNhuCau")}
                          </span>
                        ) : (
                          <div className="flex flex-wrap gap-1">
                            {/* Khoá theo vị trí: `normalized` KHÔNG bảo đảm duy
                                nhất trong một bản ghi (LLM có thể trả hai cụm
                                khác chữ nhưng cùng dạng chuẩn hoá), mà danh
                                sách này chỉ đọc nên vị trí là ổn định. */}
                            {pt.extracted_terms.map((term, i) => (
                              <span
                                key={`${pt.id}-${i}`}
                                className="rounded-md bg-surface px-2 py-0.5 text-xs text-foreground"
                                title={term.normalized}
                              >
                                {term.text}
                              </span>
                            ))}
                          </div>
                        )}
                      </td>

                      <td className="px-4 py-3 whitespace-nowrap text-xs text-muted">
                        <span title={mocDayDu(pt.created_at)}>{mocNgan(pt.created_at)}</span>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
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
      </section>
    </div>
  );
}
