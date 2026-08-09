/**
 * Test phần logic thuần của lớp realtime.
 *
 * Vòng đời WS (mở/đóng/thử lại) được kiểm bằng trình duyệt thật ở kịch bản
 * hai-tab; ở đây kiểm hai thứ dễ sai mà không cần dựng socket: dựng URL và
 * tính thời gian chờ.
 */

import { describe, expect, it } from "vitest";
import { duongDanWebSocket, thoiGianCho } from "./use-inbox-socket";

describe("duongDanWebSocket", () => {
  it("đổi http sang ws và gắn token", () => {
    const u = new URL(duongDanWebSocket("http://127.0.0.1:8000", "abc"));
    expect(u.protocol).toBe("ws:");
    expect(u.host).toBe("127.0.0.1:8000");
    expect(u.pathname).toBe("/ws/inbox");
    expect(u.searchParams.get("token")).toBe("abc");
  });

  it("đổi https sang wss (token đi qua query string nên phải có TLS)", () => {
    const u = new URL(duongDanWebSocket("https://omnichat.example", "xyz"));
    expect(u.protocol).toBe("wss:");
  });

  it("KHÔNG thêm tiền tố /api/v1 — WS nằm ngoài nhóm đó", () => {
    const u = new URL(duongDanWebSocket("http://localhost:8000", "t"));
    expect(u.pathname).toBe("/ws/inbox");
    expect(u.pathname).not.toContain("api/v1");
  });

  it("bỏ qua đường dẫn thừa trong base URL", () => {
    const u = new URL(duongDanWebSocket("http://localhost:8000/api/v1", "t"));
    expect(u.pathname).toBe("/ws/inbox");
  });

  it("token được mã hoá đúng khi có ký tự đặc biệt", () => {
    const token = "a+b/c=d&e";
    const u = new URL(duongDanWebSocket("http://localhost:8000", token));
    expect(u.searchParams.get("token")).toBe(token);
  });
});

describe("thoiGianCho — backoff", () => {
  it("tăng dần theo số lần thử", () => {
    // Cố định phần ngẫu nhiên để so sánh được.
    const a = thoiGianCho(0, 1);
    const b = thoiGianCho(1, 1);
    const c = thoiGianCho(2, 1);
    expect(b).toBeGreaterThan(a);
    expect(c).toBeGreaterThan(b);
  });

  it("chặn trần ở 30 giây dù thử rất nhiều lần", () => {
    expect(thoiGianCho(50, 1)).toBeLessThanOrEqual(30_000);
    expect(thoiGianCho(100, 1)).toBeLessThanOrEqual(30_000);
  });

  it("luôn chờ ít nhất nửa giây — không quay vòng đập server", () => {
    for (let lan = 0; lan < 10; lan += 1) {
      expect(thoiGianCho(lan, 0)).toBeGreaterThanOrEqual(500);
    }
  });

  it("có nhiễu để nhiều tab không thử lại cùng nhịp", () => {
    const som = thoiGianCho(3, 0);
    const muon = thoiGianCho(3, 1);
    expect(som).not.toBe(muon);
  });
});
