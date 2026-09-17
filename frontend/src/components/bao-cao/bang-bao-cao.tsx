"use client";

/**
 * Vỏ bảng chung cho 4 báo cáo: xử lý bốn trạng thái (đang tải · lỗi · rỗng ·
 * có dữ liệu) một chỗ để mỗi màn chỉ lo cột và dòng của nó.
 *
 * `[]` (khoảng không có dữ liệu) là **trạng thái bình thường HTTP 200** (đo
 * thật), nên hiện câu "không có dữ liệu" chứ không phải lỗi.
 */

import type { UseQueryResult } from "@tanstack/react-query";
import { t } from "@/lib/i18n";
import { thongDiepLoi } from "@/lib/loi-quan-tri";

export function BangBaoCao<T>({
  truyVan,
  tieuDeCot,
  children,
}: {
  truyVan: UseQueryResult<T[]>;
  /** Header các cột — render một `<tr>` chứa `<th>`. */
  tieuDeCot: React.ReactNode;
  /** Thân bảng khi có dữ liệu (đã bảo đảm `data.length > 0`). */
  children: (rows: T[]) => React.ReactNode;
}) {
  const rows = truyVan.data ?? [];

  return (
    <section className="overflow-hidden rounded-lg border border-border-subtle bg-white">
      {truyVan.isPending && (
        <p className="px-5 py-8 text-center text-sm text-muted">{t("baoCao.dangTai")}</p>
      )}
      {truyVan.isError && (
        <p className="px-5 py-8 text-center text-sm text-danger-fg">
          {thongDiepLoi(truyVan.error)}
        </p>
      )}
      {truyVan.data && rows.length === 0 && (
        <p className="px-5 py-8 text-center text-sm text-muted">{t("baoCao.trong")}</p>
      )}

      {rows.length > 0 && (
        <div className="overflow-x-auto">
          <table className="w-full border-collapse text-left">
            <thead>
              <tr className="border-b border-border-subtle bg-surface/60 text-[11px] font-bold uppercase tracking-wider text-muted">
                {tieuDeCot}
              </tr>
            </thead>
            <tbody>{children(rows)}</tbody>
          </table>
        </div>
      )}
    </section>
  );
}
