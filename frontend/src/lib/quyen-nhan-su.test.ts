/**
 * Quyền ở khu Nhân sự (#F3 task 1.6).
 *
 * Trọng tâm là **RB-2** — quy tắc duyệt đơn phụ thuộc vai của NGƯỜI GỬI, không
 * phải của người duyệt. Đây là chỗ dễ làm sai nhất của cả #F3, và sai thì
 * không có gì báo: nút hiện ra, bấm vào mới nhận 403.
 */

import { describe, expect, it } from "vitest";
import {
  datDuocMucTieuKpi,
  hienDuyet,
  hienGuiDon,
  hienThuHoi,
  nhanVienPhanCaDuoc,
  quanLyDuocCa,
  xemDuocKpiPhong,
  type NguoiNhanSu,
} from "./quyen-nhan-su";
import type { LeaveRequest, UserResponse } from "./types";

const PHONG_A = "11111111-1111-1111-1111-111111111111";
const PHONG_B = "22222222-2222-2222-2222-222222222222";

const admin: NguoiNhanSu = { id: "u-admin", role: "ADMIN", department_id: null };
const managerA: NguoiNhanSu = { id: "u-mgr-a", role: "MANAGER", department_id: PHONG_A };
const managerB: NguoiNhanSu = { id: "u-mgr-b", role: "MANAGER", department_id: PHONG_B };
const staffA: NguoiNhanSu = { id: "u-staff-a", role: "STAFF", department_id: PHONG_A };

function don(ghiDe: Partial<LeaveRequest> = {}): LeaveRequest {
  return {
    id: "d-1",
    requester_id: staffA.id,
    department_id: PHONG_A,
    request_type: "NGHI_PHEP",
    reason: "Về quê",
    status: "CHO_DUYET",
    created_at: "2026-09-16T08:00:00Z",
    leave_start: "2026-09-20",
    leave_end: "2026-09-22",
    decided_by: null,
    decided_at: null,
    decision_reason: null,
    ...ghiDe,
  };
}

function nguoi(ghiDe: Partial<UserResponse> = {}): UserResponse {
  return {
    id: "u-1",
    email: "a@congty.vn",
    full_name: "Nguyễn Văn A",
    phone: null,
    role: "STAFF",
    department_id: PHONG_A,
    is_active: true,
    must_change_password: false,
    last_login_at: null,
    created_at: "2026-09-01T00:00:00Z",
    ...ghiDe,
  };
}

describe("RB-2 — đơn của STAFF", () => {
  it("Manager đúng phòng duyệt được", () => {
    expect(hienDuyet(managerA, don(), "STAFF")).toBe(true);
  });

  it("Manager phòng KHÁC không duyệt được", () => {
    expect(hienDuyet(managerB, don({ department_id: PHONG_A }), "STAFF")).toBe(false);
  });

  it("Admin duyệt được", () => {
    expect(hienDuyet(admin, don(), "STAFF")).toBe(true);
  });

  it("Staff khác không duyệt được", () => {
    const staffKhac: NguoiNhanSu = {
      id: "u-staff-khac",
      role: "STAFF",
      department_id: PHONG_A,
    };
    expect(hienDuyet(staffKhac, don(), "STAFF")).toBe(false);
  });
});

describe("RB-2 — đơn của MANAGER", () => {
  const donCuaManager = don({ requester_id: managerA.id, department_id: PHONG_A });

  it("CHỈ Admin duyệt được", () => {
    expect(hienDuyet(admin, donCuaManager, "MANAGER")).toBe(true);
  });

  it("Manager KHÁC cùng phòng KHÔNG duyệt được", () => {
    // Chỗ dễ sai nhất: cùng phòng và đúng vai Manager, nhưng người GỬI cũng là
    // Manager nên chỉ Admin mới quyết được.
    const managerKhac: NguoiNhanSu = {
      id: "u-mgr-khac",
      role: "MANAGER",
      department_id: PHONG_A,
    };
    expect(hienDuyet(managerKhac, donCuaManager, "MANAGER")).toBe(false);
  });

  it("Staff không duyệt được", () => {
    expect(hienDuyet(staffA, donCuaManager, "MANAGER")).toBe(false);
  });
});

