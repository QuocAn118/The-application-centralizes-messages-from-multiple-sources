"use client";

/**
 * Tạo tài khoản — hai bước (#F2 task 1.5; redesign Phần 6 §4.6).
 *
 * Bước 2 hiện mật khẩu tạm **một lần duy nhất** (RB-3). Vì vậy ở đây cố ý
 * KHÔNG: ghi vào `localStorage`, đưa vào URL, hay `console.log`. Mật khẩu chỉ
 * sống trong state của component này và mất khi đóng hộp thoại.
 *
 * Hộp bước 2 không đóng được bằng Esc, bấm nền hay nút "×": đóng nhầm là mất
 * mật khẩu, phải đặt lại. Chỉ nút "Đã sao chép, đóng lại" mới đóng được.
 *
 * Lỗi server gắn về ĐÚNG ô (`loiTheoTruong`): email trùng hiện dưới ô email, mật
 * khẩu yếu dưới ô mật khẩu… Lỗi không thuộc ô nào (vd. phòng đã có quản lý) vẫn
 * ở dòng lỗi chung của hộp.
 */

import { useState } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { Eye, EyeOff } from "lucide-react";
import { t } from "@/lib/i18n";
import { NHAN_VAI } from "@/lib/hien-thi";
import { khoaQuanTri, taoNguoiDung } from "@/lib/quan-tri-api";
import { loiTheoTruong } from "@/lib/loi-truong";
import { DO_DAI_MAT_KHAU_TOI_THIEU } from "@/lib/xac-thuc";
import { HopThoai, NutChinh, NutPhu } from "@/components/hop-thoai";
import { Truong } from "@/components/ui/truong";
import { OChon, ONhap } from "@/components/ui/o-nhap";
import { Nut } from "@/components/ui/nut";
import { MatKhauMotLan } from "./mat-khau-mot-lan";
import type { Department, Role, UserResponse } from "@/lib/types";

type O = "hoTen" | "email" | "dienThoai" | "phong" | "matKhau";

const THEO_MA: Partial<Record<string, O>> = {
  EMAIL_ALREADY_EXISTS: "email",
  INVALID_EMAIL: "email",
  EMAIL_TOO_LONG: "email",
  EMPTY_FULL_NAME: "hoTen",
  WEAK_PASSWORD: "matKhau",
  DEPARTMENT_REQUIRED: "phong",
  INACTIVE_DEPARTMENT: "phong",
  DEPARTMENT_ALREADY_HAS_MANAGER: "phong",
  ADMIN_CANNOT_HAVE_DEPARTMENT: "phong",
};
const THEO_TEN: Partial<Record<string, O>> = {
  full_name: "hoTen",
  email: "email",
  phone: "dienThoai",
  department_id: "phong",
  password: "matKhau",
};

