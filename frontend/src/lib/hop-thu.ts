/**
 * Hàm thuần của Hộp thư (redesign 2a): mốc giờ, thời gian chờ, gộp trang,
 * dựng dòng khung chat. Không đụng React/DOM để
 * test được bằng vitest `node`.
 *
 * Mốc giờ ghép tay thay vì `Intl.RelativeTimeFormat`: bản `vi` của Intl trả
 * "2 phút trước" / dấu phân cách ngày tuỳ bản ICU — spec cần "2 phút", "15/09"
 * giống nhau ở mọi máy (cùng lý do với `mocNgan` ở hien-thi.ts).
 */

import type { ConversationEvent, InboxItem, Message } from "./types";

/** Khách chờ từ ngần này phút trở lên thì đổi sang tông cảnh báo (GĐ1 I13). */
export const NGUONG_CHO_PHUT = 15;

/** Tin liên tiếp cùng người gửi cách nhau không quá ngần này thì gom một nhóm. */
const GOM_NHOM_MS = 5 * 60_000;

const PHUT_MS = 60_000;
const THU_NGAN = ["CN", "Th 2", "Th 3", "Th 4", "Th 5", "Th 6", "Th 7"];
const THU_DAY_DU = ["Chủ nhật", "Thứ Hai", "Thứ Ba", "Thứ Tư", "Thứ Năm", "Thứ Sáu", "Thứ Bảy"];

const hai = (n: number) => String(n).padStart(2, "0");
const dauNgay = (d: Date) => new Date(d.getFullYear(), d.getMonth(), d.getDate());

/** Số ngày lịch giữa hai mốc (0 = cùng ngày), theo giờ máy người xem. */
function soNgayLich(tu: Date, den: Date): number {
  return Math.round((dauNgay(den).getTime() - dauNgay(tu).getTime()) / 86_400_000);
}

/**
 * Mốc ngắn cho dòng danh sách: "Vừa xong" · "12 phút" · "14:32" (hôm nay) ·
 * "Hôm qua" · "Th 2" (trong tuần) · "15/09".
 */
export function mocTuongDoi(iso: string, now: Date): string {
  const t = new Date(iso);
  if (Number.isNaN(t.getTime())) return "";
  const phut = Math.floor((now.getTime() - t.getTime()) / PHUT_MS);
  if (phut < 1) return "Vừa xong";
  if (phut < 60) return `${phut} phút`;
  const ngay = soNgayLich(t, now);
  if (ngay <= 0) return `${hai(t.getHours())}:${hai(t.getMinutes())}`;
  if (ngay === 1) return "Hôm qua";
  if (ngay < 7) return THU_NGAN[t.getDay()];
  return `${hai(t.getDate())}/${hai(t.getMonth() + 1)}`;
}

/** "14:32" theo giờ máy — cho giờ tin / dòng hệ thống (ngày đã có ở vạch ngày). */
export function gioPhut(iso: string): string {
  const d = new Date(iso);
  return `${hai(d.getHours())}:${hai(d.getMinutes())}`;
}

/** Số phút khách đã chờ; `null` khi không ai chờ. Không bao giờ âm (lệch đồng hồ). */
export function phutCho(waitingSince: string | null, now: Date): number | null {
  if (!waitingSince) return null;
  const t = new Date(waitingSince).getTime();
  if (Number.isNaN(t)) return null;
  return Math.max(0, Math.floor((now.getTime() - t) / PHUT_MS));
}

export function laChoLau(phut: number | null): boolean {
  return phut !== null && phut >= NGUONG_CHO_PHUT;
}

/** "Chờ 12 phút" / "Chờ 2 giờ" / "Chờ 3 ngày". */
export function nhanCho(phut: number): string {
  if (phut < 60) return `Chờ ${phut} phút`;
  if (phut < 24 * 60) return `Chờ ${Math.floor(phut / 60)} giờ`;
  return `Chờ ${Math.floor(phut / (24 * 60))} ngày`;
}

