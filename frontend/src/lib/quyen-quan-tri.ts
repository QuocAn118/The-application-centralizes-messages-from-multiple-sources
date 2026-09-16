/**
 * Ai được vào màn nào và bấm nút nào trong khu quản trị (#F2 spec §3).
 *
 * **Đây chỉ là UX, KHÔNG phải phân quyền** (RB-1) — hệt như `quyen-hanh-dong.ts`
 * của #F1. Backend mới là trọng tài: mọi thao tác vẫn có thể bị từ chối bằng
 * 403 và UI phải xử lý tử tế. Ẩn nút chỉ để người dùng khỏi bấm vào thứ chắc
 * chắn hỏng.
 *
 * Mỗi hàm dưới đây chép lại đúng một quy tắc đọc được từ use case backend; chỗ
 * nào chép được thì ghi nguồn để sau này đối chiếu khi backend đổi.
 */

import type { Role, UserResponse } from "./types";

/** Người đang đăng nhập, rút gọn còn phần quyết định quyền. */
export interface NguoiThaoTac {
  id: string;
  role: Role;
  department_id: string | null;
}

// ---------------------------------------------------------------------------
// Vào màn
// ---------------------------------------------------------------------------

/**
 * Có thấy mục "Cấu hình" ở thanh điều hướng không.
 *
 * Manager thấy, vì họ vào được màn Người dùng (phòng mình). Staff không.
 */
export function vaoDuocKhuQuanTri(vai: Role): boolean {
  return vai === "ADMIN" || vai === "MANAGER";
}

/** Màn Người dùng: Admin toàn bộ, Manager chỉ phòng mình (`list_users.py:35-44`). */
export function vaoDuocManNguoiDung(vai: Role): boolean {
  return vai === "ADMIN" || vai === "MANAGER";
}

/** Ba màn còn lại (Phòng ban · Kênh · Nhật ký) chỉ Admin. */
export function chiAdmin(vai: Role): boolean {
  return vai === "ADMIN";
}

// ---------------------------------------------------------------------------
// Thao tác trên người dùng
// ---------------------------------------------------------------------------

/**
 * Bản sao của `User.can_manage` phía backend
 * (`identity/domain/entities/user.py:236-246`).
 *
 * Admin quản mọi người. Manager **chỉ quản Staff CÙNG PHÒNG** — không quản
 * được Manager khác, kể cả cùng phòng.
 */
export function quanLyDuoc(actor: NguoiThaoTac, doiTuong: UserResponse): boolean {
  if (actor.role === "ADMIN") return true;
  if (actor.role === "MANAGER") {
    return doiTuong.role === "STAFF" && doiTuong.department_id === actor.department_id;
  }
  return false;
}

/** Tạo tài khoản — chỉ Admin (`create_user.py:63`). */
export function hienTaoTaiKhoan(actor: NguoiThaoTac): boolean {
  return actor.role === "ADMIN";
}

/**
 * Sửa hồ sơ (tên, điện thoại) — chính mình hoặc người mình quản được
 * (`update_user.py:43-49`).
 */
export function hienSuaHoSo(actor: NguoiThaoTac, doiTuong: UserResponse): boolean {
  return actor.id === doiTuong.id || quanLyDuoc(actor, doiTuong);
}

/** Đổi vai trò — chỉ Admin (`change_user_role.py:41`). */
export function hienDoiVaiTro(actor: NguoiThaoTac): boolean {
  return actor.role === "ADMIN";
}

/** Đổi phòng ban — chỉ Admin. */
export function hienDoiPhongBan(actor: NguoiThaoTac): boolean {
  return actor.role === "ADMIN";
}

/**
 * Vô hiệu hoá / kích hoạt lại — chỉ Admin (`deactivate_user.py:39`).
 *
 * Không tự chặn "Admin hoạt động cuối cùng" ở đây: FE không biết còn bao nhiêu
 * Admin đang hoạt động, mà đoán rồi ẩn nút sai còn tệ hơn. Backend trả
 * `LAST_ADMIN_CANNOT_BE_DEACTIVATED` kèm thông điệp tiếng Việt, UI hiện thẳng
 * (RB-4).
 *
 * Riêng **chính mình** thì chặn hẳn — tự khoá tài khoản của mình luôn là nhầm.
 */
export function hienVoHieuHoa(actor: NguoiThaoTac, doiTuong: UserResponse): boolean {
  return actor.role === "ADMIN" && actor.id !== doiTuong.id;
}

/** Đặt lại mật khẩu người khác — chỉ Admin (`reset_user_password.py:44`). */
export function hienDatLaiMatKhau(actor: NguoiThaoTac, doiTuong: UserResponse): boolean {
  // Mật khẩu của chính mình đổi ở `/doi-mat-khau` (cần mật khẩu cũ), không
  // phải bằng đường đặt lại của Admin.
  return actor.role === "ADMIN" && actor.id !== doiTuong.id;
}

/**
 * Các vai được chọn trong ô "Đổi vai trò".
 *
 * **Không có ADMIN**: backend trả `CANNOT_CHANGE_TO_ADMIN` — chỉ đổi qua lại
 * giữa Nhân viên và Quản lý (phát hiện lúc đọc `user.py`, xem RB-4).
 */
export const VAI_DOI_DUOC: readonly Role[] = ["STAFF", "MANAGER"] as const;

/** Có hiện bộ lọc phòng ban ở màn Người dùng không (RB-2). */
export function hienBoLocPhongBan(vai: Role): boolean {
  // Manager bị backend ghi đè `department_id` về phòng mình, nên bộ lọc sẽ
  // trông như "không ăn". Ẩn hẳn thay vì để người ta bấm vào rồi bối rối.
  return vai === "ADMIN";
}
