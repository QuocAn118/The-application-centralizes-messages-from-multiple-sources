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
import { thongDiepLoi } from "@/lib/loi-quan-tri";
import { HopThoai, NutChinh, NutPhu } from "@/components/hop-thoai";
import type { Department } from "@/lib/types";

const LOP_O_NHAP =
  "mt-1 w-full rounded-lg border border-border-subtle bg-white px-3 py-2 text-sm text-foreground outline-none transition focus:border-primary";

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

  return (
    <HopThoai
      tieuDe={phong ? t("phongBan.sua") : t("phongBan.taoMoi")}
      moTa={phong ? phong.name : undefined}
      loi={luu.isError ? thongDiepLoi(luu.error) : null}
      onDong={onDong}
      chanDuoi={
        <>
          <NutPhu onClick={onDong} disabled={luu.isPending}>
            {t("chung.huy")}
          </NutPhu>
          <NutChinh
            onClick={() => luu.mutate()}
            disabled={luu.isPending || ten.trim().length === 0}
          >
            {luu.isPending ? t("nguoiDung.dangLuu") : t("nguoiDung.luu")}
          </NutChinh>
        </>
      }
    >
      <div className="mt-4 space-y-3">
        <label className="block">
          <span className="text-xs font-medium text-muted">{t("phongBan.ten")}</span>
          <input
            value={ten}
            onChange={(e) => setTen(e.target.value)}
            maxLength={200}
            className={LOP_O_NHAP}
          />
        </label>

        <label className="block">
          <span className="text-xs font-medium text-muted">
            {t("phongBan.moTa")}{" "}
            <span className="font-normal text-muted-soft">
              {t("nguoiDung.khongBatBuoc")}
            </span>
          </span>
          <textarea
            value={moTa}
            onChange={(e) => setMoTa(e.target.value)}
            rows={3}
            className={`${LOP_O_NHAP} resize-none`}
          />
        </label>
      </div>
    </HopThoai>
  );
}
