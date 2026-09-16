"use client";

/**
 * Màn KPI (#F3 GĐ3): mục tiêu theo kỳ + tiến độ thực đạt.
 *
 * **Kỳ luôn là cặp năm+tháng.** `GET /kpi-targets` chỉ dựng `KpiPeriod` khi có
 * **đủ cả hai** tham số; gửi mỗi `period_year` thì bộ lọc bị bỏ qua **trong im
 * lặng** và trả về mọi kỳ — đã xác nhận bằng lời gọi thật (gửi lẻ năm ra 2 dòng
 * của hai kỳ khác nhau). Nên ở đây hai ô chọn luôn có giá trị, không bao giờ để
 * trống một cái.
 *
 * Phạm vi dữ liệu do backend lọc (`ListKpiTargets`): Staff chỉ thấy mục tiêu áp
 * cho chính mình, Manager thấy cả phòng, Admin thấy tất cả.
 */

import { useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { t } from "@/lib/i18n";
import { useAuth } from "@/lib/auth-context";
import { NHAN_DOI_TUONG_KPI, kyKpi } from "@/lib/hien-thi";
import { khoaNhanSu, layMucTieuKpi, layTienDoKpiTheoKy } from "@/lib/nhan-su-api";
import { khoaQuanTri, layDanhSachNguoiDung, layDanhSachPhongBan } from "@/lib/quan-tri-api";
import { datDuocMucTieuKpi } from "@/lib/quyen-nhan-su";
import { thongDiepLoi } from "@/lib/loi-quan-tri";
import { HangKpi } from "./hang-kpi";
import { HopThoaiKpi } from "./hop-thoai-kpi";
import type { KpiProgress, KpiTarget } from "@/lib/types";

const LOP_O_CHON =
  "rounded-lg border border-border-subtle bg-white px-3 py-1.5 text-xs font-medium text-foreground outline-none transition focus:border-primary";

/** Tháng 1–12. */
const THANG = Array.from({ length: 12 }, (_, i) => i + 1);

export function ManKpi() {
  const { user } = useAuth();
  const homNay = new Date();
  const [nam, setNam] = useState(homNay.getFullYear());
  const [thang, setThang] = useState(homNay.getMonth() + 1);
  const [dangSua, setDangSua] = useState<KpiTarget | null>(null);
  const [dangDat, setDangDat] = useState(false);

  const truyVan = useQuery({
    queryKey: [...khoaNhanSu.kpi.all, "danh-sach", nam, thang],
    queryFn: ({ signal }) => layMucTieuKpi({ nam, thang }, signal),
  });

  // Tiến độ CẢ BẢNG trong một lời gọi (trả nợ N4). Trước đây mỗi dòng tự gọi
  // `/kpi-progress` của riêng nó: 68 dòng = 68 lời gọi, ~3,2 giây. Backend lọc
  // phạm vi theo vai nên không cần truyền đối tượng, và Staff cũng không dò
  // được KPI người khác.
  const truyVanTienDo = useQuery({
    queryKey: khoaNhanSu.kpi.tienDoKy(nam, thang),
    queryFn: ({ signal }) => layTienDoKpiTheoKy({ nam, thang }, signal),
  });

  // Tên đối tượng: mục tiêu chỉ có `subject_id` thuần, không kèm tên. Staff bị
  // chặn `GET /users` (403) nên `retry: false` — khi đó rơi về mã rút gọn.
  const truyVanNguoiDung = useQuery({
    queryKey: [...khoaQuanTri.nguoiDung.all, "tra-ten"],
    queryFn: ({ signal }) => layDanhSachNguoiDung({ limit: 100, offset: 0 }, signal),
    retry: false,
  });

  const truyVanPhongBan = useQuery({
    queryKey: khoaQuanTri.phongBan.all,
    queryFn: ({ signal }) => layDanhSachPhongBan(signal),
    retry: false,
  });

  const moiNguoi = useMemo(
    () => truyVanNguoiDung.data?.items ?? [],
    [truyVanNguoiDung.data],
  );
  const phongBan = useMemo(
    () => truyVanPhongBan.data?.items ?? [],
    [truyVanPhongBan.data],
  );

  if (!user) return null;

  const datDuoc = datDuocMucTieuKpi(user.role);
  const danhSach = truyVan.data ?? [];

  // Tra tiến độ theo (đối tượng, chỉ số) — khoá gồm cả chỉ số vì một đối tượng
  // có thể có mục tiêu cho cả hai chỉ số.
  const tienDoTheoKhoa = new Map<string, KpiProgress>(
    (truyVanTienDo.data ?? []).map((p) => [`${p.subject_id}|${p.metric_type}`, p]),
  );

  // Năm chọn được: quanh năm nay. Mục tiêu là thứ đặt cho kỳ sắp tới hoặc xem
  // lại kỳ đã qua, không cần cả thế kỷ.
  const cacNam = [homNay.getFullYear() - 1, homNay.getFullYear(), homNay.getFullYear() + 1];

  function tenDoiTuong(mt: KpiTarget): string {
    if (mt.subject_type === "DEPARTMENT") {
      const p = phongBan.find((x) => x.id === mt.subject_id);
      return p ? `${p.name} (${NHAN_DOI_TUONG_KPI.DEPARTMENT})` : NHAN_DOI_TUONG_KPI.DEPARTMENT;
    }
    const u = moiNguoi.find((x) => x.id === mt.subject_id);
    if (u) return u.id === user!.id ? `${u.full_name} ${t("don.chinhBan")}` : u.full_name;
    // Staff không tra được tên người khác — nhưng mục tiêu Staff thấy được chỉ
    // có của chính họ, nên đây gần như luôn là bản thân.
    return mt.subject_id === user!.id ? user!.full_name : t("nhatKy.khongRo");
  }

  // Nhân viên đặt mục tiêu được: Manager chỉ trong phòng mình (backend trả
  // `MANAGER_WRONG_DEPARTMENT`), Admin thì mọi người đang hoạt động có phòng.
  const nhanVienDatDuoc = moiNguoi.filter(
    (u) =>
      u.is_active &&
      u.department_id !== null &&
      (user.role === "ADMIN" || u.department_id === user.department_id),
  );
  const phongDatDuoc =
    user.role === "ADMIN"
      ? phongBan.filter((p) => p.is_active)
      : phongBan.filter((p) => p.id === user.department_id);

  return (
    <div className="px-6 py-6">
      <section className="overflow-hidden rounded-lg border border-border-subtle bg-white">
        <div className="flex flex-wrap items-center justify-between gap-3 border-b border-border-subtle px-5 py-3">
          <h2 className="text-base font-semibold text-foreground">{t("kpi.tieuDe")}</h2>

          <div className="flex items-center gap-2">
            <label className="flex items-center gap-1.5">
              <span className="text-xs text-muted">{t("kpi.chonThang")}</span>
              <select
                value={thang}
                onChange={(e) => setThang(Number(e.target.value))}
                className={LOP_O_CHON}
              >
                {THANG.map((m) => (
                  <option key={m} value={m}>
                    {m}
                  </option>
                ))}
              </select>
            </label>
            <label className="flex items-center gap-1.5">
              <span className="text-xs text-muted">{t("kpi.chonNam")}</span>
              <select
                value={nam}
                onChange={(e) => setNam(Number(e.target.value))}
                className={LOP_O_CHON}
              >
                {cacNam.map((y) => (
                  <option key={y} value={y}>
                    {y}
                  </option>
                ))}
              </select>
            </label>

            {datDuoc && (
              <button
                type="button"
                onClick={() => setDangDat(true)}
                className="rounded-lg bg-primary px-4 py-2 text-sm font-semibold text-white transition hover:brightness-95"
              >
                + {t("kpi.datMucTieu")}
              </button>
            )}
          </div>
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
          <p className="px-5 py-8 text-center text-sm text-muted">
            {t("kpi.chuaCoMucTieu")}
          </p>
        )}

        {danhSach.length > 0 && (
          <div className="overflow-x-auto">
            <table className="w-full border-collapse text-left">
              <thead>
                <tr className="border-b border-border-subtle bg-surface/60 text-[11px] font-bold uppercase tracking-wider text-muted">
                  <th scope="col" className="px-4 py-3">
                    {t("kpi.cotDoiTuong")}
                  </th>
                  <th scope="col" className="px-4 py-3">
                    {t("kpi.cotChiSo")}
                  </th>
                  <th scope="col" className="px-4 py-3 text-right">
                    {t("kpi.cotMucTieu")}
                  </th>
                  <th scope="col" className="px-4 py-3 text-right">
                    {t("kpi.cotThucDat")}
                  </th>
                  <th scope="col" className="px-4 py-3 text-right">
                    {t("kpi.cotHoanThanh")}
                  </th>
                  <th scope="col" className="w-24 px-4 py-3" />
                </tr>
              </thead>
              <tbody>
                {danhSach.map((mt) => (
                  <HangKpi
                    key={mt.id}
                    mucTieu={mt}
                    tenDoiTuong={tenDoiTuong(mt)}
                    tienDo={tienDoTheoKhoa.get(`${mt.subject_id}|${mt.metric_type}`)}
                    dangTai={truyVanTienDo.isPending}
                    onSua={datDuoc ? () => setDangSua(mt) : null}
                  />
                ))}
              </tbody>
            </table>
          </div>
        )}

        <p className="border-t border-border-subtle bg-surface/40 px-5 py-2.5 text-xs text-muted">
          {kyKpi(nam, thang)} · {t("kpi.ghiChuThucDat")}
        </p>
      </section>

      {(dangDat || dangSua) && (
        <HopThoaiKpi
          sua={dangSua}
          vai={user.role}
          nam={nam}
          thang={thang}
          nhanVien={nhanVienDatDuoc}
          phongBan={phongDatDuoc}
          onDong={() => {
            setDangDat(false);
            setDangSua(null);
          }}
        />
      )}
    </div>
  );
}
