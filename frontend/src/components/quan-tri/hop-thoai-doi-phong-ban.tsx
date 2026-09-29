"use client";

/**
 * Đổi phòng ban (#F2 task 1.6).
 *
 * Với Admin thì phòng phải để trống (`ADMIN_CANNOT_HAVE_DEPARTMENT`); với
 * Staff/Manager thì bắt buộc có (`DEPARTMENT_REQUIRED`). Lựa chọn "không phòng"
 * chỉ mở cho Admin để không mời người dùng vào một lỗi đã biết trước.
 */

import { useState } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { t } from "@/lib/i18n";
import { doiPhongBan, khoaQuanTri } from "@/lib/quan-tri-api";
import { thongDiepLoi } from "@/lib/loi-quan-tri";
import { HopThoai, NutChinh, NutPhu } from "@/components/hop-thoai";
import { Truong } from "@/components/ui/truong";
import { OChon } from "@/components/ui/o-nhap";
import type { Department, UserResponse } from "@/lib/types";

export function HopThoaiDoiPhongBan({
  nguoi,
  phongBan,
  onDong,
}: {
  nguoi: UserResponse;
  phongBan: Department[];
  onDong: () => void;
}) {
  const queryClient = useQueryClient();
  const [phongId, setPhongId] = useState(nguoi.department_id ?? "");

  const laAdmin = nguoi.role === "ADMIN";
  const phongHoatDong = phongBan.filter((p) => p.is_active);

  const luu = useMutation({
    mutationFn: () => doiPhongBan(nguoi.id, phongId || null),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: khoaQuanTri.nguoiDung.all });
      onDong();
    },
  });

  return (
    <HopThoai
      tieuDe={t("nguoiDung.doiPhongBan")}
      moTa={nguoi.full_name}
      loi={luu.isError ? thongDiepLoi(luu.error) : null}
      onDong={onDong}
      chanDuoi={
        <>
          <NutPhu onClick={onDong} disabled={luu.isPending}>
            {t("chung.huy")}
          </NutPhu>
          <NutChinh
            onClick={() => luu.mutate()}
            disabled={luu.isPending || (!laAdmin && phongId === "")}
          >
            {luu.isPending ? t("nguoiDung.dangLuu") : t("nguoiDung.luu")}
          </NutChinh>
        </>
      }
    >
      <div className="mt-4">
        <Truong nhan={t("nguoiDung.phongMoi")}>
          {(o) => (
            <OChon {...o} value={phongId} onChange={(e) => setPhongId(e.target.value)}>
              {/* Admin được phép không thuộc phòng nào; Staff/Manager thì mục rỗng
                  chỉ là chỗ giữ khi chưa chọn, và nút Lưu vẫn khoá. */}
              {(laAdmin || phongId === "") && <option value="">{t("nguoiDung.khongPhong")}</option>}
              {phongHoatDong.map((p) => (
                <option key={p.id} value={p.id}>
                  {p.name}
                </option>
              ))}
            </OChon>
          )}
        </Truong>
      </div>
    </HopThoai>
  );
}
