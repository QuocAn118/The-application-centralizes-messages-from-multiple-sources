/**
 * IT-2 (spec §8): ô soạn disabled đúng theo trạng thái (RB-5).
 *
 * Kiểm ở tầng logic thuần thay vì dựng DOM: `lyDoKhoa` là nơi duy nhất quyết
 * định ô khoá hay mở, nên test nó là test đúng chỗ ra quyết định.
 */

import { describe, expect, it } from "vitest";
import { lyDoKhoa } from "./o-soan-tin";

describe("lyDoKhoa — RB-5", () => {
  it("DANG_MO thì gõ được", () => {
    expect(lyDoKhoa("DANG_MO")).toBeNull();
  });

  it("CHO_PHAN thì khoá, gợi ý phân phòng hoặc nhận việc", () => {
    const ly_do = lyDoKhoa("CHO_PHAN");
    expect(ly_do).not.toBeNull();
    expect(ly_do).toMatch(/phân phòng|nhận việc/i);
  });

  it("DA_DONG thì khoá, nói rõ hội thoại đã đóng", () => {
    const ly_do = lyDoKhoa("DA_DONG");
    expect(ly_do).not.toBeNull();
    expect(ly_do).toMatch(/đã đóng/i);
  });

  it("mọi trạng thái không phải DANG_MO đều khoá", () => {
    // Bảo hiểm cho tương lai: thêm trạng thái mới mà quên xử lý thì mặc định
    // phải là KHOÁ, không phải mở — sai theo hướng an toàn.
    for (const s of ["CHO_PHAN", "DA_DONG"] as const) {
      expect(lyDoKhoa(s)).not.toBeNull();
    }
  });
});
