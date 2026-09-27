import { describe, expect, it } from "vitest";
import { khoangNhanh, loaiKhoangDangChon } from "./khoang-bao-cao";

const HOM_NAY = new Date(2026, 8, 27); // 27/9/2026

describe("khoangNhanh (B3)", () => {
  it("7 ngày / 30 ngày tính cả hôm nay", () => {
    expect(khoangNhanh("7-ngay", HOM_NAY)).toEqual({ tu: "2026-09-21", den: "2026-09-27" });
    expect(khoangNhanh("30-ngay", HOM_NAY)).toEqual({ tu: "2026-08-29", den: "2026-09-27" });
  });

  it("tháng này: từ ngày 1 đến hôm nay", () => {
    expect(khoangNhanh("thang-nay", HOM_NAY)).toEqual({ tu: "2026-09-01", den: "2026-09-27" });
  });

  it("tháng trước: trọn tháng, đúng số ngày, qua năm", () => {
    expect(khoangNhanh("thang-truoc", HOM_NAY)).toEqual({ tu: "2026-08-01", den: "2026-08-31" });
    expect(khoangNhanh("thang-truoc", new Date(2028, 2, 10))).toEqual({ tu: "2028-02-01", den: "2028-02-29" });
    expect(khoangNhanh("thang-truoc", new Date(2027, 0, 5))).toEqual({ tu: "2026-12-01", den: "2026-12-31" });
  });

  it("nhận ra khoảng đang chọn là khoảng nhanh nào; tự chọn thì null", () => {
    expect(loaiKhoangDangChon({ tu: "2026-08-01", den: "2026-08-31" }, HOM_NAY)).toBe("thang-truoc");
    expect(loaiKhoangDangChon({ tu: "2026-09-02", den: "2026-09-27" }, HOM_NAY)).toBeNull();
  });
});
