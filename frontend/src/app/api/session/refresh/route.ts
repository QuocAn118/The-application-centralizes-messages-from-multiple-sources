/**
 * Làm mới token từ refresh token trong cookie httpOnly.
 *
 * Backend XOAY refresh token: mỗi lần dùng sẽ sinh token mới và thu hồi token
 * cũ. Vì vậy cookie phải được ghi đè bằng token mới ngay trong phản hồi này —
 * bỏ sót bước đó thì lần refresh kế tiếp sẽ mang token đã bị thu hồi và giết
 * cả phiên.
 */

import { NextResponse } from "next/server";
import { cookies } from "next/headers";
import {
  REFRESH_COOKIE,
  REFRESH_MAX_AGE_SECONDS,
  SERVER_API_BASE_URL,
  publicTokenPayload,
  refreshCookieOptions,
} from "@/lib/session";
import type { TokenResponse } from "@/lib/types";

export async function POST() {
  const store = await cookies();
  const refreshToken = store.get(REFRESH_COOKIE)?.value;

  if (!refreshToken) {
    return NextResponse.json(
      { error: { code: "NO_SESSION", message: "Chưa đăng nhập.", details: null } },
      { status: 401 },
    );
  }

  const res = await fetch(`${SERVER_API_BASE_URL}/api/v1/auth/refresh`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ refresh_token: refreshToken }),
  });

  if (!res.ok) {
    // Refresh token hỏng/hết hạn/bị thu hồi: xoá cookie để lần sau không thử
    // lại bằng một token chắc chắn vô dụng.
    const response = NextResponse.json(
      { error: { code: "SESSION_EXPIRED", message: "Phiên đã hết hạn.", details: null } },
      { status: 401 },
    );
    response.cookies.delete(REFRESH_COOKIE);
    return response;
  }

  const tokens = (await res.json()) as TokenResponse;

  const response = NextResponse.json(publicTokenPayload(tokens));
  response.cookies.set(
    REFRESH_COOKIE,
    tokens.refresh_token,
    refreshCookieOptions(REFRESH_MAX_AGE_SECONDS),
  );
  return response;
}
