/**
 * Tầng API client duy nhất (RB-1).
 *
 * Mọi màn gọi backend qua đây — không fetch rải rác. Trách nhiệm:
 * - gắn `Authorization: Bearer` từ access token giữ trong BỘ NHỚ (không
 *   localStorage, giảm bề mặt XSS — spec §7);
 * - gặp 401 thì tự làm mới token MỘT lần rồi thử lại request (RB-4);
 * - gom nhiều 401 đồng thời về CHỈ MỘT lần refresh (single-flight);
 * - ném `ApiError` có mã để UI xử lý 403/404/409/422 tử tế (RB-3).
 *
 * Refresh token KHÔNG đi qua đây: nó nằm trong cookie httpOnly, chỉ Route
 * Handler của Next đọc được (`/api/session/*`). Client chỉ biết "hãy refresh".
 */

import type { ApiErrorBody, TokenResponse } from "./types";

/** Lỗi từ API, mang đủ thông tin để UI quyết định cách hiển thị. */
export class ApiError extends Error {
  readonly status: number;
  readonly code: string;
  readonly details: unknown;
  readonly requestId: string | null;

  constructor(
    status: number,
    code: string,
    message: string,
    details: unknown = null,
    requestId: string | null = null,
  ) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.code = code;
    this.details = details;
    this.requestId = requestId;
  }

  /** Hết phiên: gọi lại cũng vô ích, phải đăng nhập lại. */
  get isUnauthorized(): boolean {
    return this.status === 401;
  }

  /** Không đủ quyền, hoặc server giấu sự tồn tại của tài nguyên. */
  get isForbidden(): boolean {
    return this.status === 403 || this.status === 404;
  }

  /**
   * Hành động không hợp lệ với trạng thái hiện tại (đóng hội thoại đã đóng,
   * reply khi không `DANG_MO`…). UI nên báo rõ rồi refetch để đồng bộ lại.
   */
  get isConflict(): boolean {
    return this.status === 409 || this.status === 422;
  }
}

/** Ném khi không thể làm mới phiên — người dùng phải đăng nhập lại. */
export class SessionExpiredError extends Error {
  constructor(message = "Phiên đăng nhập đã hết hạn.") {
    super(message);
    this.name = "SessionExpiredError";
  }
}

const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

/** Tiền tố của nhóm endpoint xác thực. Khác `/api/v1` trần — xem spec §6. */
const AUTH_PREFIX = "/api/v1/auth";

// ---------------------------------------------------------------------------
// Access token: giữ trong bộ nhớ module, không bao giờ chạm localStorage
// ---------------------------------------------------------------------------

let accessToken: string | null = null;

/** Đăng ký callback chạy khi phiên chết hẳn (để AuthContext đẩy về `/login`). */
let onSessionExpired: (() => void) | null = null;

/**
 * Những ai cần biết khi access token đổi.
 *
 * WebSocket mang token ở query string, nên token cũ hết hạn thì server đóng
 * kết nối (1008). Nghe sự kiện này để mở lại WS bằng token mới — nếu không,
 * realtime sẽ chết âm thầm sau lần refresh đầu tiên (RB-4).
 */
const nguoiNgheDoiToken = new Set<(token: string | null) => void>();

export function setAccessToken(token: string | null): void {
  const doi = accessToken !== token;
  accessToken = token;
  if (doi) {
    for (const nghe of nguoiNgheDoiToken) nghe(token);
  }
}

/** Đăng ký lắng nghe token đổi. Trả về hàm huỷ đăng ký. */
export function onAccessTokenChange(
  nghe: (token: string | null) => void,
): () => void {
  nguoiNgheDoiToken.add(nghe);
  return () => nguoiNgheDoiToken.delete(nghe);
}

export function getAccessToken(): string | null {
  return accessToken;
}

export function setOnSessionExpired(handler: (() => void) | null): void {
  onSessionExpired = handler;
}

// ---------------------------------------------------------------------------
// Refresh single-flight
// ---------------------------------------------------------------------------

/**
 * Promise của lần refresh ĐANG chạy, hoặc `null` khi rảnh.
 *
 * Đây là cốt lõi của single-flight: khi nhiều request cùng nhận 401, tất cả
 * cùng `await` một promise này thay vì mỗi request tự gọi refresh. Gọi song
 * song nhiều lần sẽ hỏng thật sự, không chỉ lãng phí: backend XOAY refresh
 * token (mỗi lần dùng sinh token mới và thu hồi token cũ), nên lần refresh thứ
 * hai sẽ mang token đã bị thu hồi và làm hỏng cả phiên.
 */
let refreshInFlight: Promise<string> | null = null;

/**
 * Làm mới token, đảm bảo chỉ một lần chạy tại một thời điểm.
 *
 * Refresh token nằm trong cookie httpOnly nên chính Route Handler gọi backend;
 * ở đây chỉ gọi sang route nội bộ đó và nhận access token mới.
 */
