"use client";

/**
 * Tạo / sửa phòng ban (#F2 task 2.2).
 *
 * Một component cho cả hai việc: hai form giống hệt nhau (tên + mô tả), tách
 * đôi chỉ nhân bản chỗ dễ lệch. `phong = null` nghĩa là tạo mới.
 */

import { useState } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { t } from "@/lib/i18n";
import { khoaQuanTri, suaPhongBan, taoPhongBan } from "@/lib/quan-tri-api";
import { loiTheoTruong } from "@/lib/loi-truong";
import { HopThoai, NutChinh, NutPhu } from "@/components/hop-thoai";
import { Truong } from "@/components/ui/truong";
import { ONhap, VungNhap } from "@/components/ui/o-nhap";
import type { Department } from "@/lib/types";

export function HopThoaiPhongBan({
  phong,
  onDong,
}: {
  /** `null` = tạo mới. */
  phong: Department | null;
  onDong: () => void;
}) {
  const queryClient = useQueryClient();
  const [ten, setTen] = useState(phong?.name ?? "");
  const [moTa, setMoTa] = useState(phong?.description ?? "");

  const luu = useMutation({
    mutationFn: () => {
      const duLieu = {
        name: ten.trim(),
        // Xoá trắng ô = gỡ mô tả. Gửi `null` chứ không phải chuỗi rỗng, cho
        // khớp `description: str | None` của backend.
        description: moTa.trim() || null,
      };
      return phong ? suaPhongBan(phong.id, duLieu) : taoPhongBan(duLieu);
    },
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: khoaQuanTri.phongBan.all });
      onDong();
    },
  });

  const loi = luu.isError
    ? loiTheoTruong(luu.error, { DEPARTMENT_NAME_EXISTS: "ten", EMPTY_DEPARTMENT_NAME: "ten" }, { name: "ten" })
    : null;

  return (
    <HopThoai
      tieuDe={phong ? t("phongBan.sua") : t("phongBan.taoMoi")}
      moTa={phong ? phong.name : undefined}
      loi={loi && !loi.truong ? loi.thongDiep : null}
      onDong={onDong}
      chanDuoi={
        <>
          <NutPhu onClick={onDong} disabled={luu.isPending}>
            {t("chung.huy")}
          </NutPhu>
          <NutChinh onClick={() => luu.mutate()} disabled={luu.isPending || ten.trim().length === 0}>
            {luu.isPending ? t("nguoiDung.dangLuu") : t("nguoiDung.luu")}
          </NutChinh>
        </>
      }
    >
      <div className="mt-4 flex flex-col gap-4">
        <Truong nhan={t("phongBan.ten")} batBuoc loi={loi?.truong === "ten" ? loi.thongDiep : null}>
          {(o) => <ONhap {...o} value={ten} onChange={(e) => setTen(e.target.value)} maxLength={200} />}
        </Truong>
        <Truong nhan={`${t("phongBan.moTa")} ${t("nguoiDung.khongBatBuoc")}`}>
          {(o) => <VungNhap {...o} value={moTa} onChange={(e) => setMoTa(e.target.value)} rows={3} className="resize-none" />}
        </Truong>
      </div>
    </HopThoai>
  );
}
