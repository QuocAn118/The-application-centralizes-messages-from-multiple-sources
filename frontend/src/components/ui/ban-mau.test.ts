/** Test bảng 8 màu dùng chung (nhãn, ca, avatar). */

import { describe, expect, it } from "vitest";
import { BAN_MAU, lopMau, mauTuId } from "./ban-mau";

describe("mauTuId", () => {
  it("cùng id luôn ra cùng màu (avatar không đổi màu mỗi lần tải)", () => {
    const id = "019fd148-249d-7a53-8ed4-24b7723d94fd";
    expect(mauTuId(id)).toBe(mauTuId(id));
  });

  it("luôn trong 1..8", () => {
    for (let i = 0; i < 500; i++) {
      const so = mauTuId(`id-${i}-${i * 7919}`);
      expect(so).toBeGreaterThanOrEqual(1);
      expect(so).toBeLessThanOrEqual(8);
    }
  });

  it("rải đều: 200 id phủ ít nhất 6/8 màu (không dồn một màu)", () => {
    const daGap = new Set<number>();
    for (let i = 0; i < 200; i++) daGap.add(mauTuId(`khach-${i}`));
    expect(daGap.size).toBeGreaterThanOrEqual(6);
  });

  it("UUID chỉ khác nhau ở đuôi vẫn ra màu khác nhau (UUIDv7 trùng tiền tố thời gian)", () => {
    const mau = new Set(
      ["a", "b", "c", "d", "e", "f"].map((d) => mauTuId(`019fd148-249d-7a53-8ed4-24b7723d94f${d}`)),
    );
    expect(mau.size).toBeGreaterThan(1);
  });

  it("chuỗi rỗng không ném lỗi", () => {
    expect(() => mauTuId("")).not.toThrow();
  });
});

describe("BAN_MAU / lopMau", () => {
  it("có đúng 8 màu và lớp Tailwind tương ứng", () => {
    expect(BAN_MAU).toHaveLength(8);
    expect(lopMau(1)).toBe("bg-swatch-1");
    expect(lopMau(8)).toBe("bg-swatch-8");
  });
});
