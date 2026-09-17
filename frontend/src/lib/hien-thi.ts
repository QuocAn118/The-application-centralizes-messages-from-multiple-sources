/**
 * Chuyển giá trị miền của backend sang chữ hiển thị cho người dùng.
 *
 * Tách khỏi component để nhãn không bị viết lại mỗi nơi một kiểu — giá trị enum
 * là của backend, còn cách gọi tên bằng tiếng Việt là quyết định của FE.
 */

import { t } from "./i18n";
import type {
  AnalysisOutcome,
  AuditAction,
  ConversationStatus,
  KpiMetricType,
  KpiSubjectType,
  Platform,
  RequestStatus,
  RequestType,
  Role,
} from "./types";

// Nhãn lấy từ từ điển i18n — một nguồn duy nhất, đổi ngôn ngữ là đổi cả đây.
export const NHAN_TRANG_THAI: Record<ConversationStatus, string> = {
  CHO_PHAN: t("trangThai.CHO_PHAN"),
  DANG_MO: t("trangThai.DANG_MO"),
  DA_DONG: t("trangThai.DA_DONG"),
};

export const NHAN_KENH: Record<Platform, string> = {
  ZALO: t("kenh.ZALO"),
  FACEBOOK: t("kenh.FACEBOOK"),
  INSTAGRAM: t("kenh.INSTAGRAM"),
  TELEGRAM: t("kenh.TELEGRAM"),
};

export const NHAN_VAI: Record<Role, string> = {
  STAFF: t("vai.STAFF"),
  MANAGER: t("vai.MANAGER"),
  ADMIN: t("vai.ADMIN"),
};

/** Lớp Tailwind cho badge kênh — màu lấy từ design system. */
export const LOP_BADGE_KENH: Record<Platform, string> = {
  ZALO: "bg-zalo-bg text-zalo-fg",
  FACEBOOK: "bg-facebook-bg text-facebook-fg",
  INSTAGRAM: "bg-instagram-bg text-instagram-fg",
  TELEGRAM: "bg-telegram-bg text-telegram-fg",
};

/** Lớp Tailwind cho badge trạng thái. */
export const LOP_BADGE_TRANG_THAI: Record<ConversationStatus, string> = {
  CHO_PHAN: "bg-cho-phan-bg text-cho-phan-fg",
  DANG_MO: "bg-dang-mo-bg text-dang-mo-fg",
  DA_DONG: "bg-da-dong-bg text-da-dong-fg",
};

/** Tên hiển thị của khách khi backend chưa có tên (kênh không trả về). */
export function tenKhach(ten: string | null): string {
  return ten?.trim() ? ten : t("inbox.khachChuaRoTen");
}

/** Chữ cái đầu cho avatar. */
export function chuCaiDau(ten: string | null): string {
  const daCat = tenKhach(ten).trim();
  return daCat[0]?.toUpperCase() ?? "?";
}

/** Giờ:phút 24h dạng "14:32" — ghép tay để không lệch theo bản ICU. */
function gioPhutNgan(t: Date): string {
  const gio = String(t.getHours()).padStart(2, "0");
  const phut = String(t.getMinutes()).padStart(2, "0");
  return `${gio}:${phut}`;
}

/**
 * Ngày/tháng dạng "04/08".
 *
 * Ghép tay thay vì dùng `Intl.DateTimeFormat`: dấu phân cách của locale `vi-VN`
 * khác nhau tuỳ bản ICU (có môi trường cho ra "04-08"), mà mockup chốt dấu gạch
 * chéo. Định dạng cố định thì hiển thị giống nhau ở mọi máy.
 */
function ngayThangNgan(t: Date): string {
  const ngay = String(t.getDate()).padStart(2, "0");
  const thang = String(t.getMonth() + 1).padStart(2, "0");
  return `${ngay}/${thang}`;
}

/**
 * Mốc thời gian ngắn cho dòng danh sách: hôm nay hiện giờ, hôm qua hiện chữ,
 * xa hơn hiện ngày/tháng (khớp mockup: "14:32", "Hôm qua", "04/08").
 */
export function mocNgan(isoString: string): string {
  const t = new Date(isoString);
  if (Number.isNaN(t.getTime())) return "";

  const bayGio = new Date();
  const dauHomNay = new Date(
    bayGio.getFullYear(),
    bayGio.getMonth(),
    bayGio.getDate(),
  );
  const dauHomQua = new Date(dauHomNay);
  dauHomQua.setDate(dauHomQua.getDate() - 1);

  if (t >= dauHomNay) return gioPhutNgan(t);
  if (t >= dauHomQua) return "Hôm qua";
  return ngayThangNgan(t);
}

