"use client";

/**
 * Tạo tài khoản — hai bước (#F2 task 1.5, mockup Stitch "Tạo tài khoản").
 *
 * Bước 2 hiện mật khẩu tạm **một lần duy nhất** (RB-3). Vì vậy ở đây cố ý
 * KHÔNG: ghi vào `localStorage`, đưa vào URL, hay `console.log`. Mật khẩu chỉ
 * sống trong state của component này và mất khi đóng hộp thoại.
 *
 * Hộp bước 2 không đóng được bằng Esc, bấm nền hay nút "×": đóng nhầm là mất
 * mật khẩu, phải đặt lại. Chỉ nút "Đã sao chép, đóng lại" mới đóng được.
 */

import { useState } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { t } from "@/lib/i18n";
import { NHAN_VAI } from "@/lib/hien-thi";
import { khoaQuanTri, taoNguoiDung } from "@/lib/quan-tri-api";
import { thongDiepLoi } from "@/lib/loi-quan-tri";
import { HopThoai, NutChinh, NutPhu } from "@/components/hop-thoai";
import type { Department, Role, UserResponse } from "@/lib/types";

const LOP_O_NHAP =
  "mt-1 w-full rounded-lg border border-border-subtle bg-white px-3 py-2 text-sm text-foreground outline-none transition placeholder:text-muted-soft focus:border-primary";

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
  const [daTao, setDaTao] = useState<{ nguoi: UserResponse; matKhau: string } | null>(
    null,
  );
  const [daSaoChep, setDaSaoChep] = useState(false);

  // Admin không được gắn phòng (`ADMIN_CANNOT_HAVE_DEPARTMENT`); Staff/Manager
  // thì bắt buộc có (`DEPARTMENT_REQUIRED`).
  const canPhong = vai !== "ADMIN";
  const phongHoatDong = phongBan.filter((p) => p.is_active);

  const hopLe =
    hoTen.trim().length > 0 &&
    email.trim().length > 0 &&
    matKhau.length >= 8 &&
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
        <p className="mt-4 rounded-lg border border-cho-phan-fg/30 bg-cho-phan-bg px-3.5 py-2.5 text-xs text-cho-phan-fg">
          {t("nguoiDung.canhBaoMotLan")}
        </p>

        <div className="mt-4">
          <p className="text-xs font-medium text-muted">{t("nguoiDung.matKhauTam")}</p>
          <div className="mt-1 flex items-center gap-2">
            <code className="min-w-0 flex-1 truncate rounded-lg border border-border-subtle bg-surface px-3 py-2 font-mono text-sm text-foreground">
              {daTao.matKhau}
            </code>
            <button
              type="button"
              onClick={() => {
                void navigator.clipboard
                  .writeText(daTao.matKhau)
                  .then(() => setDaSaoChep(true))
                  // Trình duyệt có thể chặn clipboard (không phải HTTPS,
                  // không có tương tác…). Nuốt lỗi: mật khẩu vẫn đang hiện
                  // trên màn, người dùng chép tay được.
                  .catch(() => setDaSaoChep(false));
              }}
              className="shrink-0 rounded-lg border border-border-subtle px-3 py-2 text-xs font-medium text-foreground transition hover:bg-surface"
            >
              {daSaoChep ? t("nguoiDung.daSaoChep") : t("nguoiDung.saoChep")}
            </button>
          </div>
          <p className="mt-2 text-xs text-muted">{t("nguoiDung.phaiDoiLanDau")}</p>
        </div>
      </HopThoai>
    );
  }

  return (
    <HopThoai
      tieuDe={t("nguoiDung.taoMoi")}
      moTa={t("nguoiDung.phaiDoiLanDau")}
      loi={tao.isError ? thongDiepLoi(tao.error) : null}
      onDong={onDong}
      chanDuoi={
        <>
          <NutPhu onClick={onDong} disabled={tao.isPending}>
            {t("chung.huy")}
          </NutPhu>
          <NutChinh
            onClick={() => tao.mutate()}
            disabled={!hopLe || tao.isPending}
          >
            {tao.isPending ? t("nguoiDung.dangLuu") : t("nguoiDung.taoMoi")}
          </NutChinh>
        </>
      }
    >
      <div className="mt-4 space-y-3">
        <label className="block">
          <span className="text-xs font-medium text-muted">{t("nguoiDung.hoTen")}</span>
          <input
            value={hoTen}
            onChange={(e) => setHoTen(e.target.value)}
            className={LOP_O_NHAP}
          />
        </label>

        <label className="block">
          <span className="text-xs font-medium text-muted">{t("nguoiDung.email")}</span>
          <input
            type="email"
            autoComplete="off"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            className={LOP_O_NHAP}
          />
        </label>

        <label className="block">
          <span className="text-xs font-medium text-muted">
            {t("nguoiDung.dienThoai")}{" "}
            <span className="font-normal text-muted-soft">
              {t("nguoiDung.khongBatBuoc")}
            </span>
          </span>
          <input
            value={dienThoai}
            onChange={(e) => setDienThoai(e.target.value)}
            className={LOP_O_NHAP}
          />
        </label>

        <div className="flex gap-3">
          <label className="block flex-1">
            <span className="text-xs font-medium text-muted">
              {t("nguoiDung.locVaiTro")}
            </span>
            <select
              value={vai}
              onChange={(e) => {
                const vaiMoi = e.target.value as Role;
                setVai(vaiMoi);
                // Đổi sang Admin thì bỏ phòng đã chọn, không gửi kèm rồi để
                // server trả `ADMIN_CANNOT_HAVE_DEPARTMENT`.
                if (vaiMoi === "ADMIN") setPhongId("");
              }}
              className={LOP_O_NHAP}
            >
              {(["STAFF", "MANAGER", "ADMIN"] as const).map((r) => (
                <option key={r} value={r}>
                  {NHAN_VAI[r]}
                </option>
              ))}
            </select>
          </label>

          {canPhong && (
            <label className="block flex-1">
              <span className="text-xs font-medium text-muted">
                {t("nguoiDung.locPhongBan")}
              </span>
              <select
                value={phongId}
                onChange={(e) => setPhongId(e.target.value)}
                className={LOP_O_NHAP}
              >
                <option value="">—</option>
                {phongHoatDong.map((p) => (
                  <option key={p.id} value={p.id}>
                    {p.name}
                  </option>
                ))}
              </select>
            </label>
          )}
        </div>

        <label className="block">
          <span className="text-xs font-medium text-muted">
            {t("nguoiDung.matKhauTam")}
          </span>
          <div className="relative">
            <input
              type={hienMatKhau ? "text" : "password"}
              autoComplete="new-password"
              value={matKhau}
              onChange={(e) => setMatKhau(e.target.value)}
              className={LOP_O_NHAP}
            />
            <button
              type="button"
              onClick={() => setHienMatKhau((truoc) => !truoc)}
              className="absolute right-2 top-1/2 -translate-y-1/2 rounded px-2 py-1 text-xs text-muted transition hover:text-foreground"
            >
              {hienMatKhau ? t("nguoiDung.an") : t("nguoiDung.hien")}
            </button>
          </div>
          <span className="mt-1 block text-xs text-muted-soft">
            {t("nguoiDung.toiThieu8")}
          </span>
        </label>
      </div>
    </HopThoai>
  );
}
