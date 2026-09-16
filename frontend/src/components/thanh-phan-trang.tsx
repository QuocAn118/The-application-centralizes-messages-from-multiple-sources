"use client";

/**
 * Thanh phân trang dùng chung cho cả bốn màn quản trị (#F2 task 1.3).
 *
 * Nhận `offset`/`limit`/`total` thô của `PageResponse` chứ không nhận "số
 * trang": backend nói bằng offset, đổi qua lại ở nhiều nơi là nguồn lỗi lệch
 * một trang.
 */

import { t } from "@/lib/i18n";

export function ThanhPhanTrang({
  offset,
  limit,
  total,
  doiOffset,
  dangTai = false,
}: {
  offset: number;
  limit: number;
  total: number;
  doiOffset: (offsetMoi: number) => void;
  dangTai?: boolean;
}) {
  if (total === 0) return null;

  const tu = offset + 1;
  const den = Math.min(offset + limit, total);
  const coTruoc = offset > 0;
  const coSau = den < total;

  return (
    <div className="flex items-center justify-between border-t border-border-subtle px-4 py-3">
      <p className="text-xs text-muted">
        {t("quanTri.hienThi", { tu, den, tong: total })}
      </p>
      <div className="flex gap-2">
        <button
          type="button"
          disabled={!coTruoc || dangTai}
          onClick={() => doiOffset(Math.max(0, offset - limit))}
          className="rounded-lg border border-border-subtle px-3 py-1.5 text-xs font-medium text-foreground transition enabled:hover:bg-surface disabled:cursor-not-allowed disabled:text-muted-soft"
        >
          {t("quanTri.truoc")}
        </button>
        <button
          type="button"
          disabled={!coSau || dangTai}
          onClick={() => doiOffset(offset + limit)}
          className="rounded-lg border border-border-subtle px-3 py-1.5 text-xs font-medium text-foreground transition enabled:hover:bg-surface disabled:cursor-not-allowed disabled:text-muted-soft"
        >
          {t("quanTri.sau")}
        </button>
      </div>
    </div>
  );
}
