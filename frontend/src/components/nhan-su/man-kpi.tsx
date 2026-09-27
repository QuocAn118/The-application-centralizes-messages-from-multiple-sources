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
import { ChevronLeft, ChevronRight, Plus, Target } from "lucide-react";
import { useQuery } from "@tanstack/react-query";
import { t } from "@/lib/i18n";
import { useAuth } from "@/lib/auth-context";
import { NHAN_DOI_TUONG_KPI, doiKy, kyKpi } from "@/lib/hien-thi";
import { khoaNhanSu, layMucTieuKpi, layTienDoKpiTheoKy } from "@/lib/nhan-su-api";
import { khoaQuanTri, layDanhSachNguoiDung, layDanhSachPhongBan } from "@/lib/quan-tri-api";
import { datDuocMucTieuKpi } from "@/lib/quyen-nhan-su";
import { thongDiepLoi } from "@/lib/loi-quan-tri";
import { HangKpi } from "./hang-kpi";
import { HopThoaiKpi } from "./hop-thoai-kpi";
import { Bang, Th } from "@/components/ui/bang";
import { DauTrang } from "@/components/ui/dau-trang";
import { The } from "@/components/ui/the";
import { Nut } from "@/components/ui/nut";
import { NutIcon } from "@/components/ui/nut-icon";
import { TrangThaiLoi, TrangThaiRong, TrangThaiTai } from "@/components/ui/trang-thai";
import type { KpiProgress, KpiTarget } from "@/lib/types";

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

  // K3: ‹ Tháng 9/2026 ›. Luôn đổi CẶP năm+tháng cùng lúc (xem chú thích đầu tệp).
  function sangKy(buoc: number) {
    const moi = doiKy(nam, thang, buoc);
    setNam(moi.nam);
    setThang(moi.thang);
  }
  const laKyNay = nam === homNay.getFullYear() && thang === homNay.getMonth() + 1;

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
    <div className="mx-auto flex max-w-[1440px] flex-col gap-5 px-8 py-6">
      <DauTrang
        tieuDe={t("kpi.tieuDe")}
        moTa={t("kpi.ghiChuThucDat")}
        hanhDong={
          datDuoc && (
            <Nut bienThe="chinh" icon={Plus} onClick={() => setDangDat(true)}>
              {t("kpi.datMucTieu")}
            </Nut>
          )
        }
      />

      <div role="group" aria-label={t("kpi.chonKy")} className="flex items-center gap-2">
        <NutIcon icon={ChevronLeft} nhan="Tháng trước" onClick={() => sangKy(-1)} />
        <span aria-live="polite" className="min-w-40 text-center text-lg font-extrabold text-ink">
          {kyKpi(nam, thang)}
        </span>
        <NutIcon icon={ChevronRight} nhan="Tháng sau" onClick={() => sangKy(1)} />
        {!laKyNay && (
          <Nut
            co="sm"
            bienThe="trong"
            onClick={() => {
              setNam(homNay.getFullYear());
              setThang(homNay.getMonth() + 1);
            }}
          >
            Về tháng này
          </Nut>
        )}
      </div>

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
          <TrangThaiRong
            icon={Target}
            tieuDe={t("kpi.chuaCoMucTieu")}
            hanhDong={
              datDuoc && (
                <Nut icon={Plus} onClick={() => setDangDat(true)}>
                  {t("kpi.datMucTieu")}
                </Nut>
              )
            }
          />
        </The>
      )}

      {danhSach.length > 0 && (
        <Bang aria-label={`${t("kpi.tieuDe")} ${kyKpi(nam, thang)}`}>
          <thead>
            <tr>
              <Th>{t("kpi.cotDoiTuong")}</Th>
              <Th>{t("kpi.cotChiSo")}</Th>
              <Th className="text-right">{t("kpi.cotMucTieu")}</Th>
              <Th className="text-right">{t("kpi.cotThucDat")}</Th>
              <Th className="w-56 text-right">{t("kpi.cotHoanThanh")}</Th>
              <Th className="w-16">
                <span className="sr-only">{t("nguoiDung.thaoTac")}</span>
              </Th>
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
        </Bang>
      )}

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
