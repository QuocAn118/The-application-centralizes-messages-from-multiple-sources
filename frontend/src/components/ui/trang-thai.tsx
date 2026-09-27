/**
 * Ba trạng thái mà mọi màn dữ liệu phải có (X9): đang tải, rỗng, lỗi.
 * Trước đây mỗi màn một kiểu, có màn chỉ in "Đang tải…".
 */

import { CircleAlert, RefreshCw, type LucideIcon } from "lucide-react";
import { t } from "@/lib/i18n";
import { Nut } from "./nut";

/**
 * Khung xương theo hình dạng hàng thật — người dùng thấy trước bố cục, không
 * phải vòng quay giữa màn. `aria-busy` + chữ ẩn cho trình đọc màn hình.
 */
export function TrangThaiTai({ dong = 5 }: { dong?: number }) {
  return (
    <div aria-busy="true" className="flex flex-col">
      <span className="sr-only">{t("chung.dangTai")}</span>
      {Array.from({ length: dong }, (_, i) => (
        <div key={i} className="flex items-center gap-4 border-t border-line px-5 py-4 first:border-t-0">
          <div className="size-9 shrink-0 animate-pulse rounded-nb bg-sunken" />
          <div className="flex flex-1 flex-col gap-2">
            <div className="h-3 w-1/3 animate-pulse rounded-[3px] bg-sunken" />
            <div className="h-3 w-2/3 animate-pulse rounded-[3px] bg-sunken" />
          </div>
        </div>
      ))}
    </div>
  );
}

/** Rỗng: nói rõ vì sao trống và làm gì để có dữ liệu (nếu người này làm được). */
export function TrangThaiRong({
  icon: Icon,
  tieuDe,
  moTa,
  hanhDong,
}: {
  icon: LucideIcon;
  tieuDe: string;
  moTa?: string;
  hanhDong?: React.ReactNode;
}) {
  return (
    <div className="flex flex-col items-center gap-3 px-6 py-12 text-center">
      <span className="inline-flex size-12 items-center justify-center rounded-nb border-2 border-ink bg-accent">
        <Icon aria-hidden className="size-6 text-ink" strokeWidth={2.25} />
      </span>
      <p className="text-base font-bold text-ink">{tieuDe}</p>
      {moTa && <p className="max-w-[48ch] text-sm text-ink-2">{moTa}</p>}
      {hanhDong && <div className="mt-1">{hanhDong}</div>}
    </div>
  );
}

/** Lỗi: hiện thẳng thông điệp server (đã tiếng Việt) + nút thử lại nếu có. */
export function TrangThaiLoi({
  thongDiep,
  onThuLai,
  hanhDong,
}: {
  thongDiep: string;
  onThuLai?: () => void;
  hanhDong?: React.ReactNode;
}) {
  return (
    <div role="alert" className="flex flex-col items-center gap-3 px-6 py-12 text-center">
      <span className="inline-flex size-12 items-center justify-center rounded-nb border-2 border-bad bg-bad-bg">
        <CircleAlert aria-hidden className="size-6 text-bad" strokeWidth={2.25} />
      </span>
      <p className="max-w-[48ch] text-sm font-semibold text-ink">{thongDiep}</p>
      {(onThuLai || hanhDong) && (
        <div className="mt-1 flex gap-2">
          {onThuLai && (
            <Nut bienThe="phu" co="sm" icon={RefreshCw} onClick={onThuLai}>
              {t("chung.thuLai")}
            </Nut>
          )}
          {hanhDong}
        </div>
      )}
    </div>
  );
}