export function HopThoaiTaoNguoiDung({
  phongBan,
  onDong,
}: {
  phongBan: Department[];
  onDong: () => void;
}) {
  const queryClient = useQueryClient();

  const [hoTen, setHoTen] = useState("");
  const [email, setEmail] = useState("");
  const [dienThoai, setDienThoai] = useState("");
  const [vai, setVai] = useState<Role>("STAFF");
  const [phongId, setPhongId] = useState("");
  const [matKhau, setMatKhau] = useState("");
  const [hienMatKhau, setHienMatKhau] = useState(false);

  // Bước 2: giữ cả người vừa tạo lẫn mật khẩu đã gửi đi — response không trả
  // mật khẩu về (đúng) nên phải nhớ lại chính chuỗi mình vừa gửi.
  const [daTao, setDaTao] = useState<{ nguoi: UserResponse; matKhau: string } | null>(null);

  // Admin không được gắn phòng (`ADMIN_CANNOT_HAVE_DEPARTMENT`); Staff/Manager
  // thì bắt buộc có (`DEPARTMENT_REQUIRED`).
  const canPhong = vai !== "ADMIN";
  const phongHoatDong = phongBan.filter((p) => p.is_active);

  const hopLe =
    hoTen.trim().length > 0 &&
    email.trim().length > 0 &&
    matKhau.length >= DO_DAI_MAT_KHAU_TOI_THIEU &&
    (!canPhong || phongId !== "");

  const tao = useMutation({
    mutationFn: () =>
      taoNguoiDung({
        email: email.trim(),
        full_name: hoTen.trim(),
        phone: dienThoai.trim() || null,
        role: vai,
        department_id: canPhong ? phongId : null,
        password: matKhau,
      }),
    onSuccess: (nguoi) => {
      setDaTao({ nguoi, matKhau });
      void queryClient.invalidateQueries({ queryKey: khoaQuanTri.nguoiDung.all });
    },
  });

  if (daTao) {
    return (
      <HopThoai
        tieuDe={t("nguoiDung.daTao")}
        moTa={daTao.nguoi.full_name}
        // `null` = không đóng được bằng Esc, bấm nền hay nút "×"; chỉ nút ở
        // chân hộp mới đóng. Lỡ tay là mất mật khẩu chỉ hiện một lần.
        onDong={null}
        chanDuoi={<NutChinh onClick={onDong}>{t("nguoiDung.dongLai")}</NutChinh>}
      >
        <MatKhauMotLan matKhau={daTao.matKhau} ghiChu={t("nguoiDung.phaiDoiLanDau")} />
      </HopThoai>
    );
  }

  const loi = tao.isError ? loiTheoTruong(tao.error, THEO_MA, THEO_TEN) : null;
  const loiO = (o: O) => (loi?.truong === o ? loi.thongDiep : null);

  return (
    <HopThoai
      tieuDe={t("nguoiDung.taoMoi")}
      moTa={t("nguoiDung.phaiDoiLanDau")}
      loi={loi && !loi.truong ? loi.thongDiep : null}
      onDong={onDong}
      chanDuoi={
        <>
          <NutPhu onClick={onDong} disabled={tao.isPending}>
            {t("chung.huy")}
          </NutPhu>
          <NutChinh onClick={() => tao.mutate()} disabled={!hopLe || tao.isPending}>
            {tao.isPending ? t("nguoiDung.dangLuu") : t("nguoiDung.taoMoi")}
          </NutChinh>
        </>
      }
    >
      <div className="mt-4 flex flex-col gap-4">
        <Truong nhan={t("nguoiDung.hoTen")} batBuoc loi={loiO("hoTen")}>
          {(o) => <ONhap {...o} value={hoTen} onChange={(e) => setHoTen(e.target.value)} />}
        </Truong>

        <Truong nhan={t("nguoiDung.email")} batBuoc loi={loiO("email")}>
          {(o) => (
            <ONhap {...o} type="email" autoComplete="off" value={email} onChange={(e) => setEmail(e.target.value)} />
          )}
        </Truong>

        <Truong nhan={`${t("nguoiDung.dienThoai")} ${t("nguoiDung.khongBatBuoc")}`} loi={loiO("dienThoai")}>
          {(o) => <ONhap {...o} type="tel" value={dienThoai} onChange={(e) => setDienThoai(e.target.value)} />}
        </Truong>

        <div className="grid grid-cols-2 gap-3">
          <Truong nhan={t("nguoiDung.locVaiTro")}>
            {(o) => (
              <OChon
                {...o}
                value={vai}
                onChange={(e) => {
                  const vaiMoi = e.target.value as Role;
                  setVai(vaiMoi);
                  // Đổi sang Admin thì bỏ phòng đã chọn, không gửi kèm rồi để
                  // server trả `ADMIN_CANNOT_HAVE_DEPARTMENT`.
                  if (vaiMoi === "ADMIN") setPhongId("");
                }}
              >
                {(["STAFF", "MANAGER", "ADMIN"] as const).map((r) => (
                  <option key={r} value={r}>
                    {NHAN_VAI[r]}
                  </option>
                ))}
              </OChon>
            )}
          </Truong>

          {canPhong && (
            <Truong nhan={t("nguoiDung.locPhongBan")} batBuoc loi={loiO("phong")}>
              {(o) => (
                <OChon {...o} value={phongId} onChange={(e) => setPhongId(e.target.value)}>
                  <option value="">—</option>
                  {phongHoatDong.map((p) => (
                    <option key={p.id} value={p.id}>
                      {p.name}
                    </option>
                  ))}
                </OChon>
              )}
            </Truong>
          )}
        </div>

        <Truong nhan={t("nguoiDung.matKhauTam")} batBuoc goiY={t("nguoiDung.toiThieu8")} loi={loiO("matKhau")}>
          {(o) => (
            <div className="flex gap-2">
              <ONhap
                {...o}
                type={hienMatKhau ? "text" : "password"}
                autoComplete="new-password"
                value={matKhau}
                onChange={(e) => setMatKhau(e.target.value)}
              />
              <Nut icon={hienMatKhau ? EyeOff : Eye} aria-pressed={hienMatKhau} onClick={() => setHienMatKhau((v) => !v)}>
                {hienMatKhau ? t("nguoiDung.an") : t("nguoiDung.hien")}
              </Nut>
            </div>
          )}
        </Truong>
      </div>
    </HopThoai>
  );
}
