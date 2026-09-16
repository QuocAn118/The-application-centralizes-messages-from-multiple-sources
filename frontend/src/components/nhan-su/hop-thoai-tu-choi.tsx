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
      <label className="mt-4 block">
        <span className="text-xs font-medium text-muted">{t("don.lyDoTuChoi")}</span>
        <textarea
          value={lyDo}
          onChange={(e) => setLyDo(e.target.value)}
          rows={3}
          autoFocus
          className="mt-1 w-full resize-none rounded-lg border border-border-subtle bg-white px-3 py-2 text-sm text-foreground outline-none transition focus:border-primary"
        />
        <span className="mt-1 block text-xs text-muted-soft">
          {t("don.batBuocLyDoTuChoi")}
        </span>
      </label>
    </HopThoai>
  );
}
