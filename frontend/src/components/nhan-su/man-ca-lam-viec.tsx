"use client";

/**
 * Màn Ca làm việc (#F3 GĐ2) — hai phần trên một trang.
 *
 * Trên: **mẫu ca** (khuôn giờ). Dưới: **lịch phân ca** theo tuần (ai làm khuôn
 * nào, ngày nào). Hai thứ luôn được xem cùng nhau: xếp lịch mà không thấy các
 * khuôn giờ hiện có thì phải nhớ trong đầu.
 *
 * Staff chỉ xem: backend trả đúng ca của họ (`ListShiftAssignments` lọc theo
 * `user_ids`), và FE ẩn mọi nút xếp/huỷ.
 */

import { useMemo, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { t } from "@/lib/i18n";
import { useAuth } from "@/lib/auth-context";
import { gioNgan, ngayVN, tuanChua } from "@/lib/hien-thi";
import {
  huyPhanCa,
  khoaNhanSu,
  layDanhSachCa,
  layLichPhanCa,
  ngungCa,
} from "@/lib/nhan-su-api";
import { khoaQuanTri, layDanhSachNguoiDung, layDanhSachPhongBan } from "@/lib/quan-tri-api";
import { quanLyDuocCa } from "@/lib/quyen-nhan-su";
import { thongDiepLoi } from "@/lib/loi-quan-tri";
import { HopXacNhan } from "@/components/hop-xac-nhan";
import { HopThoaiCa } from "./hop-thoai-ca";
import { HopThoaiPhanCa } from "./hop-thoai-phan-ca";
import { LuoiLich } from "./luoi-lich";
import type { Shift, ShiftAssignment } from "@/lib/types";

type DangMo =
  | { loai: "taoCa" }
  | { loai: "suaCa"; ca: Shift }
  | { loai: "ngungCa"; ca: Shift }
  | { loai: "phanCa"; userId: string; ngay: string }
  | { loai: "huyBuoi"; buoi: ShiftAssignment }
  | null;

export function ManCaLamViec() {
  const { user } = useAuth();
  const queryClient = useQueryClient();
  const [mocTuan, setMocTuan] = useState(() => new Date());
  const [dangMo, setDangMo] = useState<DangMo>(null);

  const tuan = useMemo(() => tuanChua(mocTuan), [mocTuan]);
  const tuNgay = tuan[0];
  const denNgay = tuan[6];

  const truyVanCa = useQuery({
    queryKey: khoaNhanSu.ca.all,
    // Không lọc `is_active`: màn quản lý phải thấy cả ca đã ngừng.
    queryFn: ({ signal }) => layDanhSachCa(undefined, signal),
  });

  const truyVanLich = useQuery({
    queryKey: khoaNhanSu.phanCa.khoang(tuNgay, denNgay),
    queryFn: ({ signal }) => layLichPhanCa(tuNgay, denNgay, signal),
  });

  const truyVanNguoiDung = useQuery({
    queryKey: [...khoaQuanTri.nguoiDung.all, "tra-ten"],
    queryFn: ({ signal }) => layDanhSachNguoiDung({ limit: 100, offset: 0 }, signal),
    // Staff bị chặn `GET /users` (403). Khi đó lưới không có hàng nào — nhưng
    // Staff chỉ xem ca của chính mình, nên bổ sung hàng của họ ở dưới.
    retry: false,
  });

  const truyVanPhongBan = useQuery({
    queryKey: khoaQuanTri.phongBan.all,
    queryFn: ({ signal }) => layDanhSachPhongBan(signal),
    retry: false,
  });

  const ngung = useMutation({
    mutationFn: (shiftId: string) => ngungCa(shiftId),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: khoaNhanSu.ca.all });
      setDangMo(null);
    },
  });

  const huy = useMutation({
    mutationFn: (buoiId: string) => huyPhanCa(buoiId),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: khoaNhanSu.phanCa.all });
      setDangMo(null);
    },
  });

  const danhSachCa = useMemo(() => truyVanCa.data ?? [], [truyVanCa.data]);
  const caTheoId = useMemo(
    () => new Map(danhSachCa.map((c) => [c.id, c])),
    [danhSachCa],
  );
  const caDangDung = danhSachCa.filter((c) => c.is_active);

  const moiNguoi = useMemo(
    () => truyVanNguoiDung.data?.items ?? [],
    [truyVanNguoiDung.data],
  );

  if (!user) return null;
  const xepDuoc = quanLyDuocCa(user.role);

  // Hàng của lưới. Manager/Admin: nhân viên trong phạm vi các mẫu ca nhìn thấy
  // được — nếu lấy cả công ty thì Admin sẽ có hàng trăm hàng vô nghĩa.
  const phongCoCa = new Set(danhSachCa.map((c) => c.department_id));
  const nhanVienLuoi = xepDuoc
    ? moiNguoi.filter((u) => u.is_active && u.department_id && phongCoCa.has(u.department_id))
    : // Staff không gọi được `/users`; tự dựng một hàng cho chính mình từ phiên
      // đăng nhập, để họ vẫn thấy ca của mình.
      moiNguoi.filter((u) => u.id === user.id).concat(
        moiNguoi.some((u) => u.id === user.id)
          ? []
          : [
              {
                id: user.id,
                email: user.email,
                full_name: user.full_name,
                phone: user.phone,
                role: user.role,
                department_id: user.department_id,
                is_active: user.is_active,
                must_change_password: user.must_change_password,
                last_login_at: user.last_login_at,
                created_at: user.created_at,
              },
            ],
      );

  const phongBan = truyVanPhongBan.data?.items ?? [];
  // Manager chỉ tạo ca được cho phòng mình; Admin cho mọi phòng đang hoạt động.
  const phongChonDuoc =
    user.role === "ADMIN"
      ? phongBan.filter((p) => p.is_active)
      : phongBan.filter((p) => p.id === user.department_id);

  function doiTuan(soNgay: number) {
    setMocTuan(
      (truoc) =>
        new Date(truoc.getFullYear(), truoc.getMonth(), truoc.getDate() + soNgay),
    );
  }

  return (
    <div className="space-y-6 px-6 py-6">
      {/* ----- Mẫu ca ----- */}
      <section className="overflow-hidden rounded-lg border border-border-subtle bg-white">
        <div className="flex items-center justify-between gap-4 border-b border-border-subtle px-5 py-3">
          <h2 className="text-base font-semibold text-foreground">{t("ca.tieuDe")}</h2>
          {xepDuoc && (
            <button
              type="button"
              onClick={() => setDangMo({ loai: "taoCa" })}
              className="rounded-lg bg-primary px-4 py-2 text-sm font-semibold text-white transition hover:brightness-95"
            >
              + {t("ca.taoMoi")}
            </button>
          )}
        </div>

        {truyVanCa.isPending && (
          <p className="px-5 py-8 text-center text-sm text-muted">{t("chung.dangTai")}</p>
        )}
        {truyVanCa.isError && (
          <p className="px-5 py-8 text-center text-sm text-danger-fg">
            {thongDiepLoi(truyVanCa.error)}
          </p>
        )}
        {truyVanCa.data && danhSachCa.length === 0 && (
          <p className="px-5 py-8 text-center text-sm text-muted">{t("ca.chuaCoCa")}</p>
        )}

        {danhSachCa.length > 0 && (
          <ul className="divide-y divide-border-subtle">
            {danhSachCa.map((ca) => (
              <li
                key={ca.id}
                className={`flex items-center justify-between gap-4 px-5 py-3 ${
                  ca.is_active ? "" : "bg-surface/40 opacity-60"
                }`}
              >
                <div className="min-w-0">
                  <span className="block truncate text-sm font-semibold text-foreground">
                    {ca.name}
                  </span>
                  <span className="block text-xs text-muted">
                    {gioNgan(ca.start_time)}–{gioNgan(ca.end_time)}
                    {" · "}
                    {phongBan.find((p) => p.id === ca.department_id)?.name ??
                      t("nguoiDung.khongPhong")}
                  </span>
                </div>

                <div className="flex shrink-0 items-center gap-2">
                  <span
                    className={`whitespace-nowrap rounded-full px-2.5 py-1 text-xs font-medium ${
                      ca.is_active
                        ? "bg-dang-mo-bg text-dang-mo-fg"
                        : "bg-da-dong-bg text-da-dong-fg"
                    }`}
                  >
                    {ca.is_active ? t("ca.dangDung") : t("ca.daNgung")}
                  </span>
                  {xepDuoc && (
                    <>
                      <button
                        type="button"
                        onClick={() => setDangMo({ loai: "suaCa", ca })}
                        className="whitespace-nowrap rounded-lg border border-border-subtle px-3 py-1.5 text-xs font-medium text-foreground transition hover:bg-surface"
                      >
                        {t("ca.sua")}
                      </button>
                      {/* Ca đã ngừng không hiện nút: backend không có endpoint
                          bật lại, giống phòng ban và kênh ở #F2. */}
                      {ca.is_active && (
                        <button
                          type="button"
                          onClick={() => setDangMo({ loai: "ngungCa", ca })}
                          className="whitespace-nowrap rounded-lg border border-border-subtle px-3 py-1.5 text-xs font-medium text-danger-fg transition hover:bg-danger-bg"
                        >
                          {t("ca.ngung")}
                        </button>
                      )}
                    </>
                  )}
                </div>
              </li>
            ))}
          </ul>
        )}
      </section>

      {/* ----- Lịch phân ca ----- */}
      <section className="overflow-hidden rounded-lg border border-border-subtle bg-white">
        <div className="flex flex-wrap items-center justify-between gap-3 border-b border-border-subtle px-5 py-3">
          <h2 className="text-base font-semibold text-foreground">{t("lich.tieuDe")}</h2>
          <div className="flex items-center gap-2">
            <button
              type="button"
              onClick={() => doiTuan(-7)}
              className="rounded-lg border border-border-subtle px-3 py-1.5 text-xs font-medium text-foreground transition hover:bg-surface"
            >
              ← {t("lich.tuanTruoc")}
            </button>
            <button
              type="button"
              onClick={() => setMocTuan(new Date())}
              className="rounded-lg border border-border-subtle px-3 py-1.5 text-xs font-medium text-foreground transition hover:bg-surface"
            >
              {t("lich.tuanNay")}
            </button>
            <button
              type="button"
              onClick={() => doiTuan(7)}
              className="rounded-lg border border-border-subtle px-3 py-1.5 text-xs font-medium text-foreground transition hover:bg-surface"
            >
              {t("lich.tuanSau")} →
            </button>
            <span className="ml-1 text-xs text-muted">
              {ngayVN(tuNgay)} – {ngayVN(denNgay)}
            </span>
          </div>
        </div>

        {truyVanLich.isPending && (
          <p className="px-5 py-8 text-center text-sm text-muted">{t("chung.dangTai")}</p>
        )}
        {truyVanLich.isError && (
          <p className="px-5 py-8 text-center text-sm text-danger-fg">
            {thongDiepLoi(truyVanLich.error)}
          </p>
        )}

        {truyVanLich.data && nhanVienLuoi.length === 0 && (
          <p className="px-5 py-8 text-center text-sm text-muted">
            {t("lich.khongCoNhanVien")}
          </p>
        )}

        {truyVanLich.data && nhanVienLuoi.length > 0 && (
          <LuoiLich
            tuan={tuan}
            nhanVien={nhanVienLuoi}
            buoi={truyVanLich.data}
            caTheoId={caTheoId}
            xepDuoc={xepDuoc && caDangDung.length > 0}
            onXep={(userId, ngay) => setDangMo({ loai: "phanCa", userId, ngay })}
            onHuy={(buoiCa) => setDangMo({ loai: "huyBuoi", buoi: buoiCa })}
          />
        )}
      </section>

      {dangMo?.loai === "taoCa" && (
        <HopThoaiCa
          ca={null}
          phongBan={phongChonDuoc}
          phongMacDinh={phongChonDuoc[0]?.id ?? ""}
          onDong={() => setDangMo(null)}
        />
      )}
      {dangMo?.loai === "suaCa" && (
        <HopThoaiCa
          ca={dangMo.ca}
          phongBan={phongBan}
          phongMacDinh={dangMo.ca.department_id}
          onDong={() => setDangMo(null)}
        />
      )}
      {dangMo?.loai === "ngungCa" && (
        <HopXacNhan
          tieuDe={t("ca.ngung")}
          moTa={t("ca.xacNhanNgung", { ten: dangMo.ca.name })}
          nhanXacNhan={t("ca.ngung")}
          nguyHiem
          dangChay={ngung.isPending}
          loi={ngung.isError ? thongDiepLoi(ngung.error) : null}
          onDong={() => setDangMo(null)}
          onXacNhan={() => ngung.mutate(dangMo.ca.id)}
        />
      )}
      {dangMo?.loai === "phanCa" && (
        <HopThoaiPhanCa
          ngay={dangMo.ngay}
          userIdGoiY={dangMo.userId}
          danhSachCa={caDangDung}
          nhanVien={moiNguoi}
          onDong={() => setDangMo(null)}
        />
      )}
      {dangMo?.loai === "huyBuoi" && (
        <HopXacNhan
          tieuDe={t("lich.huyPhanCa")}
          moTa={t("lich.xacNhanHuy", {
            ca: caTheoId.get(dangMo.buoi.shift_id)?.name ?? "",
            ngay: ngayVN(dangMo.buoi.work_date),
            ten:
              moiNguoi.find((u) => u.id === dangMo.buoi.user_id)?.full_name ??
              t("nhatKy.khongRo"),
          })}
          nhanXacNhan={t("lich.huyPhanCa")}
          nguyHiem
          dangChay={huy.isPending}
          loi={huy.isError ? thongDiepLoi(huy.error) : null}
          onDong={() => setDangMo(null)}
          onXacNhan={() => huy.mutate(dangMo.buoi.id)}
        />
      )}
    </div>
  );
}
