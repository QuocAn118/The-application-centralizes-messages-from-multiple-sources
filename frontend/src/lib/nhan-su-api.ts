/**
 * Lời gọi API của khu Nhân sự (#F3) + khoá cache dùng chung.
 *
 * Cùng mẫu với `quan-tri-api.ts`: gom một chỗ để sau mỗi thao tác ghi biết phải
 * vô hiệu hoá đúng khoá nào.
 *
 * **Hình dạng phản hồi không đồng nhất** — đã đối chiếu `openapi.json` của
 * server đang chạy, không suy từ tên endpoint:
 * - `/requests` trả `PageResponse`
 * - `/shifts`, `/shift-assignments`, `/kpi-targets` trả **mảng trần**
 *
 * Mọi lệnh đi qua `api` của `api-client` — không `fetch` trực tiếp (RB-1 #F1).
 */

import { api } from "./api-client";
import type {
  KpiMetricType,
  KpiProgress,
  KpiSubjectType,
  KpiTarget,
  LeaveRequest,
  PageResponse,
  RequestStatus,
  RequestType,
  Shift,
  ShiftAssignment,
} from "./types";

/** Số dòng mỗi trang đơn từ. Backend chặn trần ở 200. */
export const KICH_THUOC_TRANG_DON = 25;

export const khoaNhanSu = {
  ca: {
    all: ["nhan-su", "ca"] as const,
  },
  phanCa: {
    all: ["nhan-su", "phan-ca"] as const,
    /** Lịch theo khoảng ngày — khoá gồm khoảng để đổi tuần là tải lại. */
    khoang: (tu: string, den: string) => ["nhan-su", "phan-ca", tu, den] as const,
  },
  don: {
    all: ["nhan-su", "don"] as const,
  },
  kpi: {
    all: ["nhan-su", "kpi"] as const,
    /**
     * Tiến độ của một đối tượng/kỳ/chỉ số.
     *
     * Đặt dưới `kpi.all` để đặt mục tiêu mới là làm mới luôn tiến độ — phần
     * trăm hoàn thành phụ thuộc chính mục tiêu vừa đổi.
     */
    tienDo: (
      subjectType: KpiSubjectType,
      subjectId: string,
      metricType: KpiMetricType,
      nam: number,
      thang: number,
    ) => ["nhan-su", "kpi", "tien-do", subjectType, subjectId, metricType, nam, thang] as const,
  },
};

// ---------------------------------------------------------------------------
// Ca làm việc
// ---------------------------------------------------------------------------

/** Mảng trần, KHÔNG phải PageResponse. Phạm vi do backend lọc theo vai. */
export function layDanhSachCa(isActive?: boolean, signal?: AbortSignal): Promise<Shift[]> {
  return api.get<Shift[]>(
    "/shifts",
    { is_active: isActive === undefined ? undefined : String(isActive) },
    signal,
  );
}

export interface DuLieuCa {
  name: string;
  /** "HH:MM" — backend nhận `time`, chấp nhận cả "HH:MM" lẫn "HH:MM:SS". */
  start_time: string;
  end_time: string;
}

export function taoCa(duLieu: DuLieuCa & { department_id: string }): Promise<Shift> {
  return api.post<Shift>("/shifts", duLieu);
}

/**
 * Sửa mẫu ca.
 *
 * `UpdateShiftRequest` đòi **cả ba trường** (`name`, `start_time`, `end_time`
 * đều không có default) — không phải PATCH từng phần như `/users`. Gửi thiếu
 * một trường là 422.
 */
export function suaCa(shiftId: string, duLieu: DuLieuCa): Promise<Shift> {
  return api.patch<Shift>(`/shifts/${shiftId}`, duLieu);
}

/** Backend không có DELETE, cũng không có kích hoạt lại. */
export function ngungCa(shiftId: string): Promise<Shift> {
  return api.post<Shift>(`/shifts/${shiftId}/deactivate`);
}

