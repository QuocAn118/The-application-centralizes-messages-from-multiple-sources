/**
 * Badge kênh và badge trạng thái (mockup Stitch).
 *
 * Không phải Client Component: chỉ render theo prop, không có trạng thái nội bộ.
 */

import {
  LOP_BADGE_KENH,
  LOP_BADGE_TRANG_THAI,
  NHAN_KENH,
  NHAN_TRANG_THAI,
} from "@/lib/hien-thi";
import type { ConversationStatus, Platform } from "@/lib/types";

export function BadgeKenh({ platform }: { platform: Platform }) {
  return (
    <span
      className={`inline-flex shrink-0 items-center gap-1 rounded-full px-2 py-0.5 text-[11px] font-medium ${LOP_BADGE_KENH[platform]}`}
    >
      <span className="h-1.5 w-1.5 rounded-full bg-current" aria-hidden />
      {NHAN_KENH[platform]}
    </span>
  );
}

export function BadgeTrangThai({ status }: { status: ConversationStatus }) {
  return (
    <span
      className={`inline-flex shrink-0 items-center rounded-full px-2 py-0.5 text-[11px] font-medium ${LOP_BADGE_TRANG_THAI[status]}`}
    >
      {NHAN_TRANG_THAI[status]}
    </span>
  );
}
