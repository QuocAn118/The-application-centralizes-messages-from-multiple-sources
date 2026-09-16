/**
 * RB-4 — thông điệp lỗi nghiệp vụ phải là CÂU CỦA SERVER, không phải bản dịch
 * lại ở FE (#F2 task 1.8).
 *
 * Test này khoá đúng quyết định đó: nếu ai sau này thêm một bảng tra mã lỗi ở
 * FE, các khẳng định dưới sẽ đỏ.
 */

import { describe, expect, it } from "vitest";
import { ApiError, SessionExpiredError } from "./api-client";
import { thongDiepLoi } from "./loi-quan-tri";
import { t } from "./i18n";

/** Bảy quy tắc nghiệp vụ backend trả kèm thông điệp tiếng Việt đầy đủ. */
const QUY_TAC_NGHIEP_VU: [string, string][] = [
  ["DEPARTMENT_ALREADY_HAS_MANAGER", "Phòng ban này đã có quản lý."],
  ["LAST_ADMIN_CANNOT_BE_DEACTIVATED", "Không thể vô hiệu hoá quản trị viên cuối cùng."],
  ["DEPARTMENT_REQUIRED", "Nhân viên và quản lý phải thuộc một phòng ban."],
  ["ADMIN_CANNOT_HAVE_DEPARTMENT", "Quản trị viên không thuộc phòng ban nào."],
  ["INACTIVE_DEPARTMENT", "Phòng ban đã ngừng hoạt động."],
  ["CANNOT_CHANGE_TO_ADMIN", "Chỉ đổi qua lại giữa nhân viên và quản lý."],
  ["DEPARTMENT_HAS_ACTIVE_MEMBERS", "Phòng ban còn nhân viên đang hoạt động."],
];

describe("thongDiepLoi", () => {
  it.each(QUY_TAC_NGHIEP_VU)(
    "%s — hiện THẲNG câu của server, không dịch lại",
    (code, message) => {
      const loi = new ApiError(422, code, message);
      expect(thongDiepLoi(loi)).toBe(message);
    },
  );

  it("403 dùng câu của FE vì server cố ý trả lời mơ hồ", () => {
    const loi = new ApiError(403, "FORBIDDEN", "Forbidden");
    expect(thongDiepLoi(loi)).toBe(t("loiQuanTri.khongDuQuyen"));
  });

  it("404 cũng coi là không đủ quyền — server giấu sự tồn tại của tài nguyên", () => {
    const loi = new ApiError(404, "NOT_FOUND", "Not found");
    expect(thongDiepLoi(loi)).toBe(t("loiQuanTri.khongDuQuyen"));
  });

  it("ApiError không có message thì rơi về câu chung, không hiện chuỗi rỗng", () => {
    const loi = new ApiError(500, "INTERNAL", "   ");
    expect(thongDiepLoi(loi)).toBe(t("loiQuanTri.chung"));
  });

  it("hết phiên giữ nguyên câu của SessionExpiredError", () => {
    const loi = new SessionExpiredError();
    expect(thongDiepLoi(loi)).toBe(loi.message);
  });

  it("lỗi mạng (TypeError của fetch) dùng câu chung", () => {
    expect(thongDiepLoi(new TypeError("Failed to fetch"))).toBe(t("loiQuanTri.chung"));
  });

  it("thứ không phải Error cũng không làm vỡ UI", () => {
    expect(thongDiepLoi(null)).toBe(t("loiQuanTri.chung"));
    expect(thongDiepLoi("chuỗi lạ")).toBe(t("loiQuanTri.chung"));
  });
});
