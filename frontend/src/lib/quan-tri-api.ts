/**
 * Lời gọi API của khu quản trị (#F2) + khoá cache dùng chung.
 *
 * Gom một chỗ như `inbox-api.ts`: sau mỗi thao tác ghi (tạo/sửa/vô hiệu hoá)
 * phải vô hiệu hoá đúng khoá, và nếu khoá rải rác trong component thì rất dễ sót.
 *
 * Mọi lệnh đi qua `api` của `api-client` — không `fetch` trực tiếp (RB-1 #F1).
 */

import { api } from "./api-client";
import type {
  AuditAction,
  AuditLogEntry,
  Channel,
  Department,
  PageResponse,
  Platform,
  Role,
  ThamSoNguoiDung,
  UserResponse,
} from "./types";

/** Số dòng mỗi trang. Backend chặn trần ở 100. */
export const KICH_THUOC_TRANG = 25;

export const khoaQuanTri = {
  nguoiDung: {
    all: ["quan-tri", "nguoi-dung"] as const,
    list: (thamSo: ThamSoNguoiDung) =>
      ["quan-tri", "nguoi-dung", "list", thamSo] as const,
  },
  phongBan: {
    all: ["quan-tri", "phong-ban"] as const,
  },
  kenh: {
    all: ["quan-tri", "kenh"] as const,
  },
  nhatKy: {
    all: ["quan-tri", "nhat-ky"] as const,
  },
};

// ---------------------------------------------------------------------------
// Người dùng
// ---------------------------------------------------------------------------

export function layDanhSachNguoiDung(
  thamSo: ThamSoNguoiDung,
  signal?: AbortSignal,
): Promise<PageResponse<UserResponse>> {
  return api.get<PageResponse<UserResponse>>(
    "/users",
    {
      search: thamSo.search || undefined,
      role: thamSo.role,
      department_id: thamSo.department_id,
      // Chuỗi hoá tường minh: `false` phải lên URL, không được rơi mất.
      is_active: thamSo.is_active === undefined ? undefined : String(thamSo.is_active),
      limit: thamSo.limit,
      offset: thamSo.offset,
    },
    signal,
  );
}

export interface DuLieuTaoNguoiDung {
  email: string;
  full_name: string;
  phone?: string | null;
  role: Role;
  department_id?: string | null;
  password: string;
}

export function taoNguoiDung(duLieu: DuLieuTaoNguoiDung): Promise<UserResponse> {
  return api.post<UserResponse>("/users", duLieu);
}

/** Chỉ sửa được tên và điện thoại — backend không nhận trường khác. */
export function suaHoSo(
  userId: string,
  duLieu: { full_name?: string; phone?: string | null },
): Promise<UserResponse> {
  return api.patch<UserResponse>(`/users/${userId}`, duLieu);
}

/**
 * Đổi vai trò. ``department_id`` đi kèm vì đổi sang MANAGER thì backend cần
 * biết phòng nào — và mỗi phòng chỉ được một Manager.
 */
export function doiVaiTro(
  userId: string,
  duLieu: { role: Role; department_id?: string | null },
): Promise<UserResponse> {
  return api.patch<UserResponse>(`/users/${userId}/role`, duLieu);
}

export function doiPhongBan(
  userId: string,
  departmentId: string | null,
): Promise<UserResponse> {
  return api.patch<UserResponse>(`/users/${userId}/department`, {
    department_id: departmentId,
  });
}

export function voHieuHoaNguoiDung(userId: string): Promise<UserResponse> {
  return api.post<UserResponse>(`/users/${userId}/deactivate`);
}

export function kichHoatLaiNguoiDung(userId: string): Promise<UserResponse> {
  return api.post<UserResponse>(`/users/${userId}/reactivate`);
}

/**
 * Đặt lại mật khẩu.
 *
 * Trả **204 No Content**, KHÔNG trả `UserResponse` như mọi thao tác khác trên
 * `/users` — đã đối chiếu `openapi.json` và xác nhận bằng lời gọi thật. Khai là
 * `UserResponse` thì `tsc` vẫn xanh (api-client trả `undefined as T` cho 204)
 * còn UI nhận `undefined` rồi vỡ lúc chạy. Vì vậy trả `void` và nơi gọi phải
 * refetch nếu cần dữ liệu mới.
 */
