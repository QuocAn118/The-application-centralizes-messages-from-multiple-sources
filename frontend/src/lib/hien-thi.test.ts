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
  LOP_BADGE_TRANG_THAI_DON,
  NHAN_HANH_DONG,
  NHAN_KENH,
  DAU_GACH,
  DON_VI_KPI,
  LOP_BADGE_KET_QUA_PHAN_TICH,
  NHAN_KET_QUA_PHAN_TICH,
  doTinCay,
  NHAN_CHI_SO_KPI,
  NHAN_DOI_TUONG_KPI,
  NHAN_LOAI_DON,
  lopMucKpi,
  phanTramKpi,
  soKpi,
  NHAN_TRANG_THAI_DON,
  NHAN_VAI,
  chuCaiDau,
  lopBadgeHanhDong,
  gioNgan,
  mocNgan,
  ngayVN,
  nhomCuaHanhDong,
  khungGioHopLe,
  tenKhach,
  tuanChua,
  khoangThoiGian,
  phanTramKpiSo,
  maRutGon,
  tenNguoi,
  tenPhong,
  soDem,
} from "./hien-thi";
import type {
  AnalysisOutcome,
  AuditAction,
  KpiMetricType,
  KpiSubjectType,
  Platform,
  RequestStatus,
  RequestType,
  Role,
} from "./types";

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

/**
 * RB-9 cho #F3 — hai enum đơn từ.
 *
 * Danh sách liệt kê tay, chép từ `hrm/domain/value_objects/request_kind.py`.
 * Không đọc ngược từ chính bảng đang kiểm: làm thế thì bảng thiếu khoá nào test
 * cũng không biết.
 */
const MOI_LOAI_DON: RequestType[] = ["NGHI_PHEP", "TANG_LUONG", "KHAC"];
const MOI_TRANG_THAI_DON: RequestStatus[] = [
  "CHO_DUYET",
  "DA_DUYET",
  "TU_CHOI",
  "DA_HUY",
];

describe("NHAN_LOAI_DON (RB-9)", () => {
  it("có đúng 3 giá trị, khớp enum backend", () => {
    expect(Object.keys(NHAN_LOAI_DON).sort()).toEqual([...MOI_LOAI_DON].sort());
  });

  it.each(MOI_LOAI_DON)("%s có nhãn tiếng Việt", (loai) => {
    expect(NHAN_LOAI_DON[loai]?.trim().length).toBeGreaterThan(0);
    expect(NHAN_LOAI_DON[loai]).not.toBe(loai);
  });
});

describe("NHAN_TRANG_THAI_DON (RB-9)", () => {
  it("có đúng 4 giá trị, khớp enum backend", () => {
    expect(Object.keys(NHAN_TRANG_THAI_DON).sort()).toEqual(
      [...MOI_TRANG_THAI_DON].sort(),
    );
  });

  it.each(MOI_TRANG_THAI_DON)("%s có nhãn và lớp badge", (tt) => {
    expect(NHAN_TRANG_THAI_DON[tt]?.trim().length).toBeGreaterThan(0);
    expect(LOP_BADGE_TRANG_THAI_DON[tt]?.trim().length).toBeGreaterThan(0);
  });

  it("TU_CHOI và DA_HUY có NHÃN khác nhau dù đều là kết thúc", () => {
    // Từ chối là quyết định của người duyệt; thu hồi là người gửi tự rút. Gộp
    // nhãn sẽ giấu mất khác biệt đó.
    expect(NHAN_TRANG_THAI_DON.TU_CHOI).not.toBe(NHAN_TRANG_THAI_DON.DA_HUY);
  });
});

