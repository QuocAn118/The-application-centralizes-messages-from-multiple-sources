/**
 * Quy ước cookie phiên — dùng chung giữa các Route Handler.
 *
 * Refresh token nằm trong cookie `httpOnly` để JavaScript trên trang không đọc
 * được: nếu có lỗ XSS, kẻ tấn công vẫn không lấy được token dài hạn. Access
 * token thì ngược lại — chỉ sống trong bộ nhớ, không bao giờ vào cookie.
 */

import type { TokenResponse } from "./types";

export const REFRESH_COOKIE = "omnichat_refresh";

/** URL backend dùng ở phía server (không lộ ra trình duyệt). */
export const SERVER_API_BASE_URL =
  process.env.API_BASE_URL ??
  process.env.NEXT_PUBLIC_API_BASE_URL ??
  "http://localhost:8000";

/**
 * Thuộc tính cookie refresh token.
 *
 * `SameSite=Lax` đủ cho luồng đăng nhập thường và vẫn chặn gửi cookie trong
 * request chéo trang; `Secure` chỉ bật ở production vì môi trường dev chạy HTTP.
 */
export function refreshCookieOptions(maxAge: number) {
  return {
    httpOnly: true,
    sameSite: "lax" as const,
    secure: process.env.NODE_ENV === "production",
    path: "/",
    maxAge,
  };
}

/**
 * Thân phản hồi trả về cho client sau login/refresh.
 *
 * Cố ý LƯỢC BỎ `refresh_token`: nó đã nằm trong cookie httpOnly, gửi thêm bản
 * sao xuống JavaScript sẽ vô hiệu hoá chính lớp bảo vệ vừa dựng.
 */
export function publicTokenPayload(tokens: TokenResponse) {
  return {
    access_token: tokens.access_token,
    token_type: tokens.token_type,
    expires_in: tokens.expires_in,
    must_change_password: tokens.must_change_password,
  };
}

/** Số giây sống của cookie refresh. Mặc định 30 ngày, khớp cấu hình backend. */
export const REFRESH_MAX_AGE_SECONDS = 60 * 60 * 24 * 30;
