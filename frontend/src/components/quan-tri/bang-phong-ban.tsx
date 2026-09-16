"use client";

/**
 * Bảng phòng ban (#F2 task 2.1).
 *
 * Số nhân viên mỗi phòng là một truy vấn riêng cho từng dòng (`GET /users` đọc
 * `total`) vì `DepartmentResponse` không mang sẵn con số đó. Với vài chục phòng
 * thì chấp nhận được; nếu sau này danh sách phòng dài ra thì nên xin backend
 * trả kèm `member_count` thay vì bắn N lời gọi.
 */

import { useQuery } from "@tanstack/react-query";
import { t } from "@/lib/i18n";
import { demNhanVienCuaPhong, khoaQuanTri } from "@/lib/quan-tri-api";
import type { Department } from "@/lib/types";

/** Thao tác chọn từ menu của một dòng. */
export type ThaoTacPhong = "sua" | "ngung";

export function BangPhongBan({
  danhSach,
  laAdmin,
  chonThaoTac,
}: {
  danhSach: Department[];
  laAdmin: boolean;
  chonThaoTac: (thaoTac: ThaoTacPhong, phong: Department) => void;
}) {
  return (
    <table className="w-full border-collapse text-left">
      <thead>
        <tr className="border-b border-border-subtle bg-surface/60 text-[11px] font-bold uppercase tracking-wider text-muted">
          <th scope="col" className="px-5 py-3.5">{t("phongBan.cotTen")}</th>
          <th scope="col" className="w-32 px-4 py-3.5">{t("phongBan.cotSoNhanVien")}</th>
          <th scope="col" className="w-44 px-4 py-3.5">{t("phongBan.cotTrangThai")}</th>
          <th scope="col" className="w-56 px-5 py-3.5 text-right">
            <span className="sr-only">{t("nguoiDung.thaoTac")}</span>
          </th>
        </tr>
      </thead>
      <tbody>
        {danhSach.map((phong) => (
          <tr
            key={phong.id}
            className={`border-b border-border-subtle last:border-0 ${
              phong.is_active ? "" : "bg-surface/40 opacity-60"
            }`}
          >
            <td className="px-5 py-3">
              <span className="block text-sm font-semibold text-foreground">
                {phong.name}
              </span>
              <span className="block truncate text-xs text-muted">
                {phong.description?.trim() || t("phongBan.khongMoTa")}
              </span>
            </td>

            <td className="px-4 py-3">
              <SoNhanVien departmentId={phong.id} />
            </td>

            <td className="px-4 py-3">
              <span
                className={`inline-flex items-center gap-1.5 whitespace-nowrap rounded-full px-2.5 py-1 text-xs font-medium ${
                  phong.is_active
                    ? "bg-dang-mo-bg text-dang-mo-fg"
                    : "bg-da-dong-bg text-da-dong-fg"
                }`}
              >
                <span aria-hidden className="h-1.5 w-1.5 rounded-full bg-current" />
                {phong.is_active
                  ? t("phongBan.dangHoatDong")
                  : t("nguoiDung.daVoHieuHoa")}
              </span>
            </td>

            <td className="px-5 py-3 text-right">
              {laAdmin && (
                <div className="flex justify-end gap-2">
                  <button
                    type="button"
                    onClick={() => chonThaoTac("sua", phong)}
                    className="whitespace-nowrap rounded-lg border border-border-subtle px-3 py-1.5 text-xs font-medium text-foreground transition hover:bg-surface"
                  >
                    {t("phongBan.sua")}
                  </button>
                  {/* Phòng đã ngừng thì không hiện nút: backend KHÔNG có
                      endpoint kích hoạt lại, nên đây là thao tác một chiều. */}
                  {phong.is_active && (
                    <button
                      type="button"
                      onClick={() => chonThaoTac("ngung", phong)}
                      className="whitespace-nowrap rounded-lg border border-border-subtle px-3 py-1.5 text-xs font-medium text-danger-fg transition hover:bg-danger-bg"
                    >
                      {t("phongBan.ngungHoatDong")}
                    </button>
                  )}
                </div>
              )}
            </td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}

/** Số nhân viên đang hoạt động của một phòng. */
function SoNhanVien({ departmentId }: { departmentId: string }) {
  const { data, isPending, isError } = useQuery({
    queryKey: khoaQuanTri.phongBan.demNhanVien(departmentId),
    queryFn: ({ signal }) => demNhanVienCuaPhong(departmentId, signal),
  });

  if (isPending) {
    return <span className="text-xs text-muted-soft">{t("phongBan.dangDemNhanVien")}</span>;
  }
  // Đếm hỏng không được làm vỡ cả bảng — hiện dấu gạch, phần còn lại vẫn dùng được.
  if (isError) return <span className="text-sm text-muted-soft">—</span>;

  return <span className="text-sm text-foreground">{data}</span>;
}
