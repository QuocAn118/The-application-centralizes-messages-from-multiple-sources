"use client";

/**
 * Đặt lại mật khẩu cho người khác (#F2 task 1.7).
 *
 * Cùng quy tắc RB-3 như lúc tạo tài khoản: mật khẩu hiện MỘT lần ở bước 2,
 * không lưu `localStorage`, không vào URL, không log. Bước 2 không đóng được
 * bằng Esc, bấm nền hay nút "×" — đóng nhầm là mất mật khẩu, phải đặt lại.
 */

import { useState } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { Eye, EyeOff } from "lucide-react";
import { t } from "@/lib/i18n";
import { datLaiMatKhau, khoaQuanTri } from "@/lib/quan-tri-api";
import { loiTheoTruong } from "@/lib/loi-truong";
import { DO_DAI_MAT_KHAU_TOI_THIEU } from "@/lib/xac-thuc";
import { HopThoai, NutChinh, NutPhu } from "@/components/hop-thoai";
import { Truong } from "@/components/ui/truong";
import { ONhap } from "@/components/ui/o-nhap";
import { Nut } from "@/components/ui/nut";
import { MatKhauMotLan } from "./mat-khau-mot-lan";
import type { UserResponse } from "@/lib/types";

export function HopThoaiDatLaiMatKhau({
  nguoi,
  onDong,
}: {
  nguoi: UserResponse;
  onDong: () => void;
}) {
  const queryClient = useQueryClient();
  const [matKhau, setMatKhau] = useState("");
  const [hien, setHien] = useState(false);
  const [xong, setXong] = useState<string | null>(null);

  const dat = useMutation({
    mutationFn: () => datLaiMatKhau(nguoi.id, matKhau),
    onSuccess: () => {
      setXong(matKhau);
      void queryClient.invalidateQueries({ queryKey: khoaQuanTri.nguoiDung.all });
    },
  });

  if (xong) {
    return (
      <HopThoai
        tieuDe={t("nguoiDung.daDatLai")}
        moTa={nguoi.full_name}
        onDong={null}
        chanDuoi={<NutChinh onClick={onDong}>{t("nguoiDung.dongLai")}</NutChinh>}
      >
        <MatKhauMotLan matKhau={xong} ghiChu={t("nguoiDung.canhBaoDatLai")} />
      </HopThoai>
    );
  }

  const loi = dat.isError ? loiTheoTruong(dat.error, { WEAK_PASSWORD: "matKhau" }, { password: "matKhau", new_password: "matKhau" }) : null;

  return (
    <HopThoai
      tieuDe={t("nguoiDung.datLaiMatKhau")}
      moTa={nguoi.full_name}
      loi={loi && !loi.truong ? loi.thongDiep : null}
      onDong={onDong}
      chanDuoi={
        <>
          <NutPhu onClick={onDong} disabled={dat.isPending}>
            {t("chung.huy")}
          </NutPhu>
          <NutChinh onClick={() => dat.mutate()} disabled={dat.isPending || matKhau.length < DO_DAI_MAT_KHAU_TOI_THIEU}>
            {dat.isPending ? t("nguoiDung.dangLuu") : t("nguoiDung.luu")}
          </NutChinh>
        </>
      }
    >
      <div className="mt-4 flex flex-col gap-3">
        <Truong
          nhan={t("nguoiDung.matKhauMoi")}
          goiY={t("nguoiDung.toiThieu8")}
          loi={loi?.truong === "matKhau" ? loi.thongDiep : null}
        >
          {(o) => (
            <div className="flex gap-2">
              <ONhap
                {...o}
                type={hien ? "text" : "password"}
                autoComplete="new-password"
                value={matKhau}
                onChange={(e) => setMatKhau(e.target.value)}
              />
              <Nut icon={hien ? EyeOff : Eye} aria-pressed={hien} onClick={() => setHien((v) => !v)}>
                {hien ? t("nguoiDung.an") : t("nguoiDung.hien")}
              </Nut>
            </div>
          )}
        </Truong>
        <p className="text-sm text-ink-2">{t("nguoiDung.canhBaoDatLai")}</p>
      </div>
    </HopThoai>
  );
}
