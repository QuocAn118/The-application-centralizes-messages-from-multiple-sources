"use client";

/**
 * Gửi đơn từ (#F3 task 1.4).
 *
 * Chỉ `NGHI_PHEP` mới hiện khoảng ngày — hai loại còn lại backend không dùng
 * tới `leave_start`/`leave_end`, hiện ô nhập sẽ khiến người dùng tưởng phải
 * điền.
 */

import { useState } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { t } from "@/lib/i18n";
import { NHAN_LOAI_DON } from "@/lib/hien-thi";
import { guiDon, khoaNhanSu } from "@/lib/nhan-su-api";
import { thongDiepLoi } from "@/lib/loi-quan-tri";
import { HopThoai, NutChinh, NutPhu } from "@/components/hop-thoai";
import type { RequestType } from "@/lib/types";

const LOP_O_NHAP =
  "mt-1 w-full rounded-lg border border-border-subtle bg-white px-3 py-2 text-sm text-foreground outline-none transition focus:border-primary";

const LOAI_DON: readonly RequestType[] = ["NGHI_PHEP", "TANG_LUONG", "KHAC"] as const;

export function HopThoaiGuiDon({ onDong }: { onDong: () => void }) {
  const queryClient = useQueryClient();
  const [loai, setLoai] = useState<RequestType>("NGHI_PHEP");
  const [lyDo, setLyDo] = useState("");
  const [tuNgay, setTuNgay] = useState("");
  const [denNgay, setDenNgay] = useState("");

  const canKhoangNgay = loai === "NGHI_PHEP";
  const hopLe =
    lyDo.trim().length > 0 && (!canKhoangNgay || (tuNgay !== "" && denNgay !== ""));

  const gui = useMutation({
    mutationFn: () =>
      guiDon({
        request_type: loai,
        reason: lyDo.trim(),
        // Gửi `null` chứ không phải chuỗi rỗng cho loại không cần ngày:
        // `date | None` của backend không nhận "".
        leave_start: canKhoangNgay ? tuNgay : null,
        leave_end: canKhoangNgay ? denNgay : null,
      }),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: khoaNhanSu.don.all });
      onDong();
    },
  });

  return (
    <HopThoai
      tieuDe={t("don.guiDon")}
      loi={gui.isError ? thongDiepLoi(gui.error) : null}
      onDong={onDong}
      chanDuoi={
        <>
          <NutPhu onClick={onDong} disabled={gui.isPending}>
            {t("chung.huy")}
          </NutPhu>
          <NutChinh onClick={() => gui.mutate()} disabled={!hopLe || gui.isPending}>
            {gui.isPending ? t("nguoiDung.dangLuu") : t("don.guiDon")}
          </NutChinh>
        </>
      }
    >
      <div className="mt-4 space-y-3">
        <label className="block">
          <span className="text-xs font-medium text-muted">{t("don.loaiDon")}</span>
          <select
            value={loai}
            onChange={(e) => setLoai(e.target.value as RequestType)}
            className={LOP_O_NHAP}
          >
            {LOAI_DON.map((l) => (
              <option key={l} value={l}>
                {NHAN_LOAI_DON[l]}
              </option>
            ))}
          </select>
        </label>

        {canKhoangNgay && (
          <div className="flex gap-3">
            <label className="block flex-1">
              <span className="text-xs font-medium text-muted">{t("don.tuNgay")}</span>
              <input
                type="date"
                value={tuNgay}
                onChange={(e) => {
                  setTuNgay(e.target.value);
                  // Kéo ngày kết thúc theo nếu nó đang ở trước ngày bắt đầu —
                  // để người dùng khỏi gửi một khoảng ngược rồi nhận 422.
                  if (denNgay && e.target.value > denNgay) setDenNgay(e.target.value);
                }}
                className={LOP_O_NHAP}
              />
            </label>
            <label className="block flex-1">
              <span className="text-xs font-medium text-muted">{t("don.denNgay")}</span>
              <input
                type="date"
                value={denNgay}
                min={tuNgay || undefined}
                onChange={(e) => setDenNgay(e.target.value)}
                className={LOP_O_NHAP}
              />
            </label>
          </div>
        )}

        <label className="block">
          <span className="text-xs font-medium text-muted">{t("don.lyDo")}</span>
          <textarea
            value={lyDo}
            onChange={(e) => setLyDo(e.target.value)}
            rows={3}
            className={`${LOP_O_NHAP} resize-none`}
          />
        </label>
      </div>
    </HopThoai>
  );
}
