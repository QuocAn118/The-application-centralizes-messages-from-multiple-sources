/** Test quyền khu Từ khoá (#F4, trả nợ N6). */

import { describe, expect, it } from "vitest";
import { quanLyDuocTuKhoa } from "./quyen-tu-khoa";
import type { Role } from "./types";

const MOI_VAI: Role[] = ["ADMIN", "MANAGER", "STAFF"];

describe("quanLyDuocTuKhoa", () => {
  it("Manager và Admin sửa được", () => {
    expect(quanLyDuocTuKhoa("MANAGER")).toBe(true);
    expect(quanLyDuocTuKhoa("ADMIN")).toBe(true);
  });

  it("Staff KHÔNG sửa được (KEYWORD_MANAGER_REQUIRED)", () => {
    expect(quanLyDuocTuKhoa("STAFF")).toBe(false);
  });

  it("phủ đủ mọi vai, không vai nào rơi vào undefined", () => {
    // Nếu sau này thêm vai mới, hàm phải trả boolean chứ không undefined —
    // `undefined` là falsy nên nút sẽ im lặng biến mất mà không ai biết.
    for (const vai of MOI_VAI) {
      expect(typeof quanLyDuocTuKhoa(vai)).toBe("boolean");
    }
  });
});
