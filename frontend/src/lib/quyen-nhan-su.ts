/**
 * Ai thấy gì và bấm được gì ở khu Nhân sự (#F3 spec §3).
 *
 * **Chỉ là UX, KHÔNG phải phân quyền** — như `quyen-quan-tri.ts`. Backend là
 * trọng tài; ẩn nút chỉ để người dùng khỏi bấm vào thứ chắc chắn hỏng.
 *
 * Khác khu quản trị ở chỗ **Staff cũng vào được cả ba màn**, chỉ thấy ít hơn.
 */

import type { LeaveRequest, Role, UserResponse } from "./types";

export interface NguoiNhanSu {
  id: string;
  role: Role;
  department_id: string | null;
}

// ---------------------------------------------------------------------------
// Ca làm việc
// ---------------------------------------------------------------------------

/**
 * Có được tạo/sửa/ngừng mẫu ca và phân ca không.
 *
 * `bao_dam_quan_ly_hoac_admin` — Manager hoặc Admin. Manager còn bị siết thêm
 * về đúng phòng mình ở `bao_dam_quan_ly_dung_phong`, nhưng FE không cần lặp
 * lại: ô chọn phòng của Manager chỉ có một lựa chọn.
 */
export function quanLyDuocCa(vai: Role): boolean {
  return vai === "MANAGER" || vai === "ADMIN";
}

/**
 * Nhân viên được phép phân vào một mẫu ca.
 *
 * Backend trả `AGENT_OUT_OF_DEPARTMENT` nếu nhân viên khác phòng với mẫu ca
 * (RB-6), nên lọc sẵn thay vì hiện cả công ty rồi để server từ chối.
 *
 * Chỉ lấy người **đang hoạt động**: `AssignShift` đòi `get_agent` trả về người
 * còn hiệu lực (`AGENT_NOT_FOUND`).
 */
export function nhanVienPhanCaDuoc(
  danhSach: UserResponse[],
  departmentIdCuaCa: string,
): UserResponse[] {
  return danhSach.filter(
    (u) => u.is_active && u.department_id === departmentIdCuaCa,
  );
}

// ---------------------------------------------------------------------------
// Đơn từ
// ---------------------------------------------------------------------------

/**
 * Có hiện nút "Gửi đơn" không (RB-1).
 *
 * Admin **không gửi đơn được**: `SubmitRequest` đòi người gửi có
 * `department_id`, mà Admin không thuộc phòng nào
 * (`ADMIN_CANNOT_HAVE_DEPARTMENT` ở #F2). Ẩn nút thay vì để họ điền xong rồi
 * nhận `REQUESTER_HAS_NO_DEPARTMENT`.
 *
 * Kiểm theo `department_id` chứ không theo vai: nếu sau này có Staff chưa gắn
 * phòng thì cũng đúng luôn.
 */
export function hienGuiDon(actor: NguoiNhanSu): boolean {
  return actor.department_id !== null;
}

/** Có hiện nút "Thu hồi" không — chỉ người gửi, và chỉ khi còn chờ duyệt. */
export function hienThuHoi(actor: NguoiNhanSu, don: LeaveRequest): boolean {
  return don.requester_id === actor.id && don.status === "CHO_DUYET";
}

/**
 * Có hiện nút "Duyệt"/"Từ chối" không (RB-2).
 *
 * **Quy tắc phụ thuộc vai của NGƯỜI GỬI, không phải của người duyệt** — đây là
 * chỗ dễ làm sai nhất của #F3:
 *
 * - Đơn của Staff → Admin, hoặc Manager đúng phòng của đơn.
 * - Đơn của Manager → **chỉ Admin**.
 * - Không ai tự duyệt đơn của chính mình, kể cả Admin.
 *
 * ``vaiNguoiGui`` là `null` khi FE không tra được (người gửi nằm ngoài trang
 * danh sách đã tải). Khi đó **vẫn hiện nút** và để server quyết: ẩn nhầm nút
 * của người có quyền thì họ bế tắc không hiểu vì sao, còn hiện nhầm thì chỉ tốn
 * một lần bấm và nhận thông điệp rõ ràng.
 */
export function hienDuyet(
  actor: NguoiNhanSu,
  don: LeaveRequest,
  vaiNguoiGui: Role | null,
): boolean {
  if (don.status !== "CHO_DUYET") return false;
  if (don.requester_id === actor.id) return false;

  if (actor.role === "ADMIN") return true;
  if (actor.role !== "MANAGER") return false;

  // Manager chỉ duyệt được đơn trong phòng mình…
  if (don.department_id !== actor.department_id) return false;
  // …và không duyệt được đơn của Manager khác (kể cả cùng phòng).
  return vaiNguoiGui !== "MANAGER";
}

// ---------------------------------------------------------------------------
// KPI
// ---------------------------------------------------------------------------

/** Có được đặt mục tiêu KPI không — Manager (phòng mình) hoặc Admin. */
export function datDuocMucTieuKpi(vai: Role): boolean {
  return vai === "MANAGER" || vai === "ADMIN";
}

/**
 * Có xem được KPI **cấp phòng** không.
 *
 * Staff bị chặn hẳn (`KPI_FORBIDDEN` khi `subject_type = DEPARTMENT`), nên
 * không hiện lựa chọn đó trong ô chọn đối tượng.
 */
export function xemDuocKpiPhong(vai: Role): boolean {
  return vai !== "STAFF";
}