/** Mốc đầy đủ dùng cho thuộc tính `title` (xem chi tiết khi rê chuột). */
export function mocDayDu(isoString: string): string {
  const t = new Date(isoString);
  if (Number.isNaN(t.getTime())) return "";
  return t.toLocaleString("vi-VN");
}

/**
 * Lớp Tailwind cho badge vai trò (#F2).
 *
 * "Quản trị" dùng tím để tách hẳn khỏi primary xanh — nhìn lướt bảng là thấy
 * ngay ai có toàn quyền.
 */
export const LOP_BADGE_VAI: Record<Role, string> = {
  ADMIN: "bg-admin-bg text-admin-fg",
  MANAGER: "bg-zalo-bg text-zalo-fg",
  STAFF: "bg-da-dong-bg text-da-dong-fg",
};

/**
 * Nhãn tiếng Việt cho 15 hành động nhật ký (#F2 GĐ4).
 *
 * RB-9: `Record<AuditAction, string>` bắt TypeScript đòi đủ 15 khoá — thiếu
 * một khoá là lỗi biên dịch, không phải `undefined` lặng lẽ hiện giữa bảng
 * (đúng cái đã xảy ra với `TELEGRAM`). Có thêm test duyệt toàn bộ enum ở
 * `hien-thi.test.ts` để phòng trường hợp ai đó bỏ chú thích kiểu hoặc ép kiểu.
 */
export const NHAN_HANH_DONG: Record<AuditAction, string> = {
  "user.created": t("hanhDong.user.created"),
  "user.updated": t("hanhDong.user.updated"),
  "user.deactivated": t("hanhDong.user.deactivated"),
  "user.reactivated": t("hanhDong.user.reactivated"),
  "user.role_changed": t("hanhDong.user.role_changed"),
  "user.department_changed": t("hanhDong.user.department_changed"),
  "user.password_reset": t("hanhDong.user.password_reset"),
  "user.password_changed": t("hanhDong.user.password_changed"),
  "department.created": t("hanhDong.department.created"),
  "department.updated": t("hanhDong.department.updated"),
  "department.deactivated": t("hanhDong.department.deactivated"),
  "auth.login_succeeded": t("hanhDong.auth.login_succeeded"),
  "auth.login_failed": t("hanhDong.auth.login_failed"),
  "auth.logout": t("hanhDong.auth.logout"),
  "auth.token_reuse_detected": t("hanhDong.auth.token_reuse_detected"),
};

/** Tiền tố nhóm của một hành động — dùng để tô màu và lọc. */
export type NhomHanhDong = "user" | "department" | "auth";

export function nhomCuaHanhDong(hanhDong: AuditAction): NhomHanhDong {
  // Backend đặt tên dạng `<đối tượng>.<hành động>` chính là để tách được thế này.
  return hanhDong.split(".")[0] as NhomHanhDong;
}

/**
 * Lớp Tailwind cho badge hành động.
 *
 * `auth.login_failed` và `auth.token_reuse_detected` tô màu cảnh báo: đó là hai
 * dòng người đọc nhật ký cần thấy ngay khi lướt qua.
 */
export function lopBadgeHanhDong(hanhDong: AuditAction): string {
  if (hanhDong === "auth.token_reuse_detected") {
    return "bg-danger-bg text-danger-fg";
  }
  if (hanhDong === "auth.login_failed") return "bg-cho-phan-bg text-cho-phan-fg";

  const nhom = nhomCuaHanhDong(hanhDong);
  if (nhom === "user") return "bg-zalo-bg text-zalo-fg";
  if (nhom === "department") return "bg-admin-bg text-admin-fg";
  return "bg-da-dong-bg text-da-dong-fg";
}

// ---------------------------------------------------------------------------
// Nhân sự (#F3)
// ---------------------------------------------------------------------------

/** Nhãn 3 loại đơn. RB-9: `Record` bắt TypeScript đòi đủ khoá. */
export const NHAN_LOAI_DON: Record<RequestType, string> = {
  NGHI_PHEP: t("loaiDon.NGHI_PHEP"),
  TANG_LUONG: t("loaiDon.TANG_LUONG"),
  KHAC: t("loaiDon.KHAC"),
};

/** Nhãn 4 trạng thái đơn. */
export const NHAN_TRANG_THAI_DON: Record<RequestStatus, string> = {
  CHO_DUYET: t("trangThaiDon.CHO_DUYET"),
  DA_DUYET: t("trangThaiDon.DA_DUYET"),
  TU_CHOI: t("trangThaiDon.TU_CHOI"),
  DA_HUY: t("trangThaiDon.DA_HUY"),
};