describe("RB-2 — không ai tự duyệt đơn của chính mình", () => {
  it("Admin không duyệt đơn của chính Admin", () => {
    expect(hienDuyet(admin, don({ requester_id: admin.id }), "ADMIN")).toBe(false);
  });

  it("Manager không duyệt đơn của chính mình dù đúng phòng", () => {
    expect(
      hienDuyet(managerA, don({ requester_id: managerA.id }), "MANAGER"),
    ).toBe(false);
  });
});

describe("RB-2 — đơn đã có quyết định thì không còn nút", () => {
  it.each(["DA_DUYET", "TU_CHOI", "DA_HUY"] as const)(
    "trạng thái %s không hiện nút duyệt",
    (status) => {
      expect(hienDuyet(admin, don({ status }), "STAFF")).toBe(false);
    },
  );
});

describe("RB-2 — không tra được vai người gửi", () => {
  it("Manager VẪN thấy nút khi không biết vai người gửi", () => {
    // Người gửi nằm ngoài trang danh sách đã tải. Ẩn nút của người có quyền thì
    // họ bế tắc không hiểu vì sao; hiện nhầm chỉ tốn một lần bấm và nhận thông
    // điệp rõ ràng từ server.
    expect(hienDuyet(managerA, don(), null)).toBe(true);
  });

  it("nhưng vẫn tôn trọng phạm vi phòng", () => {
    expect(hienDuyet(managerB, don({ department_id: PHONG_A }), null)).toBe(false);
  });
});

describe("RB-1 — gửi đơn", () => {
  it("Admin KHÔNG gửi được (không thuộc phòng nào)", () => {
    expect(hienGuiDon(admin)).toBe(false);
  });

  it("Manager và Staff gửi được", () => {
    expect(hienGuiDon(managerA)).toBe(true);
    expect(hienGuiDon(staffA)).toBe(true);
  });

  it("Staff chưa gắn phòng cũng không gửi được", () => {
    // Kiểm theo `department_id` chứ không theo vai, nên trường hợp này đúng
    // luôn mà không cần luật riêng.
    expect(hienGuiDon({ id: "x", role: "STAFF", department_id: null })).toBe(false);
  });
});

describe("Thu hồi đơn", () => {
  it("chỉ người gửi, và chỉ khi còn chờ duyệt", () => {
    expect(hienThuHoi(staffA, don())).toBe(true);
    expect(hienThuHoi(staffA, don({ status: "DA_DUYET" }))).toBe(false);
    expect(hienThuHoi(managerA, don())).toBe(false);
  });
});

describe("Ca làm việc", () => {
  it("chỉ Manager/Admin quản lý được ca", () => {
    expect(quanLyDuocCa("STAFF")).toBe(false);
    expect(quanLyDuocCa("MANAGER")).toBe(true);
    expect(quanLyDuocCa("ADMIN")).toBe(true);
  });

  it("RB-6: chỉ hiện nhân viên đang hoạt động CÙNG PHÒNG với mẫu ca", () => {
    const danhSach = [
      nguoi({ id: "a", department_id: PHONG_A }),
      nguoi({ id: "b", department_id: PHONG_B }),
      nguoi({ id: "c", department_id: PHONG_A, is_active: false }),
      nguoi({ id: "d", department_id: null, role: "ADMIN" }),
    ];
    expect(nhanVienPhanCaDuoc(danhSach, PHONG_A).map((u) => u.id)).toEqual(["a"]);
  });
});

describe("KPI", () => {
  it("chỉ Manager/Admin đặt được mục tiêu", () => {
    expect(datDuocMucTieuKpi("STAFF")).toBe(false);
    expect(datDuocMucTieuKpi("MANAGER")).toBe(true);
  });

  it("Staff không xem được KPI cấp phòng", () => {
    expect(xemDuocKpiPhong("STAFF")).toBe(false);
    expect(xemDuocKpiPhong("MANAGER")).toBe(true);
    expect(xemDuocKpiPhong("ADMIN")).toBe(true);
  });
});
