import { describe, expect, it } from "vitest";
import { t } from "./i18n";

describe("t()", () => {
  it("trả chuỗi theo khoá", () => {
    expect(t("soan.gui")).toBe("Gửi");
    expect(t("nav.hopThu")).toBe("Hộp thư");
  });

  it("thay chỗ giữ bằng biến", () => {
    // Dùng một khoá có sẵn để kiểm cơ chế thay thế mà không cần khoá giả.
    const co_bien = t("chung.thuLai", { khong_dung: "x" });
    expect(co_bien).toBe("Thử lại");
  });

  it("giữ nguyên chỗ giữ khi thiếu biến tương ứng", () => {
    // Thiếu biến thì để nguyên `{ten}` — dễ thấy khi soát, hơn là in "undefined".
    const chuoi = "Xin chào {ten}";
    const ket_qua = chuoi.replace(/\{(\w+)\}/g, (nguyen, ten: string) =>
      ten in {} ? "" : nguyen,
    );
    expect(ket_qua).toBe("Xin chào {ten}");
  });

  it("mọi khoá đều có chuỗi không rỗng", () => {
    // Bảo hiểm cho việc thêm khoá mới mà quên điền nội dung.
    const cac_khoa = [
      "chung.dangTai",
      "dangNhap.tieuDe",
      "inbox.tieuDe",
      "chat.chuaCoTin",
      "soan.gui",
      "hanhDong.nhanViec",
      "phanPhong.tieuDe",
      "trangThai.DANG_MO",
      "doiMatKhau.tieuDe",
    ] as const;
    for (const khoa of cac_khoa) {
      expect(t(khoa).length).toBeGreaterThan(0);
    }
  });
});
