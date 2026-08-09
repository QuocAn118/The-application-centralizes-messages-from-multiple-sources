/**
 * Đăng nhập: nhận email/mật khẩu, gọi backend, cất refresh token vào cookie
 * httpOnly rồi chỉ trả access token về cho trình duyệt.
 *
 * Đi vòng qua server thay vì gọi thẳng backend từ trình duyệt là có chủ ý: chỉ
 * ở đây mới đặt được cookie `httpOnly`.
 */

import { NextResponse } from "next/server";
import {
  REFRESH_COOKIE,
  REFRESH_MAX_AGE_SECONDS,
  SERVER_API_BASE_URL,
  publicTokenPayload,
  refreshCookieOptions,
} from "@/lib/session";
import type { TokenResponse } from "@/lib/types";

export async function POST(request: Request) {
  const { email, password } = (await request.json()) as {
    email?: string;
    password?: string;
  };

  const res = await fetch(`${SERVER_API_BASE_URL}/api/v1/auth/login`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email, password }),
  });

  if (!res.ok) {
    // Chuyển nguyên trạng lỗi của backend (401 sai mật khẩu, 429 quá nhiều lần
    // thử) để UI hiển thị đúng thông điệp thay vì gộp thành một lỗi chung.
    const body = await res.text();
    return new NextResponse(body, {
      status: res.status,
      headers: { "Content-Type": "application/json" },
    });
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