describe("gioNgan / ngayVN", () => {
  it("cắt giây khỏi giờ backend trả về", () => {
    expect(gioNgan("22:00:00")).toBe("22:00");
    expect(gioNgan("06:30:00")).toBe("06:30");
  });

  it("đổi ngày ISO sang DD/MM/YYYY", () => {
    expect(ngayVN("2026-09-20")).toBe("20/09/2026");
  });

  it("không đi qua Date nên không lệch múi giờ", () => {
    // Nếu dùng `new Date("2026-01-01")` rồi lấy ngày địa phương, ở múi giờ âm
    // sẽ ra 31/12/2025. Ghép chuỗi thì không bao giờ lệch.
    expect(ngayVN("2026-01-01")).toBe("01/01/2026");
    expect(ngayVN("2026-12-31T17:00:00Z")).toBe("31/12/2026");
  });
});

describe("tuanChua", () => {
  it("bắt đầu từ thứ Hai", () => {
    // 16/09/2026 là thứ Tư.
    const tuan = tuanChua(new Date(2026, 8, 16));
    expect(tuan).toHaveLength(7);
    expect(tuan[0]).toBe("2026-09-14");
    expect(tuan[6]).toBe("2026-09-20");
  });

  it("CHỦ NHẬT thuộc về tuần TRƯỚC, không phải tuần sau", () => {
    // Bẫy kinh điển: getDay() trả 0 cho Chủ nhật, cộng 1 sẽ nhảy sang tuần sau.
    // 20/09/2026 là Chủ nhật — phải nằm cuối tuần 14–20.
    const tuan = tuanChua(new Date(2026, 8, 20));
    expect(tuan[0]).toBe("2026-09-14");
    expect(tuan[6]).toBe("2026-09-20");
  });

  it("thứ Hai cho ra chính nó ở vị trí đầu", () => {
    const tuan = tuanChua(new Date(2026, 8, 14));
    expect(tuan[0]).toBe("2026-09-14");
  });

  it("bắc qua ranh giới tháng", () => {
    // 01/10/2026 là thứ Năm -> tuần bắt đầu 28/09.
    const tuan = tuanChua(new Date(2026, 9, 1));
    expect(tuan[0]).toBe("2026-09-28");
    expect(tuan[6]).toBe("2026-10-04");
  });

  it("bắc qua ranh giới năm", () => {
    // 01/01/2027 là thứ Sáu -> tuần bắt đầu 28/12/2026.
    const tuan = tuanChua(new Date(2027, 0, 1));
    expect(tuan[0]).toBe("2026-12-28");
    expect(tuan[6]).toBe("2027-01-03");
  });

  it("không lệch ngày do múi giờ", () => {
    // Nếu dùng toISOString() thì ở UTC+7 ngày 14/09 lúc 00:00 địa phương sẽ
    // thành "2026-09-13" — sai một ngày cho cả lịch.
    const tuan = tuanChua(new Date(2026, 8, 14, 0, 0, 0));
    expect(tuan[0]).toBe("2026-09-14");
  });
});

describe("khungGioHopLe (RB-4)", () => {
  // Backend đòi giờ kết thúc SAU giờ bắt đầu: `shift.py` ghi "ca không qua nửa
  // đêm ở #4" và trả 422 INVALID_SHIFT_WINDOW. Bản spec đầu của tôi ghi ngược
  // — chỉ phát hiện khi gọi API thật.
  it("ca 08:00–17:00 hợp lệ", () => {
    expect(khungGioHopLe("08:00", "17:00")).toBe(true);
  });

  it("ca 22:00–06:00 KHÔNG hợp lệ (qua đêm, backend từ chối)", () => {
    expect(khungGioHopLe("22:00", "06:00")).toBe(false);
  });

  it("giờ đầu bằng giờ cuối cũng không hợp lệ", () => {
    expect(khungGioHopLe("08:00", "08:00")).toBe(false);
  });

  it("so được cả chuỗi có giây", () => {
    expect(khungGioHopLe("08:00:00", "17:00:00")).toBe(true);
  });
});


/**
 * RB-9 cho KPI — hai enum còn lại của #F3.
 *
 * Liệt kê tay, KHÔNG đọc ngược từ chính bảng đang kiểm: đọc ngược thì bảng
 * thiếu khoá nào test cũng thiếu khoá đó và luôn xanh.
 */
