/**
 * Logo kênh — logo THƯƠNG HIỆU THẬT từ gói `simple-icons` (quyết định sau duyệt
 * Phần 1), mỗi kênh một màu, chỉ dùng ở cỡ nhỏ.
 *
 * Nguồn path (ghi trong gói simple-icons 16.x):
 * - Zalo: https://zalo.me
 * - Telegram: https://telegram.org/tour/screenshots
 * - Instagram: https://about.meta.com/brand/resources/instagram
 * - Facebook: https://about.meta.com/brand/resources/facebook/logo
 *
 * Màu: dùng token `--zalo` … (globals.css) — màu chính thức, riêng Telegram làm
 * đậm để đạt ≥ 3:1 (xem chú thích ở globals.css, khoá bằng tuong-phan.test.ts).
 * Import từng icon theo tên để bundle chỉ mang đúng 4 path này.
 */

import { siFacebook, siInstagram, siTelegram, siZalo, type SimpleIcon } from "simple-icons";
import { NHAN_KENH } from "@/lib/hien-thi";
import type { Platform } from "@/lib/types";

const LOGO: Record<Platform, SimpleIcon> = {
  ZALO: siZalo,
  FACEBOOK: siFacebook,
  INSTAGRAM: siInstagram,
  TELEGRAM: siTelegram,
};

const MAU: Record<Platform, string> = {
  ZALO: "text-zalo",
  FACEBOOK: "text-facebook",
  INSTAGRAM: "text-instagram",
  TELEGRAM: "text-telegram",
};

export function IconKenh({ kenh, co = 16 }: { kenh: Platform; co?: number }) {
  if (kenh === "ZALO") {
    // Path Zalo của simple-icons là CHỮ "Zalo" (wordmark), không phải biểu tượng
    // gọn như ba kênh kia: ở 16px nó thành một vệt chữ không đọc được. Dựng theo
    // đúng bố cục icon ứng dụng chính thức của Zalo — chữ trắng trên ô xanh — vẫn
    // dùng NGUYÊN path chính thức, không vẽ tay. Chữ trắng trên #0068FF: 4,7:1.
    return (
      <svg role="img" aria-label={NHAN_KENH.ZALO} viewBox="0 0 24 24" width={co} height={co} className="shrink-0 text-zalo">
        <title>{NHAN_KENH.ZALO}</title>
        <rect width="24" height="24" rx="5" fill="currentColor" />
        <path d={siZalo.path} fill="#fff" transform="translate(12 12) scale(0.86) translate(-12 -12)" />
      </svg>
    );
  }
  return (
    <svg
      role="img"
      aria-label={NHAN_KENH[kenh]}
      viewBox="0 0 24 24"
      width={co}
      height={co}
      fill="currentColor"
      className={`shrink-0 ${MAU[kenh]}`}
    >
      <title>{NHAN_KENH[kenh]}</title>
      <path d={LOGO[kenh].path} />
    </svg>
  );
}
