/**
 * Bảng 8 màu dịu dùng chung: nền avatar, màu ca làm việc, màu nhãn khách.
 *
 * Nhãn (BE-6) **chỉ được chọn trong bảng này** (quyết định GĐ1 #3): mọi màu đã
 * kiểm chữ `ink` ≥ 12:1 trong `lib/tuong-phan.test.ts`, nên không có nhãn nào
 * khó đọc. Giá trị hex nằm ở `globals.css` (`--swatch-1..8`), không chép ra đây.
 */

/** Lớp Tailwind đầy đủ, viết tường minh để Tailwind quét được (không ghép chuỗi động). */
export const BAN_MAU = [
  "bg-swatch-1",
  "bg-swatch-2",
  "bg-swatch-3",
  "bg-swatch-4",
  "bg-swatch-5",
  "bg-swatch-6",
  "bg-swatch-7",
  "bg-swatch-8",
] as const;

export type SoMau = 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8;

/**
 * Màu ổn định suy từ một id (FNV-1a 32-bit): cùng id luôn cùng màu.
 *
 * Băm cả chuỗi chứ không lấy vài ký tự đầu: UUIDv7 của hệ thống trùng tiền tố
 * thời gian, lấy đầu chuỗi thì khách tạo cùng lúc sẽ cùng màu.
 */
export function mauTuId(id: string): SoMau {
  let h = 0x811c9dc5;
  for (let i = 0; i < id.length; i++) {
    h ^= id.charCodeAt(i);
    h = Math.imul(h, 0x01000193);
  }
  return (((h >>> 0) % 8) + 1) as SoMau;
}

export function lopMau(so: SoMau): (typeof BAN_MAU)[number] {
  return BAN_MAU[so - 1];
}