const MOI_CHI_SO: KpiMetricType[] = ["CONVERSATIONS_CLOSED", "AVG_RESPONSE_MINUTES"];
const MOI_DOI_TUONG: KpiSubjectType[] = ["USER", "DEPARTMENT"];

describe("NHAN_CHI_SO_KPI / DON_VI_KPI (RB-9)", () => {
  it("phủ đủ mọi chỉ số, không thừa không thiếu", () => {
    expect(Object.keys(NHAN_CHI_SO_KPI).sort()).toEqual([...MOI_CHI_SO].sort());
    expect(Object.keys(DON_VI_KPI).sort()).toEqual([...MOI_CHI_SO].sort());
  });

  it.each(MOI_CHI_SO)("%s có nhãn tiếng Việt và đơn vị", (chiSo) => {
    expect(NHAN_CHI_SO_KPI[chiSo]?.trim().length).toBeGreaterThan(0);
    expect(NHAN_CHI_SO_KPI[chiSo]).not.toBe(chiSo);
    expect(DON_VI_KPI[chiSo]?.trim().length).toBeGreaterThan(0);
  });

  it("hai chỉ số có đơn vị KHÁC nhau", () => {
    // "30" một mình không phân biệt được 30 hội thoại với 30 phút, mà hai thứ
    // ngược chiều nhau về tốt/xấu.
    expect(DON_VI_KPI.CONVERSATIONS_CLOSED).not.toBe(DON_VI_KPI.AVG_RESPONSE_MINUTES);
  });
});

describe("NHAN_DOI_TUONG_KPI (RB-9)", () => {
  it("phủ đủ mọi loại đối tượng", () => {
    expect(Object.keys(NHAN_DOI_TUONG_KPI).sort()).toEqual([...MOI_DOI_TUONG].sort());
  });

  it.each(MOI_DOI_TUONG)("%s có nhãn tiếng Việt", (loai) => {
    expect(NHAN_DOI_TUONG_KPI[loai]?.trim().length).toBeGreaterThan(0);
    expect(NHAN_DOI_TUONG_KPI[loai]).not.toBe(loai);
  });
});

/**
 * RB-3 — `null` (chưa đo được) và `0` (đã đo, bằng không) KHÔNG được gộp.
 *
 * Cả hai đều xảy ra thật, trong cùng một kỳ, tuỳ chỉ số — đã đối chiếu bằng lời
 * gọi thật lên server đang chạy:
 * - `CONVERSATIONS_CLOSED` trả `actual_value: "0"`, `achievement_percent: "0.0"`
 * - `AVG_RESPONSE_MINUTES` trả cả hai bằng `null`
 *
 * Gộp chúng lại là biến "chưa có dữ liệu" thành "nhân viên không làm gì".
 */
describe("soKpi — phân biệt null với 0", () => {
  it("null hiện dấu gạch", () => {
    expect(soKpi(null)).toBe(DAU_GACH);
  });

  it('"0" hiện SỐ KHÔNG, không phải dấu gạch', () => {
    expect(soKpi("0")).toBe("0");
    expect(soKpi("0.0")).toBe("0");
  });

  it("cắt đuôi thập phân thừa của Decimal", () => {
    expect(soKpi("55.00")).toBe("55");
    expect(soKpi("15.00")).toBe("15");
  });

  it("giữ phần thập phân có nghĩa", () => {
    expect(soKpi("10.50")).toBe("10.5");
    expect(soKpi("20.05")).toBe("20.05");
  });

  it("KHÔNG cắt nhầm số 0 ở cuối phần nguyên", () => {
    // Bẫy: "1000".replace(/\.?0+$/, "") ra "1" nếu quên chặn chuỗi không có
    // dấu chấm.
    expect(soKpi("1000")).toBe("1000");
    expect(soKpi("100")).toBe("100");
    expect(soKpi("100.00")).toBe("100");
  });
});

