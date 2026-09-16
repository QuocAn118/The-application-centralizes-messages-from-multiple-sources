"use client";

/**
 * Đổi vai trò (#F2 task 1.6).
 *
 * Ô chọn **không có "Quản trị"**: backend trả `CANNOT_CHANGE_TO_ADMIN` — chỉ
 * đổi qua lại giữa Nhân viên và Quản lý (RB-4). Danh sách vai lấy từ
 * `VAI_DOI_DUOC` để quy tắc này nằm một chỗ.
 *
 * Gửi kèm `department_id` vì đổi sang Quản lý thì backend cần biết phòng nào,
 * và mỗi phòng chỉ được một Quản lý đang hoạt động
 * (`DEPARTMENT_ALREADY_HAS_MANAGER`).
 */

import { useState } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { t } from "@/lib/i18n";
import { NHAN_VAI } from "@/lib/hien-thi";
import { doiVaiTro, khoaQuanTri } from "@/lib/quan-tri-api";
import { VAI_DOI_DUOC } from "@/lib/quyen-quan-tri";
import { thongDiepLoi } from "@/lib/loi-quan-tri";
import { HopThoai, NutChinh, NutPhu } from "@/components/hop-thoai";
import type { Department, Role, UserResponse } from "@/lib/types";

const LOP_O_NHAP =
  "mt-1 w-full rounded-lg border border-border-subtle bg-white px-3 py-2 text-sm text-foreground outline-none transition focus:border-primary";

export function HopThoaiDoiVaiTro({
  nguoi,
  phongBan,
  onDong,
}: {
  nguoi: UserResponse;
  phongBan: Department[];
  onDong: () => void;
}) {
  const queryClient = useQueryClient();
  // Người đang là ADMIN không nằm trong `VAI_DOI_DUOC`; mặc định về STAFF để ô
  // chọn không rơi vào giá trị không có trong danh sách.
  const vaiDau: Role = nguoi.role === "ADMIN" ? "STAFF" : nguoi.role;
  const [vai, setVai] = useState<Role>(vaiDau);
  const [phongId, setPhongId] = useState(nguoi.department_id ?? "");

  const phongHoatDong = phongBan.filter((p) => p.is_active);

  const luu = useMutation({
    mutationFn: () => doiVaiTro(nguoi.id, { role: vai, department_id: phongId || null }),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: khoaQuanTri.nguoiDung.all });
      onDong();
    },
  });

  return (
    <HopThoai
      tieuDe={t("nguoiDung.doiVaiTro")}
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
            disabled={luu.isPending || phongId === ""}
          >
            {luu.isPending ? t("nguoiDung.dangLuu") : t("nguoiDung.luu")}
          </NutChinh>
        </>
      }
    >
      <div className="mt-4 space-y-3">
        <label className="block">
          <span className="text-xs font-medium text-muted">{t("nguoiDung.vaiMoi")}</span>
          <select
            value={vai}
            onChange={(e) => setVai(e.target.value as Role)}
            className={LOP_O_NHAP}
          >
            {VAI_DOI_DUOC.map((r) => (
              <option key={r} value={r}>
                {NHAN_VAI[r]}
              </option>
            ))}
          </select>
          <span className="mt-1 block text-xs text-muted-soft">
            {t("nguoiDung.khongDoiSangQuanTri")}
          </span>
        </label>

        <label className="block">
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
      </div>
    </HopThoai>
  );
}