function refreshAccessToken(): Promise<string> {
  if (refreshInFlight) return refreshInFlight;

  refreshInFlight = (async () => {
    const res = await fetch("/api/session/refresh", {
      method: "POST",
      // Cookie httpOnly phải được gửi kèm, nếu không route handler không thấy.
      credentials: "include",
    });

    if (!res.ok) {
      throw new SessionExpiredError();
    }

    const data = (await res.json()) as TokenResponse;
    // Qua `setAccessToken` chứ không gán thẳng: WS phải được báo để mở lại
    // kết nối bằng token mới.
    setAccessToken(data.access_token);
    return data.access_token;
  })();

  // Dọn khoá dù thành công hay thất bại; nếu không, một lần refresh hỏng sẽ
  // khiến mọi lần refresh sau đó trả lại đúng promise lỗi đó mãi mãi.
  refreshInFlight = refreshInFlight.finally(() => {
    refreshInFlight = null;
  }) as Promise<string>;

  return refreshInFlight;
}

/** Chỉ dùng trong test — xoá trạng thái module giữa các ca kiểm thử. */
export function __resetApiClientState(): void {
  accessToken = null;
  refreshInFlight = null;
  onSessionExpired = null;
  nguoiNgheDoiToken.clear();
}

// ---------------------------------------------------------------------------
// Gọi API
// ---------------------------------------------------------------------------

export interface RequestOptions {
  method?: string;
  body?: unknown;
  query?: Record<string, string | number | undefined>;
  signal?: AbortSignal;
  /** Bỏ qua việc gắn Bearer (dùng cho chính lời gọi đăng nhập). */
  skipAuth?: boolean;
}

function buildUrl(path: string, query?: RequestOptions["query"]): string {
  const url = new URL(
    path.startsWith("/api") ? path : `/api/v1${path}`,
    API_BASE_URL,
  );
  if (query) {
    for (const [key, value] of Object.entries(query)) {
      if (value !== undefined) url.searchParams.set(key, String(value));
    }
  }
  return url.toString();
}

async function toApiError(res: Response): Promise<ApiError> {
  let code = "UNKNOWN_ERROR";
  let message = "Đã xảy ra lỗi.";
  let details: unknown = null;
  let requestId: string | null = null;

  try {
    const body = (await res.json()) as Partial<ApiErrorBody>;
    if (body?.error) {
      code = body.error.code ?? code;
      message = body.error.message ?? message;
      details = body.error.details ?? null;
    }
    requestId = body?.request_id ?? null;
  } catch {
    // Phản hồi lỗi không phải JSON (proxy, timeout…) — giữ thông điệp mặc định.
  }

  return new ApiError(res.status, code, message, details, requestId);
}

async function rawRequest(
  path: string,
  options: RequestOptions,
): Promise<Response> {
  const headers: Record<string, string> = {};
  if (options.body !== undefined) {
    headers["Content-Type"] = "application/json";
  }
  if (!options.skipAuth && accessToken) {
    headers["Authorization"] = `Bearer ${accessToken}`;
  }

  return fetch(buildUrl(path, options.query), {
    method: options.method ?? "GET",
    headers,
    body: options.body === undefined ? undefined : JSON.stringify(options.body),
    signal: options.signal,
  });
}

/**
 * Gọi API, tự làm mới token khi gặp 401 rồi thử lại ĐÚNG MỘT lần.
 *
 * Chỉ thử lại một lần là có chủ ý: nếu request đã mang token vừa mới làm mới
 * mà vẫn 401 thì vấn đề không nằm ở token, lặp thêm chỉ tạo vòng lặp vô hạn.
 */
export async function apiRequest<T>(
  path: string,
  options: RequestOptions = {},
): Promise<T> {
  let res = await rawRequest(path, options);

  if (res.status === 401 && !options.skipAuth) {
    try {
      await refreshAccessToken();
    } catch {
      onSessionExpired?.();
      throw new SessionExpiredError();
    }
    res = await rawRequest(path, options);

    // Vẫn 401 sau khi đã có token mới → phiên hỏng thật.
    if (res.status === 401) {
      onSessionExpired?.();
      throw new SessionExpiredError();
    }
  }

  if (!res.ok) {
    throw await toApiError(res);
  }

  // 204 No Content (logout, change-password) không có thân phản hồi.
  if (res.status === 204) {
    return undefined as T;
  }

  return (await res.json()) as T;
}

export const api = {
  get: <T>(path: string, query?: RequestOptions["query"], signal?: AbortSignal) =>
    apiRequest<T>(path, { method: "GET", query, signal }),

  post: <T>(path: string, body?: unknown, options: RequestOptions = {}) =>
    apiRequest<T>(path, { ...options, method: "POST", body }),
};

export { AUTH_PREFIX, API_BASE_URL };
