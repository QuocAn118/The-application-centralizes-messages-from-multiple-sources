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
import { Truong } from "@/components/ui/truong";
import { ONhap } from "@/components/ui/o-nhap";
import type { UserResponse } from "@/lib/types";

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
      <div className="mt-4 flex flex-col gap-4">
        <Truong nhan={t("nguoiDung.hoTen")} batBuoc>
          {(o) => <ONhap {...o} value={hoTen} onChange={(e) => setHoTen(e.target.value)} />}
        </Truong>
        <Truong nhan={`${t("nguoiDung.dienThoai")} ${t("nguoiDung.khongBatBuoc")}`}>
          {(o) => <ONhap {...o} type="tel" value={dienThoai} onChange={(e) => setDienThoai(e.target.value)} />}
        </Truong>
      </div>
    </HopThoai>
  );
}