describe("phanTramKpi", () => {
  it("null hiện dấu gạch, KHÔNG hiện 0%", () => {
    expect(phanTramKpi(null)).toBe(DAU_GACH);
    expect(phanTramKpi(null)).not.toContain("0");
  });

  it('"0.0" hiện "0%" — đã đo và bằng không', () => {
    expect(phanTramKpi("0.0")).toBe("0%");
  });

  it("phần trăm thường", () => {
    expect(phanTramKpi("120.5")).toBe("120.5%");
    expect(phanTramKpi("100.0")).toBe("100%");
  });
});

/**
 * RB-8 — backend ĐÃ chuẩn hoá chiều, nên ≥ 100% là tốt cho CẢ HAI chỉ số.
 * `lopMucKpi` cố ý không nhận `metric_type`: thêm logic đảo chiều ở FE sẽ tô
 * ngược màu cho `AVG_RESPONSE_MINUTES`.
 */
describe("lopMucKpi (RB-8)", () => {
  it("null thì xám, không tô tốt cũng không tô xấu", () => {
    expect(lopMucKpi(null)).toBe("text-muted");
  });

  it("đạt và vượt mục tiêu thì tô tốt", () => {
    expect(lopMucKpi("100.0")).toBe("text-dang-mo-fg");
    expect(lopMucKpi("250.0")).toBe("text-dang-mo-fg");
  });

  it("dưới 80% thì tô cảnh báo", () => {
    expect(lopMucKpi("0.0")).toBe("text-danger-fg");
    expect(lopMucKpi("79.9")).toBe("text-danger-fg");
  });

  it("chuỗi không phải số thì xám, không vỡ", () => {
    expect(lopMucKpi("khong-phai-so")).toBe("text-muted");
  });
});


/**
 * RB-9 cho #F4 — enum `AnalysisOutcome`.
 *
 * Liệt kê tay cả ba, KHÔNG đọc ngược từ chính bảng đang kiểm.
 */
const MOI_KET_QUA: AnalysisOutcome[] = ["AUTO_ASSIGNED", "AMBIGUOUS", "NOT_ANALYZED"];

describe("NHAN_KET_QUA_PHAN_TICH / LOP_BADGE_KET_QUA_PHAN_TICH (RB-9)", () => {
  it("phủ đủ ba kết cục, không thừa không thiếu", () => {
    expect(Object.keys(NHAN_KET_QUA_PHAN_TICH).sort()).toEqual([...MOI_KET_QUA].sort());
    expect(Object.keys(LOP_BADGE_KET_QUA_PHAN_TICH).sort()).toEqual([...MOI_KET_QUA].sort());
  });

  it.each(MOI_KET_QUA)("%s có nhãn tiếng Việt và lớp badge", (kq) => {
    expect(NHAN_KET_QUA_PHAN_TICH[kq]?.trim().length).toBeGreaterThan(0);
    expect(NHAN_KET_QUA_PHAN_TICH[kq]).not.toBe(kq);
    expect(LOP_BADGE_KET_QUA_PHAN_TICH[kq]?.trim().length).toBeGreaterThan(0);
  });

  it("ba kết cục có ba nhãn KHÁC nhau", () => {
    // Trùng nhãn thì người đọc không phân biệt được "đã tự phân" với "không
    // phân tích được" — hai tình huống cần hành động khác hẳn nhau.
    expect(new Set(MOI_KET_QUA.map((k) => NHAN_KET_QUA_PHAN_TICH[k])).size).toBe(3);
  });
});

/**
 * RB-8 — `confidence` `null` là "không có độ tin cậy" (NOT_ANALYZED), KHÔNG
 * phải 0%. Cùng bài học với `phanTramKpi` của #F3.
 */
