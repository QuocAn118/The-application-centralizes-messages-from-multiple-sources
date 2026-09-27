"use client";

/**
 * Màn Từ khoá (#F4 GĐ1; trả nợ N6) — **mọi vai**.
 *
 * Nhóm theo phòng vì từ khoá chỉ có nghĩa trong ngữ cảnh phòng: "bảo hành" của
 * Kỹ thuật và của Kinh doanh là hai thứ khác nhau, và AI dùng cả danh mục của
 * từng phòng để chọn nơi phân hội thoại.
 *
 * **Phạm vi do backend lọc** (`pham_vi_phong_doc`): Admin thấy mọi phòng,
 * Manager/Staff chỉ phòng mình. FE không lọc lại — lọc chồng chỉ tạo cơ hội lệch.
 *
 * **Staff XEM được, chỉ không SỬA được** (`GET /keywords` trả 200 cho Staff;
 * `POST/PATCH/DELETE` mới 403 `KEYWORD_MANAGER_REQUIRED`). Trước đây màn này
 * nằm trong `/quan-tri` nên Staff bị chặn ở cửa — nợ N6, nay đã tách khu riêng.
 *
 * Redesign Phần 4 (T1–T3): mỗi phòng một thẻ, từ khoá là chip; bấm chip để
 * sửa, × để xoá (có xác nhận), ô thêm nhanh cuối dãy. Nút "Thêm từ khoá" trên
 * đầu trang vẫn giữ: đó là đường duy nhất thêm vào phòng CHƯA có từ khoá nào
 * (phòng rỗng không có thẻ, nên không có ô thêm nhanh).
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
import { Plus, Tags } from "lucide-react";
import { OTimKiem } from "@/components/o-tim-kiem";
import { DauTrang } from "@/components/ui/dau-trang";
import { The } from "@/components/ui/the";
import { Nut } from "@/components/ui/nut";
import { TrangThaiLoi, TrangThaiRong, TrangThaiTai } from "@/components/ui/trang-thai";
import { HopXacNhan } from "@/components/hop-xac-nhan";
import { quanLyDuocTuKhoa } from "@/lib/quyen-tu-khoa";
import { HopThoaiTuKhoa } from "./hop-thoai-tu-khoa";
import { ChipTuKhoa, OThemNhanh } from "./chip-tu-khoa";
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
  // Id từ khoá đang có mà lần thêm nhanh vừa rồi trùng với (409 details) — tô chip đó.
  const [chipTrung, setChipTrung] = useState<string | null>(null);

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

  // Staff không sửa được gì (`KEYWORD_MANAGER_REQUIRED`) nên không hiện nút nào.
  const suaDuocNoiChung = quanLyDuocTuKhoa(user.role);

  // Manager chỉ thêm được cho phòng mình; Admin cho mọi phòng đang hoạt động.
  const phongThemDuoc = !suaDuocNoiChung
    ? []
    : user.role === "ADMIN"
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
    suaDuocNoiChung &&
    (user.role === "ADMIN" || k.department_id === user.department_id);

  // Phòng có từ khoá, theo thứ tự của danh sách phòng ban; phòng lạ (đã ngừng
  // chẳng hạn) vẫn phải hiện, nếu không từ khoá của nó biến mất không dấu vết.
  // Phòng mình thêm được thì hiện cả khi RỖNG (trừ lúc đang tìm): thẻ rỗng là
  // chỗ duy nhất có ô thêm nhanh cho phòng đó.
  const idCoTuKhoa = [...theoPhong.keys()];
  const phongHien = [
    ...phongBan
      .filter((p) => theoPhong.has(p.id) || (!tim && phongThemDuoc.some((x) => x.id === p.id)))
      .map((p) => ({ id: p.id, ten: p.name })),
    ...idCoTuKhoa
      .filter((id) => !phongBan.some((p) => p.id === id))
      .map((id) => ({ id, ten: t("nguoiDung.khongPhong") })),
  ];

  return (
    <div className="mx-auto flex max-w-[1440px] flex-col gap-5 px-8 py-6">
      <DauTrang
        tieuDe={t("tuKhoa.tieuDe")}
        moTa={t("tuKhoa.moTaTrang")}
        hanhDong={
          <>
            <OTimKiem nhanGoiY={t("tuKhoa.timGoiY")} doiTuKhoa={setTim} />
            {phongThemDuoc.length > 0 && (
              <Nut bienThe="chinh" icon={Plus} onClick={() => setDangMo({ loai: "them" })}>
                {t("tuKhoa.them")}
              </Nut>
            )}
          </>
        }
      />

      {truyVan.isPending && (
        <The>
          <TrangThaiTai dong={3} />
        </The>
      )}
      {truyVan.isError && (
        <The>
          <TrangThaiLoi thongDiep={thongDiepLoi(truyVan.error)} onThuLai={() => void truyVan.refetch()} />
        </The>
      )}
      {truyVan.data && theoPhong.size === 0 && (tim || phongHien.length === 0) && (
        <The>
          <TrangThaiRong
            icon={Tags}
            tieuDe={tim ? t("tuKhoa.khongKhopTim") : t("tuKhoa.chuaCoTieuDe")}
            moTa={tim ? undefined : suaDuocNoiChung ? t("tuKhoa.chuaCo") : t("tuKhoa.chuaCoChiXem")}
            hanhDong={
              !tim &&
              phongThemDuoc.length > 0 && (
                <Nut icon={Plus} onClick={() => setDangMo({ loai: "them" })}>
                  {t("tuKhoa.them")}
                </Nut>
              )
            }
          />
        </The>
      )}

      {phongHien.map((phong) => {
        const ds = theoPhong.get(phong.id) ?? [];
        const themNhanhDuoc = phongThemDuoc.some((p) => p.id === phong.id);
        return (
          <The key={phong.id}>
            <div className="flex items-baseline gap-3 border-b-2 border-ink px-5 py-3">
              <h2 className="text-lg font-bold text-ink">{phong.ten}</h2>
              <span className="text-xs font-semibold text-ink-2">
                {t("tuKhoa.demTrongPhong", { so: String(ds.length) })}
              </span>
            </div>
            <ul
              aria-label={t("tuKhoa.dsCuaPhong", { phong: phong.ten })}
              className="flex flex-wrap items-start gap-2 px-5 py-4"
            >
              {ds.map((k) => (
                <ChipTuKhoa
                  key={k.id}
                  tuKhoa={k}
                  trung={k.id === chipTrung}
                  onSua={suaDuoc(k) ? () => setDangMo({ loai: "sua", tuKhoa: k }) : null}
                  onXoa={suaDuoc(k) ? () => setDangMo({ loai: "xoa", tuKhoa: k }) : null}
                />
              ))}
              {ds.length === 0 && (
                <li className="self-center text-sm text-ink-2">{t("tuKhoa.chuaCoTrongPhong")}</li>
              )}
              {/* Đang tìm thì ẩn ô thêm: thêm giữa lúc lọc dễ tưởng từ mới "biến mất". */}
              {themNhanhDuoc && !tim && <OThemNhanh phongId={phong.id} tenPhong={phong.ten} onTrung={setChipTrung} />}
            </ul>
          </The>
        );
      })}

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