/**
 * Lớp badge trạng thái đơn.
 *
 * `DA_HUY` dùng màu xám như `TU_CHOI` nhưng KHÔNG cùng ý nghĩa: từ chối là
 * quyết định của người duyệt, thu hồi là người gửi tự rút. Nhãn chữ phân biệt
 * hai cái đó, màu chỉ nói "không còn chờ xử lý".
 */
export const LOP_BADGE_TRANG_THAI_DON: Record<RequestStatus, string> = {
  CHO_DUYET: "bg-cho-phan-bg text-cho-phan-fg",
  DA_DUYET: "bg-dang-mo-bg text-dang-mo-fg",
  TU_CHOI: "bg-danger-bg text-danger-fg",
  DA_HUY: "bg-da-dong-bg text-da-dong-fg",
};

/**
 * Giờ "HH:MM" từ chuỗi "HH:MM:SS" của backend.
 *
 * Cắt chuỗi chứ không qua `Date`: giá trị này là giờ trong ngày, không gắn với
 * ngày nào cả — đưa qua `Date` sẽ kéo theo múi giờ và làm lệch giờ hiển thị.
 */
export function gioNgan(gio: string): string {
  return gio.slice(0, 5);
}

/** Ngày "DD/MM/YYYY" từ chuỗi ISO "YYYY-MM-DD". Ghép tay, không qua `Date`. */
export function ngayVN(iso: string): string {
  const [nam, thang, ngay] = iso.slice(0, 10).split("-");
  return `${ngay}/${thang}/${nam}`;
}

/**
 * Bảy ngày của tuần chứa `moc`, dạng "YYYY-MM-DD", **bắt đầu từ thứ Hai**.
 *
 * `getDay()` trả 0 cho Chủ nhật, nên phải quy đổi: Chủ nhật lùi 6 ngày chứ
 * không phải tiến 1. Đây là chỗ lệch một ngày kinh điển của lịch tuần.
 *
 * Tính trên giờ ĐỊA PHƯƠNG rồi mới ghép chuỗi. Dùng `toISOString()` sẽ đổi sang
 * UTC và ở múi giờ dương (như VN, UTC+7) ngày sẽ lùi lại một hôm.
 */
export function tuanChua(moc: Date): string[] {
  const thu = moc.getDay();
  const lui = thu === 0 ? 6 : thu - 1;
  const thuHai = new Date(moc.getFullYear(), moc.getMonth(), moc.getDate() - lui);

  return Array.from({ length: 7 }, (_, i) => {
    const d = new Date(thuHai.getFullYear(), thuHai.getMonth(), thuHai.getDate() + i);
    const thang = String(d.getMonth() + 1).padStart(2, "0");
    const ngay = String(d.getDate()).padStart(2, "0");
    return `${d.getFullYear()}-${thang}-${ngay}`;
  });
}

/** Tên thứ ngắn cho tiêu đề cột lịch. Index 0 = thứ Hai. */
export const THU_NGAN = ["T2", "T3", "T4", "T5", "T6", "T7", "CN"] as const;

/**
 * Khung giờ ca có hợp lệ không (RB-4).
 *
 * Backend đòi **giờ kết thúc phải SAU giờ bắt đầu** — `shift.py` ghi rõ "ca
 * không qua nửa đêm ở #4", và trả 422 `INVALID_SHIFT_WINDOW` nếu vi phạm. Ban
 * đầu tôi tưởng ngược lại (vì #3 có xử lý ca bắc qua nửa đêm) và chỉ biết khi
 * gọi thật.
 *
 * So chuỗi "HH:MM" trực tiếp được vì định dạng có độ dài cố định và thứ tự từ
 * điển trùng thứ tự thời gian.
 */
export function khungGioHopLe(batDau: string, ketThuc: string): boolean {
  return ketThuc > batDau;
}


// ---------------------------------------------------------------------------
// KPI (#F3 GĐ3)
// ---------------------------------------------------------------------------

/** Nhãn 2 loại chỉ số. RB-9: `Record` bắt TypeScript đòi đủ khoá. */
export const NHAN_CHI_SO_KPI: Record<KpiMetricType, string> = {
  CONVERSATIONS_CLOSED: t("kpi.CONVERSATIONS_CLOSED"),
  AVG_RESPONSE_MINUTES: t("kpi.AVG_RESPONSE_MINUTES"),
};

/** Nhãn 2 loại đối tượng áp mục tiêu. */
export const NHAN_DOI_TUONG_KPI: Record<KpiSubjectType, string> = {
  USER: t("kpi.doiTuongUser"),
  DEPARTMENT: t("kpi.doiTuongPhong"),
};

