/**
 * Test tiện ích hiển thị.
 *
 * `mocNgan` so theo RANH GIỚI NGÀY chứ không theo "24 giờ trước": một tin lúc
 * 23:50 hôm qua vẫn phải là "Hôm qua" khi xem lúc 00:10 hôm nay, dù mới cách
 * 20 phút. Đây là chỗ dễ viết sai nhất nên có test riêng.
 */

import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { chuCaiDau, mocNgan, tenKhach } from "./hien-thi";

describe("mocNgan", () => {
  beforeEach(() => {
    vi.useFakeTimers();
    // Mốc "bây giờ": 05/08/2026 lúc 00:10 giờ địa phương.
    vi.setSystemTime(new Date(2026, 7, 5, 0, 10, 0));
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  it("tin trong hôm nay hiện giờ:phút", () => {
    const t = new Date(2026, 7, 5, 0, 5, 0).toISOString();
    expect(mocNgan(t)).toMatch(/00:05/);
  });

  it("tin cuối ngày hôm qua vẫn là 'Hôm qua' dù chỉ cách 20 phút", () => {
    const t = new Date(2026, 7, 4, 23, 50, 0).toISOString();
    expect(mocNgan(t)).toBe("Hôm qua");
  });

  it("tin cũ hơn hai ngày hiện ngày/tháng", () => {
    const t = new Date(2026, 7, 1, 9, 0, 0).toISOString();
    expect(mocNgan(t)).toMatch(/01\/08/);
  });

  it("chuỗi thời gian hỏng trả về rỗng thay vì 'Invalid Date'", () => {
    expect(mocNgan("khong-phai-ngay")).toBe("");
  });
});

describe("tenKhach / chuCaiDau", () => {
  it("thiếu tên thì có nhãn thay thế, không để trống", () => {
    expect(tenKhach(null)).toBe("Khách chưa rõ tên");
    expect(tenKhach("   ")).toBe("Khách chưa rõ tên");
  });

  it("giữ nguyên tên có thật", () => {
    expect(tenKhach("Nguyễn Thị Mai")).toBe("Nguyễn Thị Mai");
  });

  it("chữ cái đầu viết hoa, thiếu tên vẫn có ký tự hiển thị", () => {
    expect(chuCaiDau("nguyễn thị mai")).toBe("N");
    expect(chuCaiDau(null)).toBe("K");
  });
});
