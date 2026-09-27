"use client";

/**
 * Vỏ bảng chung cho 4 báo cáo: xử lý bốn trạng thái (đang tải · lỗi · rỗng ·
 * có dữ liệu) một chỗ để mỗi màn chỉ lo cột và dòng của nó.
 *
 * `[]` (khoảng không có dữ liệu) là **trạng thái bình thường HTTP 200** (đo
 * thật), nên hiện trạng thái rỗng chứ không phải lỗi.
 */

import { BarChart3 } from "lucide-react";
import type { UseQueryResult } from "@tanstack/react-query";
import { t } from "@/lib/i18n";
import { thongDiepLoi } from "@/lib/loi-quan-tri";
import { Bang } from "@/components/ui/bang";
import { The } from "@/components/ui/the";
import { TrangThaiLoi, TrangThaiRong, TrangThaiTai } from "@/components/ui/trang-thai";

export function BangBaoCao<T>({
  truyVan,
  nhan,
  tieuDeCot,
  children,
}: {
  truyVan: UseQueryResult<T[]>;
  /** Tên truy cập của bảng (đọc màn hình). */
  nhan: string;
  /** Header các cột — các `<Th>`. */
  tieuDeCot: React.ReactNode;
  /** Thân bảng khi có dữ liệu (đã bảo đảm `data.length > 0`). */
  children: (rows: T[]) => React.ReactNode;
}) {
  const rows = truyVan.data ?? [];

  if (truyVan.isPending)
    return (
      <The as="div">
        <TrangThaiTai dong={4} />
      </The>
    );
  if (truyVan.isError)
    return (
      <The as="div">
        <TrangThaiLoi thongDiep={thongDiepLoi(truyVan.error)} onThuLai={() => void truyVan.refetch()} />
      </The>
    );
  if (rows.length === 0)
    return (
      <The as="div">
        <TrangThaiRong icon={BarChart3} tieuDe={t("baoCao.trong")} moTa={t("baoCao.trongGoiY")} />
      </The>
    );

  return (
    <Bang aria-label={nhan}>
      <thead>
        <tr>{tieuDeCot}</tr>
      </thead>
      <tbody>{children(rows)}</tbody>
    </Bang>
  );
}

/** Dòng tổng cuối bảng: kẻ đậm, nền lõm, chữ đậm. */
export function DongTong({ children }: { children: React.ReactNode }) {
  return <tr className="border-t-2 border-ink bg-sunken font-bold text-ink">{children}</tr>;
}
