/**
 * IT-3 (spec §8): nút hành động ẩn/hiện đúng theo vai + trạng thái (§3).
 *
 * Nhắc lại: đây là UX, không phải phân quyền. Test này bảo đảm FE không mời
 * người dùng bấm thứ chắc chắn bị server từ chối — chứ không thay việc xử lý
 * 403/409/422, vốn được kiểm ở test của api-client.
 */

import { describe, expect, it } from "vitest";
import {
  hienDong,
  hienNhanViec,
  hienPhanPhong,
  phongCoTheChon,
  trongPhamVi,
  type Actor,
} from "./quyen-hanh-dong";
import type { Conversation } from "./types";

const PHONG_A = "11111111-1111-1111-1111-111111111111";
const PHONG_B = "22222222-2222-2222-2222-222222222222";
const AI_DO = "99999999-9999-9999-9999-999999999999";

const staff: Actor = { role: "STAFF", department_id: PHONG_A };
const manager: Actor = { role: "MANAGER", department_id: PHONG_A };
const admin: Actor = { role: "ADMIN", department_id: null };

function hoiThoai(ghiDe: Partial<Conversation> = {}): Conversation {
  return {
    conversation_id: "c1",
    channel_id: "ch1",
    platform: "ZALO",
    customer_id: "kh1",
    customer_display_name: "Nguyễn Thị Mai",
    status: "DANG_MO",
    department_id: PHONG_A,
    assigned_user_id: null,
    last_message_at: "2026-08-05T10:00:00Z",
    messages: [],
    ...ghiDe,
  };
}

describe("trongPhamVi", () => {
  it("Admin chạm được mọi hội thoại", () => {
    expect(trongPhamVi(admin, hoiThoai({ department_id: PHONG_B }))).toBe(true);
    expect(trongPhamVi(admin, hoiThoai({ department_id: null }))).toBe(true);
  });

  it("Staff/Manager chỉ chạm hội thoại phòng mình", () => {
    expect(trongPhamVi(staff, hoiThoai({ department_id: PHONG_A }))).toBe(true);
    expect(trongPhamVi(staff, hoiThoai({ department_id: PHONG_B }))).toBe(false);
    expect(trongPhamVi(manager, hoiThoai({ department_id: PHONG_B }))).toBe(false);
  });

  it("hội thoại chờ-phân: Manager với tới, Staff thì không", () => {
    const choPhan = hoiThoai({ status: "CHO_PHAN", department_id: null });
    expect(trongPhamVi(manager, choPhan)).toBe(true);
    expect(trongPhamVi(staff, choPhan)).toBe(false);
  });
});

describe("hienNhanViec", () => {
  it("hiện khi DANG_MO và chưa ai nhận", () => {
    expect(hienNhanViec(staff, hoiThoai())).toBe(true);
  });

  it("ẩn khi đã có người nhận", () => {
    expect(hienNhanViec(staff, hoiThoai({ assigned_user_id: AI_DO }))).toBe(false);
  });

  it("ẩn khi không phải DANG_MO", () => {
    expect(hienNhanViec(staff, hoiThoai({ status: "DA_DONG" }))).toBe(false);
    expect(
      hienNhanViec(manager, hoiThoai({ status: "CHO_PHAN", department_id: null })),
    ).toBe(false);
  });

  it("ẩn khi ngoài phạm vi phòng", () => {
    expect(hienNhanViec(staff, hoiThoai({ department_id: PHONG_B }))).toBe(false);
  });
});

describe("hienDong", () => {
  it("hiện khi DANG_MO, kể cả đã có người nhận", () => {
    expect(hienDong(staff, hoiThoai())).toBe(true);
    expect(hienDong(staff, hoiThoai({ assigned_user_id: AI_DO }))).toBe(true);
  });

  it("ẩn khi đã đóng hoặc chờ phân", () => {
    expect(hienDong(staff, hoiThoai({ status: "DA_DONG" }))).toBe(false);
    expect(
      hienDong(manager, hoiThoai({ status: "CHO_PHAN", department_id: null })),
    ).toBe(false);
  });
});

describe("hienPhanPhong", () => {
  const choPhan = hoiThoai({ status: "CHO_PHAN", department_id: null });

  it("Manager và Admin thấy khi CHO_PHAN", () => {
    expect(hienPhanPhong(manager, choPhan)).toBe(true);
    expect(hienPhanPhong(admin, choPhan)).toBe(true);
  });

  it("Staff không bao giờ thấy", () => {
    expect(hienPhanPhong(staff, choPhan)).toBe(false);
  });

  it("ẩn khi hội thoại không còn chờ phân", () => {
    expect(hienPhanPhong(manager, hoiThoai({ status: "DANG_MO" }))).toBe(false);
    expect(hienPhanPhong(admin, hoiThoai({ status: "DA_DONG" }))).toBe(false);
  });
});

describe("phongCoTheChon", () => {
  const phongBan = [
    { id: PHONG_A, name: "Phòng Kinh doanh" },
    { id: PHONG_B, name: "Phòng Kỹ thuật" },
  ];

  it("Admin chọn được mọi phòng", () => {
    expect(phongCoTheChon(admin, phongBan)).toHaveLength(2);
  });

  it("Manager CHỈ chọn được phòng của mình (backend chặn ASSIGN_OUT_OF_SCOPE)", () => {
    const duoc = phongCoTheChon(manager, phongBan);
    expect(duoc).toHaveLength(1);
    expect(duoc[0].id).toBe(PHONG_A);
  });

  it("Staff không chọn được phòng nào", () => {
    expect(phongCoTheChon(staff, phongBan)).toHaveLength(0);
  });
});
