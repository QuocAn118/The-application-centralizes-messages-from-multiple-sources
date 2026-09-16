/**
 * Chuyển giá trị miền của backend sang chữ hiển thị cho người dùng.
 *
 * Tách khỏi component để nhãn không bị viết lại mỗi nơi một kiểu — giá trị enum
 * là của backend, còn cách gọi tên bằng tiếng Việt là quyết định của FE.
 */

import { t } from "./i18n";
import type { AuditAction, ConversationStatus, Platform, Role } from "./types";

// Nhãn lấy từ từ điển i18n — một nguồn duy nhất, đổi ngôn ngữ là đổi cả đây.
export const NHAN_TRANG_THAI: Record<ConversationStatus, string> = {
  CHO_PHAN: t("trangThai.CHO_PHAN"),
  DANG_MO: t("trangThai.DANG_MO"),
  DA_DONG: t("trangThai.DA_DONG"),
};

export const NHAN_KENH: Record<Platform, string> = {
  ZALO: t("kenh.ZALO"),
  FACEBOOK: t("kenh.FACEBOOK"),
  INSTAGRAM: t("kenh.INSTAGRAM"),
  TELEGRAM: t("kenh.TELEGRAM"),
};

export const NHAN_VAI: Record<Role, string> = {
  STAFF: t("vai.STAFF"),
  MANAGER: t("vai.MANAGER"),
  ADMIN: t("vai.ADMIN"),
};

/** Lớp Tailwind cho badge kênh — màu lấy từ design system. */
export const LOP_BADGE_KENH: Record<Platform, string> = {
  ZALO: "bg-zalo-bg text-zalo-fg",
  FACEBOOK: "bg-facebook-bg text-facebook-fg",
  INSTAGRAM: "bg-instagram-bg text-instagram-fg",
  TELEGRAM: "bg-telegram-bg text-telegram-fg",
};

/** Lớp Tailwind cho badge trạng thái. */
export const LOP_BADGE_TRANG_THAI: Record<ConversationStatus, string> = {
  CHO_PHAN: "bg-cho-phan-bg text-cho-phan-fg",
  DANG_MO: "bg-dang-mo-bg text-dang-mo-fg",
  DA_DONG: "bg-da-dong-bg text-da-dong-fg",
};

/** Tên hiển thị của khách khi backend chưa có tên (kênh không trả về). */
export function tenKhach(ten: string | null): string {
  return ten?.trim() ? ten : t("inbox.khachChuaRoTen");
}

/** Chữ cái đầu cho avatar. */
export function chuCaiDau(ten: string | null): string {
  const daCat = tenKhach(ten).trim();
  return daCat[0]?.toUpperCase() ?? "?";
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

/**
 * Lớp Tailwind cho badge vai trò (#F2).
 *
 * "Quản trị" dùng tím để tách hẳn khỏi primary xanh — nhìn lướt bảng là thấy
 * ngay ai có toàn quyền.
 */
export const LOP_BADGE_VAI: Record<Role, string> = {
  ADMIN: "bg-admin-bg text-admin-fg",
  MANAGER: "bg-zalo-bg text-zalo-fg",
  STAFF: "bg-da-dong-bg text-da-dong-fg",
};

/**
 * Nhãn tiếng Việt cho 15 hành động nhật ký (#F2 GĐ4).
 *
 * RB-9: `Record<AuditAction, string>` bắt TypeScript đòi đủ 15 khoá — thiếu
 * một khoá là lỗi biên dịch, không phải `undefined` lặng lẽ hiện giữa bảng
 * (đúng cái đã xảy ra với `TELEGRAM`). Có thêm test duyệt toàn bộ enum ở
 * `hien-thi.test.ts` để phòng trường hợp ai đó bỏ chú thích kiểu hoặc ép kiểu.
 */
export const NHAN_HANH_DONG: Record<AuditAction, string> = {
  "user.created": t("hanhDong.user.created"),
  "user.updated": t("hanhDong.user.updated"),
  "user.deactivated": t("hanhDong.user.deactivated"),
  "user.reactivated": t("hanhDong.user.reactivated"),
  "user.role_changed": t("hanhDong.user.role_changed"),
  "user.department_changed": t("hanhDong.user.department_changed"),
  "user.password_reset": t("hanhDong.user.password_reset"),
  "user.password_changed": t("hanhDong.user.password_changed"),
  "department.created": t("hanhDong.department.created"),
  "department.updated": t("hanhDong.department.updated"),
  "department.deactivated": t("hanhDong.department.deactivated"),
  "auth.login_succeeded": t("hanhDong.auth.login_succeeded"),
  "auth.login_failed": t("hanhDong.auth.login_failed"),
  "auth.logout": t("hanhDong.auth.logout"),
  "auth.token_reuse_detected": t("hanhDong.auth.token_reuse_detected"),
};

/** Tiền tố nhóm của một hành động — dùng để tô màu và lọc. */
export type NhomHanhDong = "user" | "department" | "auth";

export function nhomCuaHanhDong(hanhDong: AuditAction): NhomHanhDong {
  // Backend đặt tên dạng `<đối tượng>.<hành động>` chính là để tách được thế này.
  return hanhDong.split(".")[0] as NhomHanhDong;
}

/**
 * Lớp Tailwind cho badge hành động.
 *
 * `auth.login_failed` và `auth.token_reuse_detected` tô màu cảnh báo: đó là hai
 * dòng người đọc nhật ký cần thấy ngay khi lướt qua.
 */
export function lopBadgeHanhDong(hanhDong: AuditAction): string {
  if (hanhDong === "auth.token_reuse_detected") {
    return "bg-danger-bg text-danger-fg";
  }
  if (hanhDong === "auth.login_failed") return "bg-cho-phan-bg text-cho-phan-fg";

  const nhom = nhomCuaHanhDong(hanhDong);
  if (nhom === "user") return "bg-zalo-bg text-zalo-fg";
  if (nhom === "department") return "bg-admin-bg text-admin-fg";
  return "bg-da-dong-bg text-da-dong-fg";
}
