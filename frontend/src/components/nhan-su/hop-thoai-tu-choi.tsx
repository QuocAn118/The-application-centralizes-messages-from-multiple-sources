"use client";

/**
 * Từ chối đơn (#F3 task 1.5, RB-7).
 *
 * `RejectRequestRequest.reason` có `min_length=1` nên lý do là **bắt buộc** —
 * khác duyệt, vốn không cần gì. Vì vậy từ chối phải mở hộp nhập, không từ chối
 * thẳng từ nút trong bảng.
 */

import { useState } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { t } from "@/lib/i18n";
import { khoaNhanSu, tuChoiDon } from "@/lib/nhan-su-api";
import { thongDiepLoi } from "@/lib/loi-quan-tri";
import { HopThoai, NutChinh, NutPhu } from "@/components/hop-thoai";
import { Truong } from "@/components/ui/truong";
import { VungNhap } from "@/components/ui/o-nhap";
import type { LeaveRequest } from "@/lib/types";

export function HopThoaiTuChoi({
  don,
  tenNguoiGui,
  onDong,
}: {
  don: LeaveRequest;
  tenNguoiGui: string;
  onDong: () => void;
}) {
  const queryClient = useQueryClient();
  const [lyDo, setLyDo] = useState("");

  const tuChoi = useMutation({
    mutationFn: () => tuChoiDon(don.id, lyDo.trim()),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: khoaNhanSu.don.all });
      onDong();
    },
  });

  return (
    <HopThoai
      tieuDe={t("don.tuChoi")}
      moTa={tenNguoiGui}
      loi={tuChoi.isError ? thongDiepLoi(tuChoi.error) : null}
      onDong={onDong}
      chanDuoi={
        <>
          <NutPhu onClick={onDong} disabled={tuChoi.isPending}>
            {t("chung.huy")}
          </NutPhu>
          <NutChinh
            nguyHiem
            onClick={() => tuChoi.mutate()}
            disabled={tuChoi.isPending || lyDo.trim().length === 0}
          >
            {tuChoi.isPending ? t("nguoiDung.dangLuu") : t("don.tuChoi")}
          </NutChinh>
        </>
      }
    >
      <div className="mt-4">
        <Truong nhan={t("don.lyDoTuChoi")} batBuoc goiY={t("don.batBuocLyDoTuChoi")}>
          {(o) => (
            <VungNhap
              {...o}
              value={lyDo}
              onChange={(e) => setLyDo(e.target.value)}
              rows={3}
              autoFocus
              className="resize-none"
            />
          )}
        </Truong>
      </div>
    </HopThoai>
  );
}
