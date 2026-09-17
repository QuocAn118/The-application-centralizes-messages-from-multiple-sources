/** Test quyền khu Báo cáo (#F5). */

import { describe, expect, it } from "vitest";
import { chiAdminLocPhong, vaoDuocKhuBaoCao } from "./quyen-bao-cao";
import type { Role } from "./types";

const MOI_VAI: Role[] = ["ADMIN", "MANAGER", "STAFF"];

describe("vaoDuocKhuBaoCao", () => {
  it("Manager và Admin vào được", () => {
    expect(vaoDuocKhuBaoCao("MANAGER")).toBe(true);
    expect(vaoDuocKhuBaoCao("ADMIN")).toBe(true);
  });

  it("Staff KHÔNG vào được (ANALYTICS_MANAGER_REQUIRED) — khác #F3/#F4", () => {
    expect(vaoDuocKhuBaoCao("STAFF")).toBe(false);
  });

  it("phủ đủ mọi vai, luôn trả boolean", () => {
    for (const vai of MOI_VAI) {
      expect(typeof vaoDuocKhuBaoCao(vai)).toBe("boolean");
    }
  });
});

describe("chiAdminLocPhong", () => {
  it("chỉ Admin — Manager bị backend ép phạm vi nên không cho chọn phòng (RB-1)", () => {
    expect(chiAdminLocPhong("ADMIN")).toBe(true);
    expect(chiAdminLocPhong("MANAGER")).toBe(false);
    expect(chiAdminLocPhong("STAFF")).toBe(false);
  });
});
