/**
 * Thân yêu cầu khi sửa kênh (#F2 task 3.3–3.4).
 *
 * Hai quy tắc ở đây sai thì **không có gì báo lỗi** — server trả 200 và người
 * dùng tưởng đã làm xong:
 *
 * - RB-7: gỡ phòng phải là `clear_department: true`. Gửi `department_id: null`
 *   bị `UpdateChannelRequest` hiểu là "không đổi".
 * - Để trống ô token = **giữ token hiện tại**, nên khoá `credential` phải VẮNG
 *   MẶT hẳn. Gửi `credential: ""` sẽ bị Pydantic từ chối (`min_length=1`), còn
 *   gửi `credential: null` thì tuỳ backend mà thành xoá token.
 *
 * Logic dựng thân nằm ở `thanSuaKenh` trong `quan-tri-api.ts` chứ không nằm
 * trong component, đúng để test gọi được **mã đang chạy thật** — chép lại
 * logic vào file test thì component đổi mà test vẫn xanh.
 */

import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { __resetApiClientState, setAccessToken } from "./api-client";
import { suaKenh, thanSuaKenh } from "./quan-tri-api";

let fetchMock: ReturnType<typeof vi.fn>;

function thanDaGui(): Record<string, unknown> {
  const init = fetchMock.mock.calls[0][1] as RequestInit;
  return JSON.parse(String(init.body)) as Record<string, unknown>;
}

beforeEach(() => {
  __resetApiClientState();
  fetchMock = vi.fn().mockResolvedValue(
    new Response(JSON.stringify({ id: "k-1" }), {
      status: 200,
      headers: { "Content-Type": "application/json" },
    }),
  );
  vi.stubGlobal("fetch", fetchMock);
  setAccessToken("token-test");
});

afterEach(() => {
  vi.unstubAllGlobals();
  __resetApiClientState();
});

describe("RB-7 — gỡ phòng khỏi kênh", () => {
  it("ô phòng để trống thì gửi clear_department, KHÔNG gửi department_id", async () => {
    await suaKenh("k-1", thanSuaKenh({ ten: "Kênh A", token: "", phongId: "" }));
    const than = thanDaGui();

    expect(than.clear_department).toBe(true);
    // Đây là chỗ chết người: có `department_id: null` thì backend hiểu "không
    // đổi" và việc gỡ im lặng thất bại.
    expect("department_id" in than).toBe(false);
  });

  it("chọn phòng thì gửi department_id và KHÔNG gửi clear_department", async () => {
    await suaKenh("k-1", thanSuaKenh({ ten: "Kênh A", token: "", phongId: "p-9" }));
    const than = thanDaGui();

    expect(than.department_id).toBe("p-9");
    expect("clear_department" in than).toBe(false);
  });
});

describe("RB-6 — token khi sửa", () => {
  it("để trống ô token thì KHÔNG gửi khoá credential (giữ token hiện tại)", async () => {
    await suaKenh("k-1", thanSuaKenh({ ten: "Kênh A", token: "", phongId: "p-9" }));
    const than = thanDaGui();

    expect("credential" in than).toBe(false);
    // Chuỗi rỗng cũng không được: Pydantic đặt `min_length=1`.
    expect(than.credential).toBeUndefined();
  });

  it("nhập token mới thì gửi đúng nguyên văn", async () => {
    await suaKenh("k-1", thanSuaKenh({ ten: "Kênh A", token: "bot123:ABC", phongId: "p-9" }));
    expect(thanDaGui().credential).toBe("bot123:ABC");
  });
});
