/**
 * Lời gọi API khu Báo cáo (#F5) + khoá cache.
 *
 * Cùng mẫu `nhan-su-api.ts` / `tu-khoa-api.ts`: gom một chỗ để biết vô hiệu hoá
 * đúng khoá nào (báo cáo chỉ đọc nên không có ghi, nhưng khoá vẫn cần cho React
 * Query theo khoảng ngày + phòng).
 *
 * **Bốn endpoint đều GET, đều trả mảng trần** (KHÔNG `PageResponse`) — đã đối
 * chiếu bằng lời gọi thật, không suy từ tên. Tham số chung: `from` (alias) +
 * `to` (bắt buộc, `YYYY-MM-DD`) + `department_id` (tuỳ chọn — chỉ Admin dùng
 * thực chất; Manager bị backend ép về phòng mình dù truyền gì).
 *
 * Mọi lệnh qua `api` của `api-client` — không `fetch` trực tiếp (RB-1 #F1).
 */

import { api } from "./api-client";
import type {
  AgentReportItem,
  ConversationReportItem,
  RequestReportItem,
  WorkforceReportItem,
} from "./types";

/** Khoảng ngày báo cáo (đóng hai đầu). `YYYY-MM-DD`. */
export interface KhoangNgay {
  tu: string;
  den: string;
}

export const khoaBaoCao = {
  all: ["bao-cao"] as const,
  /**
   * Khoá gồm cả khoảng ngày VÀ phòng: đổi khoảng hoặc đổi phòng là tải lại.
   * `phong` để `""` khi không lọc (Admin xem tất cả / Manager luôn phòng mình).
   */
  hoiThoai: (k: KhoangNgay, phong: string) =>
    ["bao-cao", "hoi-thoai", k.tu, k.den, phong] as const,
  nhanVien: (k: KhoangNgay, phong: string) =>
    ["bao-cao", "nhan-vien", k.tu, k.den, phong] as const,
  caKpi: (k: KhoangNgay, phong: string) =>
    ["bao-cao", "ca-kpi", k.tu, k.den, phong] as const,
  donTu: (k: KhoangNgay, phong: string) =>
    ["bao-cao", "don-tu", k.tu, k.den, phong] as const,
};

/** Tham số query chung. `from` là alias của backend, không phải `from_`. */
function thamSo(k: KhoangNgay, phong?: string) {
  return { from: k.tu, to: k.den, department_id: phong || undefined };
}

export function baoCaoHoiThoai(
  k: KhoangNgay,
  phong?: string,
  signal?: AbortSignal,
): Promise<ConversationReportItem[]> {
  return api.get<ConversationReportItem[]>("/analytics/conversations", thamSo(k, phong), signal);
}

export function baoCaoNhanVien(
  k: KhoangNgay,
  phong?: string,
  signal?: AbortSignal,
): Promise<AgentReportItem[]> {
  return api.get<AgentReportItem[]>("/analytics/agents", thamSo(k, phong), signal);
}

export function baoCaoCaKpi(
  k: KhoangNgay,
  phong?: string,
  signal?: AbortSignal,
): Promise<WorkforceReportItem[]> {
  return api.get<WorkforceReportItem[]>("/analytics/workforce", thamSo(k, phong), signal);
}

export function baoCaoDonTu(
  k: KhoangNgay,
  phong?: string,
  signal?: AbortSignal,
): Promise<RequestReportItem[]> {
  return api.get<RequestReportItem[]>("/analytics/requests", thamSo(k, phong), signal);
}