/**
 * Gộp các trang của cuộn liên tục, loại trùng theo `conversation_id` (giữ lần
 * xuất hiện ĐẦU). Tin mới đẩy một hội thoại lên đầu giữa hai lần tải thì nó có
 * mặt ở cả trang 1 mới lẫn trang 2 cũ — không loại thì thành hai dòng.
 */
export function gopTrang(trang: InboxItem[][]): InboxItem[] {
  const daCo = new Set<string>();
  const ra: InboxItem[] = [];
  for (const muc of trang.flat()) {
    if (daCo.has(muc.conversation_id)) continue;
    daCo.add(muc.conversation_id);
    ra.push(muc);
  }
  return ra;
}

/** Số trên huy hiệu chưa đọc; "" = không hiện. */
export function hienSoChuaDoc(n: number): string {
  if (n <= 0) return "";
  return n > 99 ? "99+" : String(n);
}

/**
 * Tiêu đề tab Hộp thư kèm số chưa đọc: "(5) Hộp thư · OmniChat". Bỏ tiền tố cũ
 * trước khi gắn mới → gọi lại nhiều lần không thành "(5) (4) …"; 0 thì bỏ hẳn.
 */
export function tieuDeCoSoChuaDoc(tieuDe: string, soHoiThoai: number): string {
  const goc = tieuDe.replace(/^\(\d+\+?\) /, "");
  const so = hienSoChuaDoc(soHoiThoai);
  return so ? `(${so}) ${goc}` : goc;
}

const ten = (s: string | null) => s?.trim() || "—";

/** Câu của một dòng hệ thống (spec 2a §3.4). */
export function noiDungSuKien(e: ConversationEvent): string {
  switch (e.kind) {
    case "TAKEN":
      return `${ten(e.to_name)} đã nhận việc`;
    case "AUTO_ASSIGNED":
      return `Hệ thống tự giao cho ${ten(e.to_name)}`;
    case "ASSIGNED":
      return `${ten(e.actor_name)} giao cho ${ten(e.to_name)}`;
    case "REASSIGNED":
      return `Chuyển từ ${ten(e.from_name)} sang ${ten(e.to_name)}`;
    case "UNASSIGNED":
      return `Gỡ người phụ trách ${ten(e.from_name)}`;
    case "DEPARTMENT_ASSIGNED":
      return `${ten(e.actor_name)} phân về ${ten(e.department_name ?? null)}`;
    case "AUTO_ROUTED":
      return `Tự động chuyển tới ${ten(e.department_name ?? null)}${e.detail ? ` — ${e.detail}` : ""}`;
  }
}

/** Nhãn vạch ngày: "Hôm nay" · "Hôm qua" · "Thứ Hai, 15/09" (khác năm thêm năm). */
export function nhanNgay(iso: string, now: Date): string {
  const t = new Date(iso);
  const ngay = soNgayLich(t, now);
  if (ngay === 0) return "Hôm nay";
  if (ngay === 1) return "Hôm qua";
  const nam = t.getFullYear() === now.getFullYear() ? "" : `/${t.getFullYear()}`;
  return `${THU_DAY_DU[t.getDay()]}, ${hai(t.getDate())}/${hai(t.getMonth() + 1)}${nam}`;
}

export type DongChat =
  | { loai: "ngay"; khoa: string; nhan: string }
  | { loai: "su-kien"; khoa: string; noiDung: string; luc: string }
  /** `cuoiNhom`: tin cuối nhóm mới hiện giờ. */
  | { loai: "tin"; khoa: string; tin: Message; dauNhom: boolean; cuoiNhom: boolean };

/**
 * Trộn tin + dòng hệ thống theo thời gian, chèn vạch ngày, gom nhóm tin liên
 * tiếp cùng người gửi trong 5 phút. Dòng hệ thống / vạch ngày cắt nhóm.
 * Cùng mốc giờ: tin đứng trước sự kiện (sắp xếp ổn định).
 */
