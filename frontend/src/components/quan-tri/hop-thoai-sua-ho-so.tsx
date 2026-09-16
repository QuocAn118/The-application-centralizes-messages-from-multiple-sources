"use client";

/**
 * Sửa hồ sơ — chỉ tên và điện thoại (#F2 task 1.6).
 *
 * `PATCH /users/{id}` chỉ nhận hai trường này; vai trò và phòng ban có endpoint
 * riêng vì chúng kéo theo quy tắc nghiệp vụ khác hẳn.
 */

import { useState } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { t } from "@/lib/i18n";
import { khoaQuanTri, suaHoSo } from "@/lib/quan-tri-api";
import { thongDiepLoi } from "@/lib/loi-quan-tri";
import { HopThoai, NutChinh, NutPhu } from "@/components/hop-thoai";
import type { UserResponse } from "@/lib/types";

const LOP_O_NHAP =
  "mt-1 w-full rounded-lg border border-border-subtle bg-white px-3 py-2 text-sm text-foreground outline-none transition focus:border-primary";

export function HopThoaiSuaHoSo({
  nguoi,
  onDong,
}: {
  nguoi: UserResponse;
  onDong: () => void;
}) {
  const queryClient = useQueryClient();
  const [hoTen, setHoTen] = useState(nguoi.full_name);
  const [dienThoai, setDienThoai] = useState(nguoi.phone ?? "");

  const luu = useMutation({
    mutationFn: () =>
      suaHoSo(nguoi.id, {
        full_name: hoTen.trim(),
        // Xoá trắng ô = gỡ số điện thoại. Backend phân biệt `null` (gỡ) với
        // trường vắng mặt (giữ nguyên), nên gửi `null` chứ không phải "".
        phone: dienThoai.trim() || null,
      }),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: khoaQuanTri.nguoiDung.all });
      onDong();
    },
  });

  return (
    <HopThoai
      tieuDe={t("nguoiDung.suaHoSo")}
      moTa={nguoi.email}
      loi={luu.isError ? thongDiepLoi(luu.error) : null}
      onDong={onDong}
      chanDuoi={
        <>
          <NutPhu onClick={onDong} disabled={luu.isPending}>
            {t("chung.huy")}
          </NutPhu>
          <NutChinh
            onClick={() => luu.mutate()}
            disabled={luu.isPending || hoTen.trim().length === 0}
          >
            {luu.isPending ? t("nguoiDung.dangLuu") : t("nguoiDung.luu")}
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
      </div>
    </HopThoai>
  );
}
