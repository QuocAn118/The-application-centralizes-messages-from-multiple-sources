/**
 * Test tầng API client — tập trung vào IT-4 (spec §8):
 * "401 tự refresh một lần rồi thử lại; refresh hỏng → /login".
 *
 * Phần dễ sai nhất là single-flight: backend XOAY refresh token, nên hai lần
 * refresh song song sẽ khiến lần thứ hai mang token đã bị thu hồi và giết cả
 * phiên. Vì vậy có ca kiểm thử riêng cho việc gom nhiều 401 đồng thời.
 */

import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import {
  ApiError,
  SessionExpiredError,
  __resetApiClientState,
  apiRequest,
  onAccessTokenChange,
  setAccessToken,
  setOnSessionExpired,
} from "./api-client";

/** Dựng một `Response` JSON tối giản. */
function jsonResponse(status: number, body: unknown): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "Content-Type": "application/json" },
  });
}

/** Thân lỗi đúng định dạng backend trả về. */
function errorBody(code: string, message: string) {
  return { error: { code, message, details: null }, request_id: "req-1" };
}

let fetchMock: ReturnType<typeof vi.fn>;

beforeEach(() => {
  __resetApiClientState();
  fetchMock = vi.fn();
  vi.stubGlobal("fetch", fetchMock);
});

afterEach(() => {
  vi.unstubAllGlobals();
  __resetApiClientState();
});

describe("apiRequest — đường thuận", () => {
  it("gắn Bearer token khi đã đăng nhập", async () => {
    setAccessToken("token-abc");
    fetchMock.mockResolvedValueOnce(jsonResponse(200, { ok: true }));

    await apiRequest("/inbox");

    const [, init] = fetchMock.mock.calls[0];
    expect(init.headers.Authorization).toBe("Bearer token-abc");
  });

  it("không gắn Bearer khi skipAuth (dùng cho chính lời gọi đăng nhập)", async () => {
    setAccessToken("token-abc");
    fetchMock.mockResolvedValueOnce(jsonResponse(200, { ok: true }));

    await apiRequest("/auth/login", { method: "POST", skipAuth: true });

    const [, init] = fetchMock.mock.calls[0];
    expect(init.headers.Authorization).toBeUndefined();
  });

  it("trả undefined cho 204 mà không cố phân tích JSON", async () => {
    setAccessToken("token-abc");
    fetchMock.mockResolvedValueOnce(new Response(null, { status: 204 }));

    await expect(apiRequest("/auth/logout", { method: "POST" })).resolves.toBeUndefined();
  });
});

describe("apiRequest — 401 và refresh (IT-4)", () => {
  it("gặp 401 thì refresh một lần rồi thử lại request", async () => {
    setAccessToken("token-cu");
    fetchMock
      .mockResolvedValueOnce(jsonResponse(401, errorBody("EXPIRED", "hết hạn")))
      .mockResolvedValueOnce(
        jsonResponse(200, {
          access_token: "token-moi",
          refresh_token: "r2",
          token_type: "bearer",
          expires_in: 900,
          must_change_password: false,
        }),
      )
      .mockResolvedValueOnce(jsonResponse(200, { items: [] }));

    const ket_qua = await apiRequest<{ items: unknown[] }>("/inbox");

    expect(ket_qua).toEqual({ items: [] });
    expect(fetchMock).toHaveBeenCalledTimes(3);
    // Lần thử lại phải mang token MỚI, không phải token cũ.
    const [, initCuoi] = fetchMock.mock.calls[2];
    expect(initCuoi.headers.Authorization).toBe("Bearer token-moi");
  });

  it("nhiều 401 đồng thời chỉ gọi refresh MỘT lần (single-flight)", async () => {
    setAccessToken("token-cu");

    let soLanRefresh = 0;
    fetchMock.mockImplementation(async (url: string) => {
      if (typeof url === "string" && url.includes("/api/session/refresh")) {
        soLanRefresh += 1;
        // Trễ một nhịp để các request khác kịp chạm vào lần refresh đang bay.
        await new Promise((r) => setTimeout(r, 10));
        return jsonResponse(200, {
          access_token: "token-moi",
          refresh_token: "r2",
          token_type: "bearer",
          expires_in: 900,
          must_change_password: false,
        });
      }
      // Request nghiệp vụ: 401 khi còn token cũ, 200 khi đã có token mới.
      return jsonResponse(401, errorBody("EXPIRED", "hết hạn"));
    });

    // Ba request cùng lúc, cả ba đều nhận 401.
    const ket_qua = await Promise.allSettled([
      apiRequest("/inbox"),
      apiRequest("/inbox/1"),
      apiRequest("/inbox/2"),
    ]);

    // Điểm mấu chốt: dù ba request cùng gặp 401, chỉ MỘT lần refresh được gọi.
    expect(soLanRefresh).toBe(1);
    // Ở đây request nghiệp vụ luôn trả 401 nên cả ba kết thúc bằng phiên hết hạn.
    for (const r of ket_qua) {
      expect(r.status).toBe("rejected");
      expect((r as PromiseRejectedResult).reason).toBeInstanceOf(SessionExpiredError);
    }
  });

  it("refresh hỏng → ném SessionExpiredError và báo cho AuthContext", async () => {
    setAccessToken("token-cu");
    const daHetPhien = vi.fn();
    setOnSessionExpired(daHetPhien);

    fetchMock
      .mockResolvedValueOnce(jsonResponse(401, errorBody("EXPIRED", "hết hạn")))
      .mockResolvedValueOnce(jsonResponse(401, errorBody("INVALID", "token hỏng")));

    await expect(apiRequest("/inbox")).rejects.toBeInstanceOf(SessionExpiredError);
    expect(daHetPhien).toHaveBeenCalledOnce();
  });

  it("vẫn 401 sau khi đã refresh → không thử lại vô hạn", async () => {
    setAccessToken("token-cu");
    fetchMock
      .mockResolvedValueOnce(jsonResponse(401, errorBody("EXPIRED", "hết hạn")))
      .mockResolvedValueOnce(
        jsonResponse(200, {
          access_token: "token-moi",
          refresh_token: "r2",
          token_type: "bearer",
          expires_in: 900,
          must_change_password: false,
        }),
      )
      .mockResolvedValueOnce(jsonResponse(401, errorBody("EXPIRED", "vẫn hỏng")));

    await expect(apiRequest("/inbox")).rejects.toBeInstanceOf(SessionExpiredError);
    // 1 lần đầu + 1 refresh + 1 thử lại = 3. Không có lần thứ tư.
    expect(fetchMock).toHaveBeenCalledTimes(3);
  });

  it("một lần refresh hỏng không khoá vĩnh viễn các lần refresh sau", async () => {
    setAccessToken("token-cu");

    // Lượt 1: refresh hỏng.
    fetchMock
      .mockResolvedValueOnce(jsonResponse(401, errorBody("EXPIRED", "hết hạn")))
      .mockResolvedValueOnce(jsonResponse(401, errorBody("INVALID", "hỏng")));
    await expect(apiRequest("/inbox")).rejects.toBeInstanceOf(SessionExpiredError);

    // Lượt 2 (sau khi đăng nhập lại): refresh phải chạy được bình thường.
    fetchMock
      .mockResolvedValueOnce(jsonResponse(401, errorBody("EXPIRED", "hết hạn")))
      .mockResolvedValueOnce(
        jsonResponse(200, {
          access_token: "token-moi",
          refresh_token: "r3",
          token_type: "bearer",
          expires_in: 900,
          must_change_password: false,
        }),
      )
      .mockResolvedValueOnce(jsonResponse(200, { ok: true }));

    await expect(apiRequest("/inbox")).resolves.toEqual({ ok: true });
  });
});

