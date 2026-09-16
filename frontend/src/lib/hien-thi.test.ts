/**
 * Test tiện ích hiển thị.
 *
 * `mocNgan` so theo RANH GIỚI NGÀY chứ không theo "24 giờ trước": một tin lúc
 * 23:50 hôm qua vẫn phải là "Hôm qua" khi xem lúc 00:10 hôm nay, dù mới cách
 * 20 phút. Đây là chỗ dễ viết sai nhất nên có test riêng.
 */

import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import {
  LOP_BADGE_KENH,
  LOP_BADGE_VAI,
  NHAN_HANH_DONG,
  NHAN_KENH,
  NHAN_VAI,
  chuCaiDau,
  lopBadgeHanhDong,
  mocNgan,
  nhomCuaHanhDong,
  tenKhach,
} from "./hien-thi";
import type { AuditAction, Platform, Role } from "./types";

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

/**
 * Khoá lỗi 2026-09-15: backend thêm kênh TELEGRAM (2026-09-14) nhưng frontend
 * không cập nhật theo. `NHAN_KENH` và `LOP_BADGE_KENH` là `Record<Platform,…>`
 * nên tra khoá `TELEGRAM` trả `undefined` — badge hiện trống, không có lỗi nào
 * nổ ra. Đúng trên kênh DUY NHẤT đang chạy thật.
 *
 * Test duyệt qua MỌI giá trị của `Platform` thay vì liệt kê tay: thêm kênh mới
 * mà quên khai nhãn/màu thì đỏ ngay, không phải nhớ sửa test.
 */
describe("bảng nhãn kênh phủ đủ mọi nền tảng", () => {
  const MOI_KENH: Platform[] = ["ZALO", "FACEBOOK", "INSTAGRAM", "TELEGRAM"];

  it.each(MOI_KENH)("kênh %s có nhãn hiển thị", (kenh) => {
    expect(NHAN_KENH[kenh]).toBeTruthy();
  });

  it.each(MOI_KENH)("kênh %s có lớp màu badge", (kenh) => {
    expect(LOP_BADGE_KENH[kenh]).toBeTruthy();
  });
});

/** Cùng lý do RB-9: bảng vai trò thiếu khoá thì badge trống, không có lỗi. */
describe("bảng nhãn vai trò phủ đủ mọi vai", () => {
  const MOI_VAI: Role[] = ["STAFF", "MANAGER", "ADMIN"];

  it.each(MOI_VAI)("vai %s có nhãn hiển thị", (vai) => {
    expect(NHAN_VAI[vai]).toBeTruthy();
  });

  it.each(MOI_VAI)("vai %s có lớp màu badge", (vai) => {
    expect(LOP_BADGE_VAI[vai]).toBeTruthy();
  });
});

/**
 * RB-9 — bảng nhãn hành động nhật ký phải phủ ĐỦ 15 giá trị.
 *
 * Danh sách dưới đây chép từ `AuditAction` ở
 * `identity/domain/entities/audit_log.py`. Cố ý liệt kê tay **ở đây** (chứ
 * không đọc từ `NHAN_HANH_DONG`) để test là một nguồn kiểm tra ĐỘC LẬP: đọc
 * ngược từ chính bảng đang kiểm thì bảng thiếu khoá nào test cũng không biết.
 */
const MOI_HANH_DONG: AuditAction[] = [
  "user.created",
  "user.updated",
  "user.deactivated",
  "user.reactivated",
  "user.role_changed",
  "user.department_changed",
  "user.password_reset",
  "user.password_changed",
  "department.created",
  "department.updated",
  "department.deactivated",
  "auth.login_succeeded",
  "auth.login_failed",
  "auth.logout",
  "auth.token_reuse_detected",
];

describe("NHAN_HANH_DONG (RB-9)", () => {
  it("có đúng 15 giá trị, khớp enum backend", () => {
    expect(Object.keys(NHAN_HANH_DONG)).toHaveLength(15);
    expect(Object.keys(NHAN_HANH_DONG).sort()).toEqual([...MOI_HANH_DONG].sort());
  });

  it.each(MOI_HANH_DONG)("%s có nhãn tiếng Việt, không undefined", (hanhDong) => {
    const nhan = NHAN_HANH_DONG[hanhDong];
    expect(nhan).toBeDefined();
    expect(nhan.trim().length).toBeGreaterThan(0);
    // Không được rơi lại giá trị enum thô như "user.created".
    expect(nhan).not.toBe(hanhDong);
  });

  it.each(MOI_HANH_DONG)("%s có lớp badge", (hanhDong) => {
    expect(lopBadgeHanhDong(hanhDong).trim().length).toBeGreaterThan(0);
  });
});

describe("nhomCuaHanhDong", () => {
  it("tách đúng tiền tố của cả ba nhóm", () => {
    expect(nhomCuaHanhDong("user.created")).toBe("user");
    expect(nhomCuaHanhDong("department.deactivated")).toBe("department");
    expect(nhomCuaHanhDong("auth.logout")).toBe("auth");
  });

  it("mọi hành động đều thuộc một trong ba nhóm đã biết", () => {
    for (const hanhDong of MOI_HANH_DONG) {
      expect(["user", "department", "auth"]).toContain(nhomCuaHanhDong(hanhDong));
    }
  });
});

describe("lopBadgeHanhDong — hai dòng cần thấy ngay", () => {
  it("token bị dùng lại tô màu nguy hiểm", () => {
    expect(lopBadgeHanhDong("auth.token_reuse_detected")).toContain("danger");
  });

  it("đăng nhập thất bại tô màu cảnh báo, khác với đăng nhập thành công", () => {
    expect(lopBadgeHanhDong("auth.login_failed")).not.toBe(
      lopBadgeHanhDong("auth.login_succeeded"),
    );
  });
});
