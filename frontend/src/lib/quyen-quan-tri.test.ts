/**
 * Quyền hiển thị nút ở khu quản trị (#F2 task 1.8, spec §3).
 *
 * Nhắc lại RB-1: đây là UX, không phải phân quyền. Test này bảo đảm FE không
 * mời người dùng bấm thứ chắc chắn bị server từ chối — nó KHÔNG thay cho việc
 * backend chặn.
 *
 * Trọng tâm là `quanLyDuoc`, bản sao của `User.can_manage` phía backend. Chỗ
 * dễ sai nhất: Manager **không** quản được Manager khác cùng phòng.
 */

import { describe, expect, it } from "vitest";
import {
  VAI_DOI_DUOC,
  chiAdmin,
  hienBoLocPhongBan,
  hienDatLaiMatKhau,
  hienDoiPhongBan,
  hienDoiVaiTro,
  hienSuaHoSo,
  hienTaoTaiKhoan,
  hienVoHieuHoa,
  quanLyDuoc,
  vaoDuocKhuQuanTri,
  vaoDuocManNguoiDung,
  type NguoiThaoTac,
} from "./quyen-quan-tri";
import type { Role, UserResponse } from "./types";

const PHONG_A = "11111111-1111-1111-1111-111111111111";
const PHONG_B = "22222222-2222-2222-2222-222222222222";

const admin: NguoiThaoTac = { id: "u-admin", role: "ADMIN", department_id: null };
const manager: NguoiThaoTac = { id: "u-mgr", role: "MANAGER", department_id: PHONG_A };
const staff: NguoiThaoTac = { id: "u-staff", role: "STAFF", department_id: PHONG_A };

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

describe("vào được màn nào", () => {
  it("Staff không vào được khu quản trị", () => {
    expect(vaoDuocKhuQuanTri("STAFF")).toBe(false);
    expect(vaoDuocManNguoiDung("STAFF")).toBe(false);
  });

  it("Manager vào được màn Người dùng nhưng không vào được ba màn chỉ-Admin", () => {
    expect(vaoDuocKhuQuanTri("MANAGER")).toBe(true);
    expect(vaoDuocManNguoiDung("MANAGER")).toBe(true);
    expect(chiAdmin("MANAGER")).toBe(false);
  });

  it("Admin vào được tất cả", () => {
    expect(vaoDuocKhuQuanTri("ADMIN")).toBe(true);
    expect(chiAdmin("ADMIN")).toBe(true);
  });
});

describe("quanLyDuoc — bản sao User.can_manage", () => {
  it("Admin quản được mọi người, kể cả Admin khác", () => {
    expect(quanLyDuoc(admin, nguoi({ role: "ADMIN", department_id: null }))).toBe(true);
    expect(quanLyDuoc(admin, nguoi({ role: "MANAGER" }))).toBe(true);
    expect(quanLyDuoc(admin, nguoi())).toBe(true);
  });

  it("Manager quản được Staff CÙNG phòng", () => {
    expect(quanLyDuoc(manager, nguoi({ role: "STAFF", department_id: PHONG_A }))).toBe(
      true,
    );
  });

  it("Manager KHÔNG quản được Staff phòng khác", () => {
    expect(quanLyDuoc(manager, nguoi({ role: "STAFF", department_id: PHONG_B }))).toBe(
      false,
    );
  });

  it("Manager KHÔNG quản được Manager khác dù cùng phòng", () => {
    // Chỗ dễ sai nhất: "cùng phòng" chưa đủ, đối tượng phải là STAFF.
    expect(
      quanLyDuoc(manager, nguoi({ role: "MANAGER", department_id: PHONG_A })),
    ).toBe(false);
  });

  it("Staff không quản được ai", () => {
    expect(quanLyDuoc(staff, nguoi({ department_id: PHONG_A }))).toBe(false);
  });
});

describe("nút theo quyền", () => {
  it("chỉ Admin thấy nút tạo tài khoản", () => {
    expect(hienTaoTaiKhoan(admin)).toBe(true);
    expect(hienTaoTaiKhoan(manager)).toBe(false);
  });

  it("ai cũng sửa được hồ sơ CỦA CHÍNH MÌNH", () => {
    const hoSoManager = nguoi({ id: manager.id, role: "MANAGER" });
    // Manager không "quản" được chính mình theo can_manage, nhưng vẫn phải sửa
    // được hồ sơ của mình — đây là hai điều kiện HOẶC, không phải VÀ.
    expect(quanLyDuoc(manager, hoSoManager)).toBe(false);
    expect(hienSuaHoSo(manager, hoSoManager)).toBe(true);
  });

  it("đổi vai trò và đổi phòng chỉ Admin", () => {
    expect(hienDoiVaiTro(manager)).toBe(false);
    expect(hienDoiPhongBan(manager)).toBe(false);
    expect(hienDoiVaiTro(admin)).toBe(true);
    expect(hienDoiPhongBan(admin)).toBe(true);
  });

  it("Admin không tự vô hiệu hoá hay tự đặt lại mật khẩu của chính mình", () => {
    const chinhMinh = nguoi({ id: admin.id, role: "ADMIN", department_id: null });
    expect(hienVoHieuHoa(admin, chinhMinh)).toBe(false);
    expect(hienDatLaiMatKhau(admin, chinhMinh)).toBe(false);
  });

  it("Manager không thấy nút vô hiệu hoá dù với Staff phòng mình", () => {
    // `deactivate_user.py:39` đòi Admin — Manager quản được hồ sơ nhưng không
    // vô hiệu hoá được.
    const nhanVien = nguoi({ role: "STAFF", department_id: PHONG_A });
    expect(quanLyDuoc(manager, nhanVien)).toBe(true);
    expect(hienVoHieuHoa(manager, nhanVien)).toBe(false);
  });
});

describe("RB-2 — bộ lọc phòng ban", () => {
  it("Manager không thấy bộ lọc phòng ban", () => {
    // Backend ghi đè `department_id` về phòng của Manager, nên bộ lọc sẽ trông
    // như không ăn.
    expect(hienBoLocPhongBan("MANAGER")).toBe(false);
    expect(hienBoLocPhongBan("ADMIN")).toBe(true);
  });
});

describe("RB-4 — không đổi được sang Quản trị", () => {
  it("danh sách vai đổi được KHÔNG chứa ADMIN", () => {
    // Backend trả `CANNOT_CHANGE_TO_ADMIN`; hiện lựa chọn đó là mời người dùng
    // vào một thất bại đã biết trước.
    expect(VAI_DOI_DUOC).not.toContain("ADMIN" satisfies Role);
    expect([...VAI_DOI_DUOC].sort()).toEqual(["MANAGER", "STAFF"]);
  });
});