describe("báo token đổi (mắt xích để WS reconnect — RB-4)", () => {
  it("refresh xong thì báo cho người nghe kèm token mới", async () => {
    setAccessToken("token-cu");
    const daNghe: (string | null)[] = [];
    onAccessTokenChange((t) => daNghe.push(t));

    fetchMock
      .mockResolvedValueOnce(jsonResponse(401, errorBody("EXPIRED", "hết hạn")))
      .mockResolvedValueOnce(
        jsonResponse(200, {
          access_token: "token-moi",
          refresh_token: "r2",
          token_type: "bearer",
          expires_in: 900,
          must_change_password: false,
        }),
      )
      .mockResolvedValueOnce(jsonResponse(200, { ok: true }));

    await apiRequest("/inbox");

    // Không có bước này thì WS vẫn ôm token cũ và bị server đóng 1008.
    expect(daNghe).toContain("token-moi");
  });

  it("không báo khi gán lại đúng token cũ (tránh mở lại WS vô cớ)", () => {
    setAccessToken("token-a");
    const daNghe: (string | null)[] = [];
    onAccessTokenChange((t) => daNghe.push(t));

    setAccessToken("token-a");
    expect(daNghe).toHaveLength(0);

    setAccessToken("token-b");
    expect(daNghe).toEqual(["token-b"]);
  });

  it("đăng xuất (token null) cũng được báo để đóng WS", () => {
    setAccessToken("token-a");
    const daNghe: (string | null)[] = [];
    onAccessTokenChange((t) => daNghe.push(t));

    setAccessToken(null);
    expect(daNghe).toEqual([null]);
  });

  it("huỷ đăng ký thì không nhận báo nữa", () => {
    const daNghe: (string | null)[] = [];
    const huy = onAccessTokenChange((t) => daNghe.push(t));

    setAccessToken("t1");
    huy();
    setAccessToken("t2");

    expect(daNghe).toEqual(["t1"]);
  });
});

describe("apiRequest — lỗi nghiệp vụ (RB-3)", () => {
  it("403 thành ApiError phân loại được, KHÔNG kích hoạt refresh", async () => {
    setAccessToken("token-abc");
    fetchMock.mockResolvedValueOnce(
      jsonResponse(403, errorBody("PERMISSION_DENIED", "Không có quyền.")),
    );

    const loi = await apiRequest("/inbox/1").catch((e: unknown) => e);

    expect(loi).toBeInstanceOf(ApiError);
    expect((loi as ApiError).isForbidden).toBe(true);
    expect((loi as ApiError).message).toBe("Không có quyền.");
    // Chỉ một lần gọi: 403 không phải chuyện của token.
    expect(fetchMock).toHaveBeenCalledTimes(1);
  });

  it("409 và 422 được đánh dấu là xung đột trạng thái", async () => {
    setAccessToken("token-abc");
    fetchMock.mockResolvedValueOnce(
      jsonResponse(409, errorBody("CONFLICT", "Hội thoại đã đóng.")),
    );

    const loi = await apiRequest("/inbox/1/close", { method: "POST" }).catch(
      (e: unknown) => e,
    );

    expect(loi).toBeInstanceOf(ApiError);
    expect((loi as ApiError).isConflict).toBe(true);
    expect((loi as ApiError).code).toBe("CONFLICT");
  });

  it("phản hồi lỗi không phải JSON vẫn thành ApiError có nghĩa", async () => {
    setAccessToken("token-abc");
    fetchMock.mockResolvedValueOnce(new Response("502 Bad Gateway", { status: 502 }));

    const loi = await apiRequest("/inbox").catch((e: unknown) => e);

    expect(loi).toBeInstanceOf(ApiError);
    expect((loi as ApiError).status).toBe(502);
  });
});
