/**
 * Ai vào khu Báo cáo (#F5) và ai được chọn phòng.
 *
 * **Chỉ là UX, KHÔNG phải phân quyền** — như `quyen-quan-tri.ts`,
 * `quyen-tu-khoa.ts`. Backend là trọng tài; mỗi hàm chép một quy tắc đọc được từ
 * use case #5.
 */

import type { Role } from "./types";

/**
 * Có vào được khu Báo cáo không.
 *
 * `bao_dam_xem_bao_cao` (analytics) — **chỉ Manager/Admin**, Staff nhận 403
 * `ANALYTICS_MANAGER_REQUIRED` ở CẢ 4 endpoint (đã đo). Khác hẳn #F3/#F4 vốn cho
 * mọi vai. Dùng cho cả `ChanTheoVai` lẫn mục nav-rail.
 */
export function vaoDuocKhuBaoCao(vai: Role): boolean {
  return vai === "ADMIN" || vai === "MANAGER";
}

/**
 * Có hiện ô chọn phòng không — **chỉ Admin**.
 *
 * Manager bị `pham_vi_phong_bao_cao` ép về phòng mình (RB-4 của #5): truyền
 * `department_id` phòng khác thì backend IM LẶNG trả về phòng mình, HTTP 200. Ô
 * chọn phòng cho Manager sẽ nói dối — trông như đổi được mà không đổi gì. Đúng
 * tiền lệ `hienBoLocPhongBan()` của #F2.
 */
export function chiAdminLocPhong(vai: Role): boolean {
  return vai === "ADMIN";
}