/**
 * Đơn vị của từng chỉ số — hiện kèm giá trị thực đạt.
 *
 * Bắt buộc phải có: "30" một mình thì không biết là 30 hội thoại hay 30 phút,
 * mà hai cái ngược chiều nhau về ý nghĩa tốt/xấu (RB-8).
 */
export const DON_VI_KPI: Record<KpiMetricType, string> = {
  CONVERSATIONS_CLOSED: t("kpi.donViHoiThoai"),
  AVG_RESPONSE_MINUTES: t("kpi.donViPhut"),
};

/** Dấu gạch dùng cho mọi ô "chưa có số liệu". */
export const DAU_GACH = "—";

/**
 * Hiện một số đo của KPI (`target_value`, `actual_value`).
 *
 * **`null` và `0` là hai chuyện khác nhau** và đều xảy ra thật — đã đối chiếu
 * bằng lời gọi thật, hai chỉ số cho hai kết quả khác nhau trong cùng một kỳ:
 *
 * - `CONVERSATIONS_CLOSED` trả `"0"` — `_dem_hoi_thoai_dong` luôn trả về một số
 *   đếm, nên 0 nghĩa là **đã đo, và bằng không**.
 * - `AVG_RESPONSE_MINUTES` trả `null` — `_phut_phan_hoi_tb` trả `None` khi chưa
 *   có mẫu nào, nghĩa là **chưa đo được**.
 *
 * Gộp hai thứ này lại (ví dụ `Number(x) || 0`) là xoá mất sự khác biệt đó:
 * người quản lý sẽ đọc "chưa có dữ liệu" thành "nhân viên không làm gì".
 *
 * Backend trả `Decimal` dạng chuỗi ("55.00"), giữ nguyên chuỗi — chỉ cắt đuôi
 * ".00" cho dễ đọc, không đưa qua `Number` để khỏi sai số.
 */
export function soKpi(gia: string | null): string {
  if (gia === null) return DAU_GACH;
  return gia.includes(".") ? gia.replace(/\.?0+$/, "") : gia;
}

/**
 * Hiện phần trăm hoàn thành.
 *
 * `null` khi chưa có thực đạt **hoặc** khi mẫu số bằng 0 — cả hai đều là "không
 * tính được", hiện dấu gạch chứ không hiện "0%".
 */
export function phanTramKpi(phanTram: string | null): string {
  if (phanTram === null) return DAU_GACH;
  return `${soKpi(phanTram)}%`;
}

/**
 * Lớp màu theo mức hoàn thành.
 *
 * Tô thẳng theo `achievement_percent` mà KHÔNG xét chỉ số nào ngược chiều:
 * backend đã chuẩn hoá chiều (RB-8) — với `AVG_RESPONSE_MINUTES` nó tính
 * `target / actual`, nên **≥ 100% luôn là tốt** cho cả hai chỉ số. Thêm logic
 * đảo chiều ở đây là thừa và sẽ tô ngược.
 */
export function lopMucKpi(phanTram: string | null): string {
  if (phanTram === null) return "text-muted";
  const so = Number(phanTram);
  if (!Number.isFinite(so)) return "text-muted";
  if (so >= 100) return "text-dang-mo-fg";
  if (so >= 80) return "text-foreground";
  return "text-danger-fg";
}

/** Kỳ KPI dạng "Tháng 9/2026". */
export function kyKpi(nam: number, thang: number): string {
  return t("kpi.ky", { thang: String(thang), nam: String(nam) });
}


// ---------------------------------------------------------------------------
// Phân tích AI (#F4)
// ---------------------------------------------------------------------------

/** Nhãn 3 kết cục phân tích. RB-9: `Record` bắt TypeScript đòi đủ khoá. */
export const NHAN_KET_QUA_PHAN_TICH: Record<AnalysisOutcome, string> = {
  AUTO_ASSIGNED: t("phanTich.AUTO_ASSIGNED"),
  AMBIGUOUS: t("phanTich.AMBIGUOUS"),
  NOT_ANALYZED: t("phanTich.NOT_ANALYZED"),
};

/**
 * Lớp badge theo kết cục.
 *
 * `AUTO_ASSIGNED` là kết quả tốt (xanh); `AMBIGUOUS` là "cần người xem lại"
 * (vàng); `NOT_ANALYZED` là hỏng/chưa chạy (xám — KHÔNG đỏ: không phân tích
 * được thường là chưa đủ tin nhắn, không phải lỗi).
 */
