/**
 * Ai sửa được gì ở khu Từ khoá (#F4).
 *
 * **Chỉ là UX, KHÔNG phải phân quyền** — như `quyen-quan-tri.ts` và
 * `quyen-nhan-su.ts`. Backend là trọng tài.
 *
 * Khác khu Cấu hình của #F2 ở chỗ **Staff cũng vào và xem được**, chỉ không sửa.
 */

import type { Role } from "./types";

/**
 * Có tạo/sửa/xoá từ khoá được không.
 *
 * `bao_dam_quan_ly_hoac_admin` — Manager hoặc Admin, Staff nhận 403
 * `KEYWORD_MANAGER_REQUIRED`. Manager còn bị siết thêm về đúng phòng mình
 * (`KEYWORD_OUT_OF_SCOPE`), kiểm riêng ở từng dòng.
 */
export function quanLyDuocTuKhoa(vai: Role): boolean {
  return vai === "MANAGER" || vai === "ADMIN";
}