// ---------------------------------------------------------------------------
// Phân ca
// ---------------------------------------------------------------------------

export function layLichPhanCa(
  tu: string,
  den: string,
  signal?: AbortSignal,
): Promise<ShiftAssignment[]> {
  return api.get<ShiftAssignment[]>(
    "/shift-assignments",
    { date_from: tu, date_to: den },
    signal,
  );
}

export function phanCa(duLieu: {
  shift_id: string;
  user_id: string;
  /** "YYYY-MM-DD". */
  work_date: string;
}): Promise<ShiftAssignment> {
  return api.post<ShiftAssignment>("/shift-assignments", duLieu);
}

export function huyPhanCa(assignmentId: string): Promise<ShiftAssignment> {
  return api.post<ShiftAssignment>(`/shift-assignments/${assignmentId}/cancel`);
}

// ---------------------------------------------------------------------------
// Đơn từ
// ---------------------------------------------------------------------------

export interface ThamSoDon {
  status?: RequestStatus;
  limit: number;
  offset: number;
}

export function layDanhSachDon(
  thamSo: ThamSoDon,
  signal?: AbortSignal,
): Promise<PageResponse<LeaveRequest>> {
  return api.get<PageResponse<LeaveRequest>>(
    "/requests",
    { status: thamSo.status, limit: thamSo.limit, offset: thamSo.offset },
    signal,
  );
}

export function guiDon(duLieu: {
  request_type: RequestType;
  reason: string;
  /** Chỉ `NGHI_PHEP` mới có; hai loại kia gửi `null`. */
  leave_start?: string | null;
  leave_end?: string | null;
}): Promise<LeaveRequest> {
  return api.post<LeaveRequest>("/requests", duLieu);
}

export function duyetDon(requestId: string): Promise<LeaveRequest> {
  return api.post<LeaveRequest>(`/requests/${requestId}/approve`);
}

/** `reason` bắt buộc (`min_length=1`) — khác duyệt, vốn không cần lý do (RB-7). */
export function tuChoiDon(requestId: string, lyDo: string): Promise<LeaveRequest> {
  return api.post<LeaveRequest>(`/requests/${requestId}/reject`, { reason: lyDo });
}

/** Người gửi tự thu hồi khi đơn còn `CHO_DUYET`. */
export function thuHoiDon(requestId: string): Promise<LeaveRequest> {
  return api.post<LeaveRequest>(`/requests/${requestId}/cancel`);
}

// ---------------------------------------------------------------------------
// KPI
// ---------------------------------------------------------------------------

/**
 * Danh sách mục tiêu KPI.
 *
 * Kỳ là **cặp** năm+tháng: backend chỉ dựng `KpiPeriod` khi có đủ cả hai, gửi
 * lẻ một cái thì nó lặng lẽ bỏ qua bộ lọc kỳ.
 */
export function layMucTieuKpi(
  ky?: { nam: number; thang: number },
  signal?: AbortSignal,
): Promise<KpiTarget[]> {
  return api.get<KpiTarget[]>(
    "/kpi-targets",
    { period_year: ky?.nam, period_month: ky?.thang },
    signal,
  );
}

export function datMucTieuKpi(duLieu: {
  subject_type: KpiSubjectType;
  subject_id: string;
  metric_type: KpiMetricType;
  period_year: number;
  period_month: number;
  /** Chuỗi vì backend nhận `Decimal` — không làm tròn qua `number`. */
  target_value: string;
}): Promise<KpiTarget> {
  return api.post<KpiTarget>("/kpi-targets", duLieu);
}

export function layTienDoKpi(
  thamSo: {
    subject_type: KpiSubjectType;
    subject_id: string;
    metric_type: KpiMetricType;
    period_year: number;
    period_month: number;
  },
  signal?: AbortSignal,
): Promise<KpiProgress> {
  return api.get<KpiProgress>("/kpi-progress", { ...thamSo }, signal);
}
