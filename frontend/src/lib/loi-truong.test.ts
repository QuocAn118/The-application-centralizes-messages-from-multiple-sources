import { describe, expect, it } from "vitest";
import { ApiError } from "./api-client";
import { loiTheoTruong } from "./loi-truong";

const MA = { EMAIL_ALREADY_EXISTS: "email", WEAK_PASSWORD: "matKhau" } as const;
const TEN = { email: "email", full_name: "hoTen" } as const;

describe("loiTheoTruong", () => {
  it("khớp mã nghiệp vụ → đúng ô, giữ thông điệp server", () => {
    const loi = new ApiError(409, "EMAIL_ALREADY_EXISTS", "Email đã được dùng.");
    expect(loiTheoTruong(loi, MA, TEN)).toEqual({ truong: "email", thongDiep: "Email đã được dùng." });
  });

  it("422 FastAPI → theo tên trường cuối của loc", () => {
    const loi = new ApiError(422, "VALIDATION_ERROR", "Dữ liệu gửi lên không hợp lệ.", {
      cac_loi: [{ loc: ["body", "full_name"], msg: "String should have at least 1 character" }],
    });
    expect(loiTheoTruong(loi, MA, TEN).truong).toBe("hoTen");
  });

  it("không khớp ô nào → truong null, thông điệp chung", () => {
    const loi = new ApiError(409, "DEPARTMENT_ALREADY_HAS_MANAGER", "Phòng đã có quản lý.");
    expect(loiTheoTruong(loi, MA, TEN)).toEqual({ truong: null, thongDiep: "Phòng đã có quản lý." });
    expect(loiTheoTruong(new TypeError("fetch failed"), MA).truong).toBeNull();
  });
});
