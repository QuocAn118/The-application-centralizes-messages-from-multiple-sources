/**
 * Badge kênh và badge trạng thái — nay dựng trên `IconKenh` / `HuyHieu` của design
 * system (redesign Phần 1). Giữ export cũ để màn hộp thư chưa làm lại vẫn chạy.
 */

import { NHAN_KENH, NHAN_TRANG_THAI } from "@/lib/hien-thi";
import type { ConversationStatus, Platform } from "@/lib/types";
import { HuyHieu, type TongHuyHieu } from "./ui/huy-hieu";
import { IconKenh } from "./ui/icon-kenh";

export function BadgeKenh({ platform }: { platform: Platform }) {
  return (
    <span className="inline-flex shrink-0 items-center gap-1 text-xs font-semibold text-ink-2">
      <IconKenh kenh={platform} co={13} />
      {NHAN_KENH[platform]}
    </span>
  );
}

const TONG_TRANG_THAI: Record<ConversationStatus, TongHuyHieu> = {
  CHO_PHAN: "wait",
  DANG_MO: "ok",
  DA_DONG: "trung",
};

export function BadgeTrangThai({ status }: { status: ConversationStatus }) {
  return <HuyHieu tong={TONG_TRANG_THAI[status]}>{NHAN_TRANG_THAI[status]}</HuyHieu>;
}
