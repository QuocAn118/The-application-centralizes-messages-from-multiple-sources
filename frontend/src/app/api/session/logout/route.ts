/**
 * Đăng xuất: thu hồi refresh token ở backend rồi xoá cookie.
 *
 * Cookie được xoá dù backend trả lỗi gì: người dùng đã bấm đăng xuất thì phiên
 * phải kết thúc ở phía trình duyệt, không thể để họ mắc kẹt vì backend trục trặc.
 */

import { NextResponse } from "next/server";
import { cookies } from "next/headers";
import { REFRESH_COOKIE, SERVER_API_BASE_URL } from "@/lib/session";

export async function POST(request: Request) {
  const store = await cookies();
  const refreshToken = store.get(REFRESH_COOKIE)?.value;
  const authorization = request.headers.get("Authorization");

  if (refreshToken && authorization) {
    try {
      // Endpoint logout của backend cần Bearer token của phiên hiện tại.
      await fetch(`${SERVER_API_BASE_URL}/api/v1/auth/logout`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: authorization,
        },
        body: JSON.stringify({ refresh_token: refreshToken }),
      });
    } catch {
      // Backend không phản hồi vẫn tiếp tục xoá cookie — xem chú thích đầu file.
    }
  }

  const response = new NextResponse(null, { status: 204 });
  response.cookies.delete(REFRESH_COOKIE);
  return response;
}
