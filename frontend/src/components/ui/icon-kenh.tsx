/**
 * Icon kênh — chỉ dùng ở cỡ nhỏ, mỗi kênh một màu (đặc tả).
 *
 * lucide-react **không có logo thương hiệu** (không Facebook, Instagram, Zalo,
 * Telegram), và cả brief lẫn taste-skill cấm vẽ SVG tay. Nên mỗi kênh dùng một
 * glyph chung có HÌNH KHÁC NHAU (phân biệt được cả khi không thấy màu) + màu kênh
 * + tên trong `title`/`aria-label`:
 * - Telegram: máy bay giấy — trùng ý logo thật.
 * - Zalo: bong bóng chat — trùng ý logo thật.
 * - Instagram: máy ảnh. Facebook: ngón cái.
 */

import { Camera, MessageCircle, Send, ThumbsUp, type LucideIcon } from "lucide-react";
import { NHAN_KENH } from "@/lib/hien-thi";
import type { Platform } from "@/lib/types";

const ICON: Record<Platform, LucideIcon> = {
  ZALO: MessageCircle,
  FACEBOOK: ThumbsUp,
  INSTAGRAM: Camera,
  TELEGRAM: Send,
};

const MAU: Record<Platform, string> = {
  ZALO: "text-zalo",
  FACEBOOK: "text-facebook",
  INSTAGRAM: "text-instagram",
  TELEGRAM: "text-telegram",
};

export function IconKenh({ kenh, co = 16 }: { kenh: Platform; co?: number }) {
  const Icon = ICON[kenh];
  return (
    <Icon
      role="img"
      aria-label={NHAN_KENH[kenh]}
      width={co}
      height={co}
      strokeWidth={2.5}
      className={`shrink-0 ${MAU[kenh]}`}
    >
      <title>{NHAN_KENH[kenh]}</title>
    </Icon>
  );
}
