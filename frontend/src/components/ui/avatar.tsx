/**
 * Avatar khách: ô vuông bo 6px (khoá hình dạng — không tròn), màu nền suy ổn
 * định từ id (`mauTuId`) để phân biệt khách bằng mắt, chữ cái đầu của tên.
 * Có `kenh` thì gắn icon kênh nhỏ ở góc — thay cho tag kênh lặp ở mọi dòng (I1).
 */

import { chuCaiDau } from "@/lib/hien-thi";
import type { Platform } from "@/lib/types";
import { lopMau, mauTuId } from "./ban-mau";
import { IconKenh } from "./icon-kenh";

const CO = {
  sm: { khung: "size-8 text-sm", goc: "size-4", icon: 10 },
  md: { khung: "size-10 text-base", goc: "size-5", icon: 12 },
} as const;

export function Avatar({
  id,
  ten,
  kenh,
  co = "md",
}: {
  id: string;
  ten: string | null;
  kenh?: Platform;
  co?: keyof typeof CO;
}) {
  const kichThuoc = CO[co];
  return (
    <span className="relative inline-flex shrink-0" aria-hidden={kenh ? undefined : true}>
      <span
        className={`${kichThuoc.khung} ${lopMau(mauTuId(id))} inline-flex items-center justify-center rounded-nb border-2 border-ink font-extrabold text-ink`}
      >
        {chuCaiDau(ten)}
      </span>
      {kenh && (
        <span
          className={`${kichThuoc.goc} absolute -bottom-1 -right-1 inline-flex items-center justify-center rounded-[4px] border-2 border-ink bg-card`}
        >
          <IconKenh kenh={kenh} co={kichThuoc.icon} />
        </span>
      )}
    </span>
  );
}
