"use client";

/**
 * Màn Nhật ký (#F2 GĐ4) — chỉ Admin.
 *
 * **RB-8: chỉ đọc.** Entity `AuditLog` cố ý không có phương thức sửa/xoá, nên
 * màn này không có nút ghi nào. Có một dòng nói rõ điều đó để người dùng không
 * đi tìm nút xoá.
 *
 * Tên người thực hiện: nhật ký chỉ trả `actor_id`, nên tra ngược sang danh sách
 * người dùng đã tải sẵn. Không gọi `GET /users/{id}` cho từng dòng — 25 dòng là
 * 25 lời gọi, mà phần lớn trỏ tới cùng vài người.
 */

import { useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { t } from "@/lib/i18n";
import { NHAN_HANH_DONG, lopBadgeHanhDong, mocDayDu } from "@/lib/hien-thi";
import {
  KICH_THUOC_TRANG,
  khoaQuanTri,
  layDanhSachNguoiDung,
  layNhatKy,
  type ThamSoNhatKy,
} from "@/lib/quan-tri-api";
import { thongDiepLoi } from "@/lib/loi-quan-tri";
import { ThanhPhanTrang } from "@/components/thanh-phan-trang";
import type { AuditAction } from "@/lib/types";

const LOP_SELECT =
  "rounded-lg border border-border-subtle bg-white px-3 py-2 text-sm text-foreground outline-none transition focus:border-primary";

/** Nhóm hành động cho ô chọn, theo đúng tiền tố backend dùng. */
const NHOM: { nhan: string; loai: string }[] = [
  { nhan: t("nhatKy.loaiUser"), loai: "user" },
  { nhan: t("nhatKy.loaiDepartment"), loai: "department" },
  { nhan: t("nhatKy.loaiAuth"), loai: "auth" },
];

const MOI_HANH_DONG = Object.keys(NHAN_HANH_DONG) as AuditAction[];

export function ManNhatKy() {
  const [thamSo, setThamSo] = useState<ThamSoNhatKy>({
    limit: KICH_THUOC_TRANG,
    offset: 0,
  });

  const truyVan = useQuery({
    queryKey: [...khoaQuanTri.nhatKy.all, thamSo],
    queryFn: ({ signal }) => layNhatKy(thamSo, signal),
  });

  // Tải một lần danh sách người dùng để tra tên theo `actor_id`.
  const truyVanNguoiDung = useQuery({
    queryKey: [...khoaQuanTri.nguoiDung.all, "tra-ten"],
    queryFn: ({ signal }) => layDanhSachNguoiDung({ limit: 100, offset: 0 }, signal),
  });

  const tenTheoId = useMemo(
    () => new Map((truyVanNguoiDung.data?.items ?? []).map((u) => [u.id, u.full_name])),
    [truyVanNguoiDung.data],
  );

  function doiThamSo(phan: Partial<ThamSoNhatKy>) {
    setThamSo((truoc) => ({ ...truoc, ...phan, offset: 0 }));
  }

  const trang = truyVan.data;
  const coLoc =
    thamSo.action !== undefined ||
    thamSo.resource_type !== undefined ||
    thamSo.from_time !== undefined ||
    thamSo.to_time !== undefined;

  return (
    <div className="px-6 py-6">
      <div className="mb-4 flex items-center justify-between gap-4">
        <h2 className="text-base font-semibold text-foreground">{t("nhatKy.tieuDe")}</h2>
        <p className="text-xs text-muted">{t("nhatKy.chiDoc")}</p>
      </div>

      <div className="overflow-hidden rounded-lg border border-border-subtle bg-white">
        <div className="flex flex-wrap items-end gap-3 border-b border-border-subtle px-4 py-3">
          <label className="block">
            <span className="mb-1 block text-xs font-medium text-muted">
              {t("nhatKy.locHanhDong")}
            </span>
            <select
              value={thamSo.action ?? ""}
              onChange={(e) =>
                doiThamSo({ action: (e.target.value || undefined) as AuditAction | undefined })
              }
              className={LOP_SELECT}
            >
              <option value="">{t("quanTri.tatCa")}</option>
              {MOI_HANH_DONG.map((hd) => (
                <option key={hd} value={hd}>
                  {NHAN_HANH_DONG[hd]}
                </option>
              ))}
            </select>
          </label>

          <label className="block">
            <span className="mb-1 block text-xs font-medium text-muted">
              {t("nhatKy.locLoaiDoiTuong")}
            </span>
            <select
              value={thamSo.resource_type ?? ""}
              onChange={(e) => doiThamSo({ resource_type: e.target.value || undefined })}
              className={LOP_SELECT}
            >
              <option value="">{t("quanTri.tatCa")}</option>
              {NHOM.map((n) => (
                <option key={n.loai} value={n.loai}>
                  {n.nhan}
                </option>
              ))}
            </select>
          </label>

          <label className="block">
            <span className="mb-1 block text-xs font-medium text-muted">
              {t("nhatKy.locTuNgay")}
            </span>
            <input
              type="date"
              value={thamSo.from_time?.slice(0, 10) ?? ""}
              onChange={(e) =>
                doiThamSo({
                  // Ô `date` cho ra "2026-09-16"; backend nhận datetime nên gắn
                  // đầu ngày. Không dùng `new Date(...)`: nó diễn giải chuỗi
                  // trần là UTC và ngày sẽ lệch với người ở múi giờ khác.
                  from_time: e.target.value ? `${e.target.value}T00:00:00` : undefined,
                })
              }
              className={LOP_SELECT}
            />
          </label>

          <label className="block">
            <span className="mb-1 block text-xs font-medium text-muted">
              {t("nhatKy.locDenNgay")}
            </span>
            <input
              type="date"
              value={thamSo.to_time?.slice(0, 10) ?? ""}
              onChange={(e) =>
                doiThamSo({
                  // Cuối ngày, không phải đầu ngày: chọn "đến 16/09" mà gửi
                  // 00:00 thì mất hết bản ghi của chính ngày 16.
                  to_time: e.target.value ? `${e.target.value}T23:59:59` : undefined,
                })
              }
              className={LOP_SELECT}
            />
          </label>

          {coLoc && (
            <button
              type="button"
              onClick={() =>
                setThamSo({ limit: KICH_THUOC_TRANG, offset: 0 })
              }
              className="rounded-lg border border-border-subtle px-3 py-2 text-xs font-medium text-muted transition hover:bg-surface"
            >
              {t("nhatKy.xoaLoc")}
            </button>
          )}
        </div>

        {truyVan.isPending && (
          <p className="px-5 py-10 text-center text-sm text-muted">{t("chung.dangTai")}</p>
        )}

        {truyVan.isError && (
          <div className="px-5 py-10 text-center">
            <p className="text-sm text-danger-fg">{thongDiepLoi(truyVan.error)}</p>
            <button
              type="button"
              onClick={() => void truyVan.refetch()}
              className="mt-3 rounded-lg border border-border-subtle px-3 py-1.5 text-xs font-medium text-foreground transition hover:bg-surface"
            >
              {t("chung.thuLai")}
            </button>
          </div>
        )}

        {trang && trang.items.length === 0 && (
          <p className="px-5 py-10 text-center text-sm text-muted">{t("quanTri.trong")}</p>
        )}

        {trang && trang.items.length > 0 && (
          <>
            <table className="w-full border-collapse text-left">
              <thead>
                <tr className="border-b border-border-subtle bg-surface/60 text-[11px] font-bold uppercase tracking-wider text-muted">
                  <th scope="col" className="w-44 px-5 py-3.5">
                    {t("nhatKy.cotThoiGian")}
                  </th>
                  <th scope="col" className="w-64 px-4 py-3.5">
                    {t("nhatKy.cotHanhDong")}
                  </th>
                  <th scope="col" className="w-48 px-4 py-3.5">
                    {t("nhatKy.cotNguoiThucHien")}
                  </th>
                  <th scope="col" className="px-4 py-3.5">{t("nhatKy.cotDoiTuong")}</th>
                </tr>
              </thead>
              <tbody>
                {trang.items.map((dong) => (
                  <tr key={dong.id} className="border-b border-border-subtle last:border-0">
                    <td className="whitespace-nowrap px-5 py-3 text-xs text-muted">
                      {mocDayDu(dong.created_at)}
                    </td>
                    <td className="px-4 py-3">
                      <span
                        className={`inline-block rounded-full px-2.5 py-1 text-xs font-medium ${lopBadgeHanhDong(dong.action)}`}
                      >
                        {NHAN_HANH_DONG[dong.action]}
                      </span>
                    </td>
                    <td className="px-4 py-3 text-sm text-foreground">
                      {dong.actor_id
                        ? // Người thực hiện có thể đã bị xoá khỏi trang hiện tại
                          // của danh sách; khi đó hiện "Không rõ" thay vì UUID
                          // trần, vốn chẳng nói gì với người đọc.
                          (tenTheoId.get(dong.actor_id) ?? t("nhatKy.khongRo"))
                        : // `actor_id` rỗng = hệ thống tự làm (ví dụ đăng nhập
                          // thất bại: chưa biết là ai).
                          t("nhatKy.heThong")}
                    </td>
                    <td className="px-4 py-3">
                      <span className="block text-sm text-foreground">
                        {dong.resource_type}
                      </span>
                      {dong.resource_id && (
                        <span className="block truncate font-mono text-xs text-muted">
                          {dong.resource_id}
                        </span>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
            <ThanhPhanTrang
              offset={trang.offset}
              limit={trang.limit}
              total={trang.total}
              dangTai={truyVan.isFetching}
              doiOffset={(offsetMoi) =>
                setThamSo((truoc) => ({ ...truoc, offset: offsetMoi }))
              }
            />
          </>
        )}
      </div>
    </div>
  );
}