describe("doTinCay", () => {
  it("null hiện dấu gạch, KHÔNG hiện 0%", () => {
    expect(doTinCay(null)).toBe(DAU_GACH);
    expect(doTinCay(null)).not.toContain("0");
  });

  it("chuỗi Decimal thành phần trăm", () => {
    expect(doTinCay("0.950")).toBe("95%");
    expect(doTinCay("1.000")).toBe("100%");
    expect(doTinCay("0.310")).toBe("31%");
  });

  it('"0.000" hiện "0%" — có đo, và bằng không', () => {
    // Khác hẳn null: LLM có trả độ tin cậy, chỉ là bằng 0.
    expect(doTinCay("0.000")).toBe("0%");
  });

  it("chuỗi không phải số thì dấu gạch, không vỡ", () => {
    expect(doTinCay("khong-phai-so")).toBe(DAU_GACH);
  });
});

// ---------------------------------------------------------------------------
// Báo cáo (#F5)
// ---------------------------------------------------------------------------

describe("khoangThoiGian", () => {
  it("null hiện dấu gạch — chưa có mẫu, KHÔNG phải 0 giây", () => {
    // Bẫy đo thật: avg_first_response_seconds=null đi cùng handled_count>0.
    expect(khoangThoiGian(null)).toBe(DAU_GACH);
    expect(khoangThoiGian(null)).not.toContain("0");
  });

  it("0 giây là 'phản hồi tức thì', khác hẳn null", () => {
    expect(khoangThoiGian(0)).toBe("0 giây");
  });

  it("dưới 60 giây giữ giây; từ 60 lên đổi phút/giờ", () => {
    expect(khoangThoiGian(45)).toBe("45 giây");
    expect(khoangThoiGian(178)).toBe("3 phút"); // avg_first_response thật
    expect(khoangThoiGian(3600)).toBe("1 giờ");
    expect(khoangThoiGian(187858.5)).toBe("52 giờ 11 phút"); // avg_resolution thật
  });
});

describe("phanTramKpiSo", () => {
  it("null hiện dấu gạch — chưa đặt target, KHÔNG là trượt 0%", () => {
    expect(phanTramKpiSo(null)).toBe(DAU_GACH);
  });

  it("0 hiện '0%' — đã đo, hoàn thành 0% (khác null)", () => {
    // Đo thật: staffA có kpi_percent=0.0, period="2026-09".
    expect(phanTramKpiSo(0)).toBe("0%");
  });

  it("phần trăm dương làm tròn", () => {
    expect(phanTramKpiSo(84.6)).toBe("85%");
    expect(phanTramKpiSo(100)).toBe("100%");
  });
});

describe("tenNguoi / tenPhong / maRutGon", () => {
  const ten = new Map([["019fd148-249d-7a53-8ed4-24b7723d94fd", "Nguyễn Hoài An"]]);

  it("id có trong map thì trả tên", () => {
    expect(tenNguoi(ten, "019fd148-249d-7a53-8ed4-24b7723d94fd")).toBe("Nguyễn Hoài An");
  });

  it("id KHÔNG có trong map thì mã rút gọn, không undefined", () => {
    // Manager không tra được người ngoài phòng / Admin dept=null.
    expect(tenNguoi(ten, "019fd148-21d7-71e1-9142-e63b9b86e67e")).toBe("#019fd148");
    expect(tenNguoi(ten, "019fd148-21d7-71e1-9142-e63b9b86e67e")).not.toContain("undefined");
  });

  it("tenPhong: null là 'Chưa phân phòng' (CHO_PHAN), không ô trắng", () => {
    expect(tenPhong(ten, null)).toBe("Chưa phân phòng");
  });

  it("maRutGon lấy 8 ký tự đầu", () => {
    expect(maRutGon("019fd148-1ffd-7b42-9185-de81d06af387")).toBe("#019fd148");
  });
});

describe("soDem", () => {
  it("phân nhóm hàng nghìn kiểu vi-VN", () => {
    expect(soDem(1234)).toBe("1.234");
    expect(soDem(0)).toBe("0");
  });
});
