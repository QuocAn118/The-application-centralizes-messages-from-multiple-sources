"use client";

/**
 * Màn Từ khoá (#F4 GĐ1) — Manager (phòng mình) và Admin.
 *
 * Nhóm theo phòng vì từ khoá chỉ có nghĩa trong ngữ cảnh phòng: "bảo hành" của
 * Kỹ thuật và của Kinh doanh là hai thứ khác nhau, và AI dùng cả danh mục của
 * từng phòng để chọn nơi phân hội thoại.
 *
 * **Phạm vi do backend lọc** (`pham_vi_phong_doc`): Admin thấy mọi phòng,
 * Manager chỉ phòng mình. FE không lọc lại — lọc chồng chỉ tạo cơ hội lệch.
 *
 * `GET /keywords` trả **mảng trần**, không phân trang: danh mục từ khoá mỗi
 * phòng vốn ngắn (vài chục), nên lọc tại client cho gọn.
 */

import { useMemo, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { t } from "@/lib/i18n";
import { useAuth } from "@/lib/auth-context";
import { khoaQuanTri, layDanhSachPhongBan } from "@/lib/quan-tri-api";
import { khoaTuKhoa, layDanhSachTuKhoa, xoaTuKhoa } from "@/lib/tu-khoa-api";
import { thongDiepLoi } from "@/lib/loi-quan-tri";
import { OTimKiem } from "@/components/o-tim-kiem";
import { HopXacNhan } from "@/components/hop-xac-nhan";
import { HopThoaiTuKhoa } from "./hop-thoai-tu-khoa";
import type { Keyword } from "@/lib/types";

type DangMo =
  | { loai: "them" }
  | { loai: "sua"; tuKhoa: Keyword }
  | { loai: "xoa"; tuKhoa: Keyword }
  | null;

export function ManTuKhoa() {
  const { user } = useAuth();
  const queryClient = useQueryClient();
  const [tim, setTim] = useState("");
  const [dangMo, setDangMo] = useState<DangMo>(null);

  const truyVan = useQuery({
    queryKey: khoaTuKhoa.tuKhoa.all,
    queryFn: ({ signal }) => layDanhSachTuKhoa(signal),
  });

  const truyVanPhongBan = useQuery({
    queryKey: khoaQuanTri.phongBan.all,
    queryFn: ({ signal }) => layDanhSachPhongBan(signal),
    retry: false,
  });

  const xoa = useMutation({
    mutationFn: (keywordId: string) => xoaTuKhoa(keywordId),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: khoaTuKhoa.tuKhoa.all });
      setDangMo(null);
    },
  });

  const phongBan = useMemo(
    () => truyVanPhongBan.data?.items ?? [],
    [truyVanPhongBan.data],
  );

  // Lọc theo cả `text` lẫn `normalized`: gõ "bao hanh" phải tìm ra "Bảo Hành".
  const danhSach = useMemo(() => {
    const ds = truyVan.data ?? [];
    const tu = tim.trim().toLowerCase();
    if (!tu) return ds;
    return ds.filter(
      (k) => k.text.toLowerCase().includes(tu) || k.normalized.includes(tu),
    );
  }, [truyVan.data, tim]);

  // Nhóm theo phòng, giữ thứ tự phòng ban để danh sách không nhảy mỗi lần tải.
  const theoPhong = useMemo(() => {
    const nhom = new Map<string, Keyword[]>();
    for (const k of danhSach) {
      const cu = nhom.get(k.department_id);
      if (cu) cu.push(k);
      else nhom.set(k.department_id, [k]);
    }
    return nhom;
  }, [danhSach]);

  if (!user) return null;

  // Manager chỉ thêm được cho phòng mình; Admin cho mọi phòng đang hoạt động.
  const phongThemDuoc =
    user.role === "ADMIN"
      ? phongBan.filter((p) => p.is_active)
      : phongBan.filter((p) => p.id === user.department_id);

  /**
   * Sửa/xoá được từ khoá này không — chép đúng `bao_dam_quan_ly_dung_phong`:
   * Admin mọi phòng, Manager đúng phòng mình (`KEYWORD_OUT_OF_SCOPE`).
   *
   * Suy từ `user` chứ KHÔNG từ `phongThemDuoc`: danh sách phòng đến từ một
   * truy vấn khác (`/departments`, `retry: false`), hỏng truy vấn đó thì nút
   * Thêm biến mất là đúng, nhưng Sửa/Xoá thì không được biến mất theo — quyền
   * sửa không phụ thuộc việc tải được danh sách phòng.
   */
  const suaDuoc = (k: Keyword) =>
    user.role === "ADMIN" || k.department_id === user.department_id;

  // Phòng có từ khoá, theo thứ tự của danh sách phòng ban; phòng lạ (đã ngừng
  // chẳng hạn) vẫn phải hiện, nếu không từ khoá của nó biến mất không dấu vết.
  const idCoTuKhoa = [...theoPhong.keys()];
  const phongHien = [
    ...phongBan
      .filter((p) => theoPhong.has(p.id))
      .map((p) => ({ id: p.id, ten: p.name })),
    ...idCoTuKhoa
      .filter((id) => !phongBan.some((p) => p.id === id))
      .map((id) => ({ id, ten: t("nguoiDung.khongPhong") })),
  ];

  return (
    <div className="space-y-4 px-6 py-6">
      <section className="overflow-hidden rounded-lg border border-border-subtle bg-white">
        <div className="flex flex-wrap items-center justify-between gap-3 border-b border-border-subtle px-5 py-3">
          <h2 className="text-base font-semibold text-foreground">
            {t("tuKhoa.tieuDe")}
          </h2>
          <div className="flex items-center gap-2">
            <OTimKiem nhanGoiY={t("tuKhoa.timGoiY")} doiTuKhoa={setTim} />
            {phongThemDuoc.length > 0 && (
              <button
                type="button"
                onClick={() => setDangMo({ loai: "them" })}
                className="whitespace-nowrap rounded-lg bg-primary px-4 py-2 text-sm font-semibold text-white transition hover:brightness-95"
              >
                + {t("tuKhoa.them")}
              </button>
            )}
          </div>
        </div>

        {truyVan.isPending && (
          <p className="px-5 py-8 text-center text-sm text-muted">
            {t("chung.dangTai")}
          </p>
        )}
        {truyVan.isError && (
          <p className="px-5 py-8 text-center text-sm text-danger-fg">
            {thongDiepLoi(truyVan.error)}
          </p>
        )}
        {truyVan.data && phongHien.length === 0 && (
          <p className="px-5 py-8 text-center text-sm text-muted">
            {t("tuKhoa.chuaCo")}
          </p>
        )}

        {phongHien.map((phong) => {
          const ds = theoPhong.get(phong.id) ?? [];
          return (
            <div
              key={phong.id}
              className="border-b border-border-subtle last:border-0"
            >
              <div className="flex items-baseline gap-2 bg-surface/50 px-5 py-2">
                <h3 className="text-sm font-semibold text-foreground">
                  {phong.ten}
                </h3>
                <span className="text-xs text-muted">
                  {t("tuKhoa.demTrongPhong", { so: String(ds.length) })}
                </span>
              </div>

              <ul className="divide-y divide-border-subtle">
                {ds.map((k) => (
                  <li
                    key={k.id}
                    className="flex items-center justify-between gap-4 px-5 py-2.5"
                  >
                    <div className="min-w-0">
                      <span className="block truncate text-sm text-foreground">
                        {k.text}
                      </span>
                      {/* Hiện dạng chuẩn hoá: người dùng cần thấy vì sao
                          "Bảo Hành" bị báo trùng khi họ gõ "bao hanh". */}
                      <span className="block truncate text-xs text-muted-soft">
                        {t("tuKhoa.dangKhop", { chuan: k.normalized })}
                      </span>
                    </div>
                    <div className="flex shrink-0 items-center gap-2">
                      {suaDuoc(k) && (
                        <>
                          <button
                            type="button"
                            onClick={() =>
                              setDangMo({ loai: "sua", tuKhoa: k })
                            }
                            className="rounded-lg border border-border-subtle px-3 py-1.5 text-xs font-medium text-foreground transition hover:bg-surface"
                          >
                            {t("tuKhoa.sua")}
                          </button>
                          <button
                            type="button"
                            onClick={() =>
                              setDangMo({ loai: "xoa", tuKhoa: k })
                            }
                            className="rounded-lg border border-border-subtle px-3 py-1.5 text-xs font-medium text-danger-fg transition hover:bg-danger-bg"
                          >
                            {t("tuKhoa.xoa")}
                          </button>
                        </>
                      )}
                    </div>
                  </li>
                ))}
              </ul>
            </div>
          );
        })}
      </section>

      {dangMo?.loai === "them" && (
        <HopThoaiTuKhoa
          tuKhoa={null}
          phongBan={phongThemDuoc}
          phongMacDinh={phongThemDuoc[0]?.id ?? ""}
          onDong={() => setDangMo(null)}
        />
      )}
      {dangMo?.loai === "sua" && (
        <HopThoaiTuKhoa
          tuKhoa={dangMo.tuKhoa}
          phongBan={phongBan}
          phongMacDinh={dangMo.tuKhoa.department_id}
          onDong={() => setDangMo(null)}
        />
      )}
      {dangMo?.loai === "xoa" && (
        <HopXacNhan
          tieuDe={t("tuKhoa.xoa")}
          moTa={t("tuKhoa.xacNhanXoa", { ten: dangMo.tuKhoa.text })}
          nhanXacNhan={t("tuKhoa.xoa")}
          nguyHiem
          dangChay={xoa.isPending}
          loi={xoa.isError ? thongDiepLoi(xoa.error) : null}
          onDong={() => setDangMo(null)}
          onXacNhan={() => xoa.mutate(dangMo.tuKhoa.id)}
        />
      )}
    </div>
  );
}