export const LOP_BADGE_KET_QUA_PHAN_TICH: Record<AnalysisOutcome, string> = {
  AUTO_ASSIGNED: "bg-dang-mo-bg text-dang-mo-fg",
  AMBIGUOUS: "bg-cho-phan-bg text-cho-phan-fg",
  NOT_ANALYZED: "bg-da-dong-bg text-da-dong-fg",
};

/**
 * Độ tin cậy `Decimal` 0..1 (chuỗi "0.950") thành phần trăm để đọc.
 *
 * `null` nghĩa là **không có** độ tin cậy (`NOT_ANALYZED`), không phải 0% —
 * hiện dấu gạch. Cùng bài học với `phanTramKpi` của #F3: "0%" nói rằng đã đo và
 * kết quả bằng không, sai hẳn nghĩa.
 */
export function doTinCay(giaTri: string | null): string {
  if (giaTri === null) return DAU_GACH;
  const so = Number(giaTri);
  if (!Number.isFinite(so)) return DAU_GACH;
  return `${Math.round(so * 100)}%`;
}


// ---------------------------------------------------------------------------
// Báo cáo (#F5)
// ---------------------------------------------------------------------------

/** Số nguyên có dấu phân nhóm hàng nghìn (1234 → "1.234"). */
const DINH_DANG_SO = new Intl.NumberFormat("vi-VN");

export function soDem(n: number): string {
  return DINH_DANG_SO.format(n);
}

/**
 * Thời lượng từ **giây** sang chữ đọc: "45 giây", "12 phút", "2 giờ 5 phút".
 *
 * `null` = **chưa có mẫu** (chưa phản hồi/đóng/quyết đơn nào) → dấu gạch. Đây là
 * cùng bẫy null-vs-0 của KPI: báo cáo agents đo được `avg_first_response_seconds`
 * là `null` NGAY CẢ khi `handled_count > 0`. "0 giây" nghĩa là tức thì, khác hẳn
 * "chưa đo được" — không được suy null → 0.
 *
 * Làm tròn tới phút khi ≥ 60 giây (báo cáo không cần độ chính xác tới giây cho
 * khoảng nhiều ngày); dưới 60 giây giữ nguyên giây cho khỏi ra "0 phút".
 */
export function khoangThoiGian(giay: number | null): string {
  if (giay === null) return DAU_GACH;
  const s = Math.round(giay);
  if (s < 60) return `${s} giây`;
  const tongPhut = Math.round(s / 60);
  const gio = Math.floor(tongPhut / 60);
  const phut = tongPhut % 60;
  if (gio === 0) return `${phut} phút`;
  if (phut === 0) return `${gio} giờ`;
  return `${gio} giờ ${phut} phút`;
}

/**
 * Phần trăm KPI của báo cáo (số, không phải chuỗi như #F3).
 *
 * Ba hình dạng đo thật đi kèm nhau: `null` = chưa đặt target → dấu gạch;
 * `0` = đã đo, hoàn thành 0% → **"0%"** (KHÁC dấu gạch); `>0` → phần trăm. Suy
 * `null → 0` là biến "chưa có mục tiêu" thành "trượt hoàn toàn".
 */
export function phanTramKpiSo(phanTram: number | null): string {
  if (phanTram === null) return DAU_GACH;
  return `${Math.round(phanTram)}%`;
}

/**
 * Mã rút gọn từ UUID (8 ký tự đầu, "#a1b2c3d4") — dùng khi KHÔNG tra được tên.
 *
 * Vì sao cần: báo cáo trả UUID trần. Với Manager, `/users` chỉ trả người trong
 * phòng mình và `/users/{id}` người ngoài phòng trả **403**; báo cáo agents lại
 * chứa cả user `department_id=null` (Admin đã xử lý hội thoại) mà không map nào
 * của Manager có. Thay vì ô trắng / "undefined" / một lời gọi chắc chắn 403, hiện
 * mã này để người đọc vẫn phân biệt được các dòng.
 */
export function maRutGon(id: string): string {
  return `#${id.slice(0, 8)}`;
}

/** Tên người từ map đã tải; thiếu id → mã rút gọn (xem `maRutGon`). */
export function tenNguoi(ten: Map<string, string>, id: string): string {
  return ten.get(id) ?? maRutGon(id);
}

/**
 * Tên phòng từ map; `null` = **chưa phân phòng** (hội thoại `CHO_PHAN` — xuất
 * hiện thật trong báo cáo hội thoại); id lạ → mã rút gọn.
 */
export function tenPhong(ten: Map<string, string>, id: string | null): string {
  if (id === null) return t("baoCao.chuaPhanPhong");
  return ten.get(id) ?? maRutGon(id);
}
