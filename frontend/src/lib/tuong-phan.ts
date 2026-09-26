/**
 * Tỉ lệ tương phản WCAG 2.x giữa hai màu hex `#rrggbb`.
 *
 * Dùng chung cho test khoá token (`tuong-phan.test.ts`) và trang
 * `/design-system` (hiện tỉ lệ thật cạnh từng mẫu màu) — một công thức, hai nơi.
 */

/**
 * Chuẩn hoá về `#rrggbb`. Trình duyệt / trình nén CSS có thể trả dạng rút gọn
 * `#111` — gặp ở `/design-system`: `getPropertyValue("--ink")` ra `#111`, tính
 * theo 6 ký tự thành NaN.
 */
function chuanHex(hex: string): string {
  const h = hex.trim();
  return /^#[0-9a-fA-F]{3}$/.test(h) ? `#${h[1]}${h[1]}${h[2]}${h[2]}${h[3]}${h[3]}` : h;
}

function doSang(mau: string): number {
  const hex = chuanHex(mau);
  const kenh = [1, 3, 5].map((i) => parseInt(hex.slice(i, i + 2), 16) / 255);
  const [r, g, b] = kenh.map((c) => (c <= 0.03928 ? c / 12.92 : ((c + 0.055) / 1.055) ** 2.4));
  return 0.2126 * r + 0.7152 * g + 0.0722 * b;
}

export function tuongPhan(a: string, b: string): number {
  const [sang, toi] = [doSang(a), doSang(b)].sort((x, y) => y - x);
  return (sang + 0.05) / (toi + 0.05);
}
