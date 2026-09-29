import { describe, expect, it } from "vitest";
import { LOI_SAI_THONG_TIN, dieuKienMatKhau, thongDiepDangNhap } from "./xac-thuc";

describe("thongDiepDangNhap", () => {
  it("sai email và sai mật khẩu ra CÙNG một câu (không lộ tài khoản có tồn tại)", () => {
    expect(thongDiepDangNhap(401, "INVALID_CREDENTIALS", "Email hoặc mật khẩu không đúng.")).toBe(LOI_SAI_THONG_TIN);
    expect(thongDiepDangNhap(422, "VALIDATION_ERROR", "value is not a valid email")).toBe(LOI_SAI_THONG_TIN);
  });

  it("giữ thông điệp server cho 429 và tài khoản bị khoá", () => {
    expect(thongDiepDangNhap(429, "RATE_LIMIT_EXCEEDED", "Thử lại sau 60 giây.")).toBe("Thử lại sau 60 giây.");
    expect(thongDiepDangNhap(403, "INACTIVE_ACCOUNT", "Tài khoản đã bị vô hiệu hoá.")).toBe(
      "Tài khoản đã bị vô hiệu hoá.",
    );
  });

  it("lỗi mạng và lỗi máy chủ có câu riêng", () => {
    expect(thongDiepDangNhap(null)).toMatch(/kết nối/);
    expect(thongDiepDangNhap(502)).toMatch(/sự cố/);
  });
});

describe("dieuKienMatKhau — khớp kiem_tra_do_manh của backend", () => {
  const dat = (mk: string, lai = mk) => dieuKienMatKhau(mk, lai).map((d) => d.dat);

  it("tick dần theo từng điều kiện", () => {
    expect(dat("", "")).toEqual([false, false, false, false]);
    expect(dat("abc")).toEqual([false, true, false, true]);
    expect(dat("abc12345")).toEqual([true, true, true, true]);
    expect(dat("12345678")).toEqual([true, false, true, true]);
  });

  it("chữ có dấu tính là chữ cái (Python isalpha)", () => {
    expect(dat("đđđ11111")[1]).toBe(true);
  });

  it("đếm ký tự theo code point, không theo UTF-16", () => {
    expect(dat("😀😀😀a1234")[0]).toBe(true); // 8 ký tự
    expect(dat("😀😀a1234")[0]).toBe(false); // 7 ký tự
  });

  it("không khớp ô nhập lại", () => {
    expect(dat("abc12345", "abc1234")[3]).toBe(false);
  });
});
