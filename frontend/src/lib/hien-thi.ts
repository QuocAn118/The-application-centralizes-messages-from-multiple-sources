/**
 * Chuyển giá trị miền của backend sang chữ hiển thị cho người dùng.
 *
 * Tách khỏi component để nhãn không bị viết lại mỗi nơi một kiểu — giá trị enum
 * là của backend, còn cách gọi tên bằng tiếng Việt là quyết định của FE.
 */

import type { ConversationStatus, Platform, Role } from "./types";

export const NHAN_TRANG_THAI: Record<ConversationStatus, string> = {
  CHO_PHAN: "Chờ phân",
  DANG_MO: "Đang mở",
  DA_DONG: "Đã đóng",
};

export const NHAN_KENH: Record<Platform, string> = {
  ZALO: "Zalo",
  FACEBOOK: "Facebook",
  INSTAGRAM: "Instagram",
};

export const NHAN_VAI: Record<Role, string> = {
  STAFF: "Nhân viên",
  MANAGER: "Quản lý",
  ADMIN: "Quản trị",
};

/** Lớp Tailwind cho badge kênh — màu lấy từ design system. */
export const LOP_BADGE_KENH: Record<Platform, string> = {
  ZALO: "bg-zalo-bg text-zalo-fg",
  FACEBOOK: "bg-facebook-bg text-facebook-fg",
  INSTAGRAM: "bg-instagram-bg text-instagram-fg",
};

/** Lớp Tailwind cho badge trạng thái. */
export const LOP_BADGE_TRANG_THAI: Record<ConversationStatus, string> = {
  CHO_PHAN: "bg-cho-phan-bg text-cho-phan-fg",
  DANG_MO: "bg-dang-mo-bg text-dang-mo-fg",
  DA_DONG: "bg-da-dong-bg text-da-dong-fg",
};

/** Tên hiển thị của khách khi backend chưa có tên (kênh không trả về). */
export function tenKhach(ten: string | null): string {
  return ten?.trim() ? ten : "Khách chưa rõ tên";
}

/** Chữ cái đầu cho avatar. */
export function chuCaiDau(ten: string | null): string {
  const t = tenKhach(ten).trim();
  return t[0]?.toUpperCase() ?? "?";
}

/** Giờ:phút 24h dạng "14:32" — ghép tay để không lệch theo bản ICU. */
function gioPhutNgan(t: Date): string {
  const gio = String(t.getHours()).padStart(2, "0");
  const phut = String(t.getMinutes()).padStart(2, "0");
  return `${gio}:${phut}`;
}

/**
 * Ngày/tháng dạng "04/08".
 *
 * Ghép tay thay vì dùng `Intl.DateTimeFormat`: dấu phân cách của locale `vi-VN`
 * khác nhau tuỳ bản ICU (có môi trường cho ra "04-08"), mà mockup chốt dấu gạch
 * chéo. Định dạng cố định thì hiển thị giống nhau ở mọi máy.
 */
function ngayThangNgan(t: Date): string {
  const ngay = String(t.getDate()).padStart(2, "0");
  const thang = String(t.getMonth() + 1).padStart(2, "0");
  return `${ngay}/${thang}`;
}

/**
 * Mốc thời gian ngắn cho dòng danh sách: hôm nay hiện giờ, hôm qua hiện chữ,
 * xa hơn hiện ngày/tháng (khớp mockup: "14:32", "Hôm qua", "04/08").
 */
export function mocNgan(isoString: string): string {
  const t = new Date(isoString);
  if (Number.isNaN(t.getTime())) return "";

  const bayGio = new Date();
  const dauHomNay = new Date(
    bayGio.getFullYear(),
    bayGio.getMonth(),
    bayGio.getDate(),
  );
  const dauHomQua = new Date(dauHomNay);
  dauHomQua.setDate(dauHomQua.getDate() - 1);

  if (t >= dauHomNay) return gioPhutNgan(t);
  if (t >= dauHomQua) return "Hôm qua";
  return ngayThangNgan(t);
}

/** Mốc đầy đủ dùng cho thuộc tính `title` (xem chi tiết khi rê chuột). */
export function mocDayDu(isoString: string): string {
  const t = new Date(isoString);
  if (Number.isNaN(t.getTime())) return "";
  return t.toLocaleString("vi-VN");
}