export function datLaiMatKhau(userId: string, matKhauMoi: string): Promise<void> {
  return api.post<void>(`/users/${userId}/reset-password`, {
    new_password: matKhauMoi,
  });
}

// ---------------------------------------------------------------------------
// Phòng ban
// ---------------------------------------------------------------------------

/**
 * Danh sách phòng ban.
 *
 * `GET /departments` trả **PageResponse**, không phải mảng trần như
 * `/channels` — đã đối chiếu `openapi.json`. Lấy trần 100 (mức backend cho
 * phép) vì số phòng ban thực tế nhỏ, không cần phân trang ở UI.
 *
 * Khác `layPhongBanHoatDong` của #F1 (chỉ lấy `is_active=true` để chọn phòng
 * khi phân hội thoại): màn quản trị phải thấy **cả phòng đã ngừng hoạt động**
 * thì mới bật lại hay kiểm tra được.
 */
export function layDanhSachPhongBan(
  signal?: AbortSignal,
): Promise<PageResponse<Department>> {
  return api.get<PageResponse<Department>>(
    "/departments",
    { limit: 100, offset: 0 },
    signal,
  );
}

export function taoPhongBan(duLieu: {
  name: string;
  description?: string | null;
}): Promise<Department> {
  return api.post<Department>("/departments", duLieu);
}

export function suaPhongBan(
  departmentId: string,
  duLieu: { name?: string; description?: string | null },
): Promise<Department> {
  return api.patch<Department>(`/departments/${departmentId}`, duLieu);
}

/** Backend KHÔNG có DELETE — chỉ ngừng hoạt động, dữ liệu cũ giữ nguyên. */
export function ngungHoatDongPhongBan(departmentId: string): Promise<Department> {
  return api.post<Department>(`/departments/${departmentId}/deactivate`);
}

// ---------------------------------------------------------------------------
// Kênh
// ---------------------------------------------------------------------------

export function layDanhSachKenh(
  isActive?: boolean,
  signal?: AbortSignal,
): Promise<Channel[]> {
  return api.get<Channel[]>(
    "/channels",
    { is_active: isActive === undefined ? undefined : String(isActive) },
    signal,
  );
}

export function ketNoiKenh(duLieu: {
  platform: Platform;
  external_channel_id: string;
  name: string;
  credential: string;
  department_id?: string | null;
}): Promise<Channel> {
  return api.post<Channel>("/channels", duLieu);
}

/**
 * Sửa kênh.
 *
 * Hai điều dễ sai, đều đã đối chiếu `UpdateChannelRequest`:
 * - ``credential`` bỏ trống = **giữ token hiện tại**, không phải xoá.
 * - Muốn gỡ phòng phải gửi ``clear_department: true``; gửi
 *   ``department_id: null`` bị hiểu là "không đổi".
 */
export function suaKenh(
  channelId: string,
  duLieu: {
    name?: string;
    credential?: string;
    department_id?: string | null;
    clear_department?: boolean;
  },
): Promise<Channel> {
  return api.patch<Channel>(`/channels/${channelId}`, duLieu);
}

export function ngatKenh(channelId: string): Promise<Channel> {
  return api.post<Channel>(`/channels/${channelId}/deactivate`);
}

// ---------------------------------------------------------------------------
// Nhật ký
// ---------------------------------------------------------------------------

export interface ThamSoNhatKy {
  actor_id?: string;
  action?: AuditAction;
  resource_type?: string;
  from_time?: string;
  to_time?: string;
  limit: number;
  offset: number;
}

export function layNhatKy(
  thamSo: ThamSoNhatKy,
  signal?: AbortSignal,
): Promise<PageResponse<AuditLogEntry>> {
  return api.get<PageResponse<AuditLogEntry>>(
    "/audit-logs",
    {
      actor_id: thamSo.actor_id,
      action: thamSo.action,
      resource_type: thamSo.resource_type,
      from_time: thamSo.from_time,
      to_time: thamSo.to_time,
      limit: thamSo.limit,
      offset: thamSo.offset,
    },
    signal,
  );
}
