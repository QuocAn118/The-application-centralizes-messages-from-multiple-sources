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
import { t } from "@/lib/i18n";
import { datLaiMatKhau, khoaQuanTri } from "@/lib/quan-tri-api";
import { thongDiepLoi } from "@/lib/loi-quan-tri";
import { HopThoai, NutChinh, NutPhu } from "@/components/hop-thoai";
import type { UserResponse } from "@/lib/types";

const LOP_O_NHAP =
  "mt-1 w-full rounded-lg border border-border-subtle bg-white px-3 py-2 text-sm text-foreground outline-none transition focus:border-primary";

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
  const [daSaoChep, setDaSaoChep] = useState(false);

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
        <p className="mt-4 rounded-lg border border-cho-phan-fg/30 bg-cho-phan-bg px-3.5 py-2.5 text-xs text-cho-phan-fg">
          {t("nguoiDung.canhBaoMotLan")}
        </p>
        <div className="mt-4 flex items-center gap-2">
          <code className="min-w-0 flex-1 truncate rounded-lg border border-border-subtle bg-surface px-3 py-2 font-mono text-sm text-foreground">
            {xong}
          </code>
          <button
            type="button"
            onClick={() => {
              void navigator.clipboard
                .writeText(xong)
                .then(() => setDaSaoChep(true))
                .catch(() => setDaSaoChep(false));
            }}
            className="shrink-0 rounded-lg border border-border-subtle px-3 py-2 text-xs font-medium text-foreground transition hover:bg-surface"
          >
            {daSaoChep ? t("nguoiDung.daSaoChep") : t("nguoiDung.saoChep")}
          </button>
        </div>
        <p className="mt-2 text-xs text-muted">{t("nguoiDung.canhBaoDatLai")}</p>
      </HopThoai>
    );
  }

  return (
    <HopThoai
      tieuDe={t("nguoiDung.datLaiMatKhau")}
      moTa={nguoi.full_name}
      loi={dat.isError ? thongDiepLoi(dat.error) : null}
      onDong={onDong}
      chanDuoi={
        <>
          <NutPhu onClick={onDong} disabled={dat.isPending}>
            {t("chung.huy")}
          </NutPhu>
          <NutChinh
            onClick={() => dat.mutate()}
            disabled={dat.isPending || matKhau.length < 8}
          >
            {dat.isPending ? t("nguoiDung.dangLuu") : t("nguoiDung.luu")}
          </NutChinh>
        </>
      }
    >
      <label className="mt-4 block">
        <span className="text-xs font-medium text-muted">
          {t("nguoiDung.matKhauMoi")}
        </span>
        <div className="relative">
          <input
            type={hien ? "text" : "password"}
            autoComplete="new-password"
            value={matKhau}
            onChange={(e) => setMatKhau(e.target.value)}
            className={LOP_O_NHAP}
          />
          <button
            type="button"
            onClick={() => setHien((truoc) => !truoc)}
            className="absolute right-2 top-1/2 -translate-y-1/2 rounded px-2 py-1 text-xs text-muted transition hover:text-foreground"
          >
            {hien ? t("nguoiDung.an") : t("nguoiDung.hien")}
          </button>
        </div>
        <span className="mt-1 block text-xs text-muted-soft">
          {t("nguoiDung.toiThieu8")}
        </span>
      </label>
      <p className="mt-3 text-xs text-muted">{t("nguoiDung.canhBaoDatLai")}</p>
    </HopThoai>
  );
}