export function dungDongChat(tin: Message[], suKien: ConversationEvent[], now: Date): DongChat[] {
  type Muc = { luc: number; iso: string } & (
    | { la: "tin"; tin: Message }
    | { la: "su-kien"; e: ConversationEvent }
  );
  const muc: Muc[] = [
    ...tin.map((m): Muc => ({ la: "tin", tin: m, iso: m.created_at, luc: Date.parse(m.created_at) })),
    ...suKien.map((e): Muc => ({ la: "su-kien", e, iso: e.created_at, luc: Date.parse(e.created_at) })),
  ].sort((a, b) => a.luc - b.luc);

  const ra: DongChat[] = [];
  let ngayTruoc = "";
  let tinTruoc: Message | null = null;

  const cungNguoi = (a: Message, b: Message) =>
    a.direction === b.direction && a.sender_user_id === b.sender_user_id;

  for (const m of muc) {
    const d = new Date(m.luc);
    const khoaNgay = `${d.getFullYear()}-${d.getMonth()}-${d.getDate()}`;
    if (khoaNgay !== ngayTruoc) {
      ra.push({ loai: "ngay", khoa: `ngay-${khoaNgay}`, nhan: nhanNgay(m.iso, now) });
      ngayTruoc = khoaNgay;
      tinTruoc = null;
    }
    if (m.la === "su-kien") {
      ra.push({ loai: "su-kien", khoa: m.e.id, noiDung: noiDungSuKien(m.e), luc: m.iso });
      tinTruoc = null;
      continue;
    }
    const noiNhom =
      tinTruoc !== null &&
      cungNguoi(tinTruoc, m.tin) &&
      m.luc - Date.parse(tinTruoc.created_at) <= GOM_NHOM_MS;
    if (noiNhom) {
      const cuoi = ra[ra.length - 1];
      if (cuoi.loai === "tin") cuoi.cuoiNhom = false;
    }
    ra.push({ loai: "tin", khoa: m.tin.id, tin: m.tin, dauNhom: !noiNhom, cuoiNhom: true });
    tinTruoc = m.tin;
  }
  return ra;
}

// ---------------------------------------------------------------------------
// 2b: mẫu trả lời, ghi chú
// ---------------------------------------------------------------------------

/** Bỏ dấu + thường hoá để lọc: gõ "bao gia" vẫn ra "Báo giá". */
export function boDau(chu: string): string {
  return chu.normalize("NFD").replace(/[\u0300-\u036f]/g, "").replace(/đ/gi, "d").toLowerCase();
}

/**
 * Chữ lọc mẫu khi người dùng gõ `/` ở ĐẦU ô soạn; `null` = không ở chế độ mẫu.
 * Chỉ tính khi cả ô là một dòng bắt đầu bằng `/` — gõ `/` giữa câu (đường dẫn,
 * phân số) không được bật danh sách mẫu.
 */
export function lenhMau(noiDung: string): string | null {
  const m = /^\/([^\n]*)$/.exec(noiDung);
  return m ? m[1] : null;
}

/** Lọc mẫu theo tiêu đề hoặc nội dung, không phân biệt dấu. */
export function locMau<T extends { title: string; body: string }>(mau: T[], chu: string): T[] {
  const tim = boDau(chu.trim());
  if (!tim) return mau;
  return mau.filter((m) => boDau(m.title).includes(tim) || boDau(m.body).includes(tim));
}

/** Dòng nói rõ ai thấy ghi chú (GĐ1 §10.4). */
export function nhanPhamViGhiChu(departmentName: string | null): string {
  return departmentName
    ? `Chỉ phòng ${departmentName} thấy ghi chú này`
    : "Chỉ quản trị viên thấy ghi chú này";
}
