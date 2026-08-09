/**
 * Nút hành động nào được hiện, theo vai + trạng thái hội thoại (spec §3).
 *
 * **Đây chỉ là UX, KHÔNG phải phân quyền** (RB-3). Server mới là trọng tài: mọi
 * hành động vẫn có thể bị từ chối bằng 403/409/422 và UI phải xử lý tử tế. Ẩn
 * nút chỉ để người dùng khỏi bấm vào thứ chắc chắn hỏng.
 *
 * Quy tắc rút từ chính use case backend, không đoán:
 * - `TakeConversation` → `assign_to_agent` đòi `DANG_MO` + chưa có người nhận;
 *   phạm vi do `bao_dam_thao_tac` (đúng phòng, hoặc Admin).
 * - `CloseConversation` → `close` đòi `DANG_MO`; phạm vi như trên.
 * - `AssignConversationToDepartment` đòi vai MANAGER/ADMIN + `CHO_PHAN`, và
 *   **Manager chỉ được phân về phòng của chính mình**.
 */

import type { Conversation, Role } from "./types";

export interface Actor {
  role: Role;
  department_id: string | null;
}

/**
 * Người này có nằm trong phạm vi thao tác của hội thoại không.
 *
 * Bản sao của `co_the_thao_tac` phía backend — giữ đồng bộ khi backend đổi.
 */
export function trongPhamVi(actor: Actor, hoiThoai: Conversation): boolean {
  if (actor.role === "ADMIN") return true;
  if (hoiThoai.department_id === null) {
    // Hội thoại chờ-phân: chỉ Manager (và Admin ở trên) với tới được.
    return actor.role === "MANAGER";
  }
  return hoiThoai.department_id === actor.department_id;
}

/** Có hiện nút "Nhận việc" không. */
export function hienNhanViec(actor: Actor, hoiThoai: Conversation): boolean {
  return (
    trongPhamVi(actor, hoiThoai) &&
    hoiThoai.status === "DANG_MO" &&
    hoiThoai.assigned_user_id === null
  );
}

/** Có hiện nút "Đóng hội thoại" không. */
export function hienDong(actor: Actor, hoiThoai: Conversation): boolean {
  return trongPhamVi(actor, hoiThoai) && hoiThoai.status === "DANG_MO";
}

/** Có hiện nút "Phân phòng" không. */
export function hienPhanPhong(actor: Actor, hoiThoai: Conversation): boolean {
  if (hoiThoai.status !== "CHO_PHAN") return false;
  return actor.role === "MANAGER" || actor.role === "ADMIN";
}

/**
 * Các phòng người này được phép phân tới.
 *
 * Manager chỉ được phân về phòng của mình (`ASSIGN_OUT_OF_SCOPE` nếu cố khác),
 * nên lọc sẵn thay vì hiện cả danh sách rồi để server từ chối.
 */
export function phongCoTheChon<T extends { id: string }>(
  actor: Actor,
  phongBan: T[],
): T[] {
  if (actor.role === "ADMIN") return phongBan;
  if (actor.role === "MANAGER" && actor.department_id) {
    return phongBan.filter((p) => p.id === actor.department_id);
  }
  return [];
}
