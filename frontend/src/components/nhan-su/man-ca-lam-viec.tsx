"use client";

/**
 * Màn Ca làm việc (#F3 GĐ2, redesign Phần 3).
 *
 * **Lịch tuần lên đầu, chiếm cả màn** (S1) — đó là thứ mở ra xem hằng ngày. Mẫu
 * ca (khuôn giờ, sửa thỉnh thoảng) là chế độ xem thứ hai; chú giải màu dưới lịch
 * vẫn cho thấy các khuôn giờ đang dùng mà không cần chuyển.
 *
 * Staff chỉ xem: backend trả đúng ca của họ (`ListShiftAssignments` lọc theo
 * `user_ids`), và FE ẩn mọi nút xếp/huỷ.
 */

import { useMemo, useState } from "react";
import { CalendarDays, ChevronLeft, ChevronRight, Clock, Pencil, Plus, Power } from "lucide-react";
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
import { ChuGiaiCa, LuoiLich } from "./luoi-lich";
import { lopMau, mauTuId } from "@/components/ui/ban-mau";
import { DauTrang } from "@/components/ui/dau-trang";
import { The } from "@/components/ui/the";
import { Bang, Td, Th, Tr } from "@/components/ui/bang";
import { HuyHieu } from "@/components/ui/huy-hieu";
import { MenuHanhDong } from "@/components/ui/menu-hanh-dong";
import { Nut } from "@/components/ui/nut";
import { TrangThaiLoi, TrangThaiRong, TrangThaiTai } from "@/components/ui/trang-thai";
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
  const [cheDo, setCheDo] = useState<"lich" | "mau">("lich");

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

  const tenPhong = (id: string) =>
    phongBan.find((p) => p.id === id)?.name ?? t("nguoiDung.khongPhong");

  return (
    <div className="flex flex-col gap-5 px-8 py-6">
      <DauTrang
        tieuDe="Ca làm việc"
        moTa={
          cheDo === "mau"
            ? "Khuôn giờ dùng để xếp lịch. Mẫu đã ngừng không xếp thêm được."
            : xepDuoc
              ? "Bấm vào một ô trống để xếp ca. Ngày đã qua không xếp thêm được."
              : "Lịch ca của bạn theo tuần."
        }
        hanhDong={
          <>
            <div role="group" aria-label="Chế độ xem" className="flex">
              <Nut
                bienThe={cheDo === "lich" ? "chinh" : "phu"}
                icon={CalendarDays}
                aria-pressed={cheDo === "lich"}
                onClick={() => setCheDo("lich")}
                className="rounded-r-none"
              >
                Lịch tuần
              </Nut>
              <Nut
                bienThe={cheDo === "mau" ? "chinh" : "phu"}
                icon={Clock}
                aria-pressed={cheDo === "mau"}
                onClick={() => setCheDo("mau")}
                className="rounded-l-none"
              >
                {t("ca.tieuDe")}
              </Nut>
            </div>
            {xepDuoc && (
              <Nut icon={Plus} onClick={() => setDangMo({ loai: "taoCa" })}>
                {t("ca.taoMoi")}
              </Nut>
            )}
          </>
        }
      />

      {cheDo === "lich" ? (
        <The>
          <div className="flex flex-wrap items-center justify-between gap-3 border-b-2 border-ink px-5 py-3">
            <div className="flex items-center gap-2">
              <Nut co="sm" icon={ChevronLeft} onClick={() => doiTuan(-7)}>
                {t("lich.tuanTruoc")}
              </Nut>
              <Nut co="sm" onClick={() => setMocTuan(new Date())}>
                {t("lich.tuanNay")}
              </Nut>
              <Nut co="sm" onClick={() => doiTuan(7)}>
                {t("lich.tuanSau")}
                <ChevronRight aria-hidden className="size-4" strokeWidth={2.25} />
              </Nut>
              <span className="ml-2 text-sm font-bold text-ink">
                {ngayVN(tuNgay)} – {ngayVN(denNgay)}
              </span>
            </div>
            {/* Chú giải chỉ các ca có mặt trên lưới tuần này — giải thích màu đang thấy. */}
            <ChuGiaiCa
              ca={danhSachCa.filter((c) =>
                truyVanLich.data?.some((b) => b.status === "ACTIVE" && b.shift_id === c.id),
              )}
            />
          </div>

          {truyVanLich.isPending && <TrangThaiTai />}
          {truyVanLich.isError && (
            <TrangThaiLoi
              thongDiep={thongDiepLoi(truyVanLich.error)}
              onThuLai={() => void truyVanLich.refetch()}
            />
          )}
          {truyVanLich.data && nhanVienLuoi.length === 0 && (
            <TrangThaiRong
              icon={CalendarDays}
              tieuDe={danhSachCa.length === 0 ? t("ca.chuaCoCa") : t("lich.khongCoNhanVien")}
            />
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
        </The>
      ) : (
        <div className="max-w-[1440px]">
          {truyVanCa.isPending && (
            <The>
              <TrangThaiTai dong={3} />
            </The>
          )}
          {truyVanCa.isError && (
            <The>
              <TrangThaiLoi
                thongDiep={thongDiepLoi(truyVanCa.error)}
                onThuLai={() => void truyVanCa.refetch()}
              />
            </The>
          )}
          {truyVanCa.data && danhSachCa.length === 0 && (
            <The>
              <TrangThaiRong icon={Clock} tieuDe={t("ca.chuaCoCa")} />
            </The>
          )}
          {danhSachCa.length > 0 && (
            <Bang aria-label={t("ca.tieuDe")}>
              <thead>
                <tr>
                  <Th>{t("ca.ten")}</Th>
                  <Th>Khung giờ</Th>
                  <Th>{t("ca.phongBan")}</Th>
                  <Th>Trạng thái</Th>
                  <Th className="w-16">
                    <span className="sr-only">{t("nguoiDung.thaoTac")}</span>
                  </Th>
                </tr>
              </thead>
              <tbody>
                {danhSachCa.map((ca) => (
                  <Tr key={ca.id}>
                    <Td>
                      <span className="flex items-center gap-2 font-bold">
                        <span
                          aria-hidden
                          className={`size-3.5 shrink-0 rounded-[3px] border-2 border-ink ${lopMau(mauTuId(ca.id))}`}
                        />
                        {ca.name}
                      </span>
                    </Td>
                    <Td className="tabular-nums">
                      {gioNgan(ca.start_time)}–{gioNgan(ca.end_time)}
                    </Td>
                    <Td>{tenPhong(ca.department_id)}</Td>
                    <Td>
                      <HuyHieu tong={ca.is_active ? "ok" : "trung"}>
                        {ca.is_active ? t("ca.dangDung") : t("ca.daNgung")}
                      </HuyHieu>
                    </Td>
                    <Td className="text-right">
                      {xepDuoc && (
                        <MenuHanhDong
                          nhan={`Thao tác với ${ca.name}`}
                          muc={[
                            {
                              nhan: t("ca.sua"),
                              icon: Pencil,
                              onChon: () => setDangMo({ loai: "suaCa", ca }),
                            },
                            // Ca đã ngừng không bật lại được: backend không có endpoint.
                            {
                              nhan: t("ca.ngung"),
                              icon: Power,
                              nguyHiem: true,
                              an: !ca.is_active,
                              onChon: () => setDangMo({ loai: "ngungCa", ca }),
                            },
                          ]}
                        />
                      )}
                    </Td>
                  </Tr>
                ))}
              </tbody>
            </Bang>
          )}
        </div>
      )}

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
