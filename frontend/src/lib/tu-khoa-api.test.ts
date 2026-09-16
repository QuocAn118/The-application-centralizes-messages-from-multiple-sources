/**
 * Test tầng gọi API của khu Từ khoá (#F4 task 1.5).
 *
 * Trọng tâm là những chỗ **`tsc` không bắt được**: kiểu trả về của 204, và
 * tham số lên URL.
 */

import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { __resetApiClientState, setAccessToken } from "./api-client";
import {
  KICH_THUOC_TRANG_PHAN_TICH,
  layDanhSachPhanTich,
  layDanhSachTuKhoa,
  suaTuKhoa,
  taoTuKhoa,
  xoaTuKhoa,
} from "./tu-khoa-api";

let fetchMock: ReturnType<typeof vi.fn>;

function jsonResponse(body: unknown): Response {
  return new Response(JSON.stringify(body), {
    status: 200,
    headers: { "Content-Type": "application/json" },
  });
}

function urlDaGoi(i = 0): URL {
  return new URL(String(fetchMock.mock.calls[i][0]));
}

function thanDaGui(i = 0): unknown {
  const init = fetchMock.mock.calls[i][1] as RequestInit;
  return JSON.parse(String(init.body));
}

function phuongThuc(i = 0): string {
  return String((fetchMock.mock.calls[i][1] as RequestInit).method);
}

beforeEach(() => {
  __resetApiClientState();
  fetchMock = vi.fn().mockResolvedValue(jsonResponse([]));
  vi.stubGlobal("fetch", fetchMock);
  setAccessToken("token-test");
});

afterEach(() => {
  vi.unstubAllGlobals();
  __resetApiClientState();
});

describe("xoaTuKhoa", () => {
  it("chịu được 204 No Content — endpoint này KHÔNG trả KeywordResponse", async () => {
    // Đã đối chiếu bằng lời gọi thật: DELETE /keywords/{id} trả 204, không có
    // thân. Khai nhầm thành `Promise<Keyword>` thì `tsc` VẪN XANH (api-client
    // trả `undefined as T` cho 204) còn UI nhận `undefined` rồi vỡ lúc chạy —
    // đúng cái bẫy đã dính ở `datLaiMatKhau` của #F2.
    fetchMock.mockResolvedValueOnce(new Response(null, { status: 204 }));
    await expect(xoaTuKhoa("k-1")).resolves.toBeUndefined();
    expect(phuongThuc()).toBe("DELETE");
  });

  it("gọi đúng đường dẫn", async () => {
    fetchMock.mockResolvedValueOnce(new Response(null, { status: 204 }));
    await xoaTuKhoa("k-42");
    expect(urlDaGoi().pathname).toContain("/keywords/k-42");
  });
});

describe("taoTuKhoa", () => {
  it("gửi cả department_id và text", async () => {
    fetchMock.mockResolvedValueOnce(
      jsonResponse({ id: "k", department_id: "p", text: "Bảo Hành", normalized: "bao hanh" }),
    );
    await taoTuKhoa({ department_id: "p-1", text: "Bảo Hành" });
    expect(thanDaGui()).toEqual({ department_id: "p-1", text: "Bảo Hành" });
  });

  it("KHÔNG tự chuẩn hoá text trước khi gửi", async () => {
    // RB-3: chuẩn hoá là việc của backend. FE gửi nguyên văn người dùng gõ —
    // tự bỏ dấu ở đây là chép thuật toán sang chỗ thứ hai để hai bản lệch nhau.
    fetchMock.mockResolvedValueOnce(
      jsonResponse({ id: "k", department_id: "p", text: "Bảo Hành", normalized: "bao hanh" }),
    );
    await taoTuKhoa({ department_id: "p-1", text: "Bảo Hành" });
    expect((thanDaGui() as { text: string }).text).toBe("Bảo Hành");
  });
});

describe("suaTuKhoa", () => {
  it("PATCH chỉ gửi text — không gửi department_id (RB-6)", async () => {
    // `UpdateKeywordRequest` chỉ có `text`; gửi thừa trường là mời 422.
    fetchMock.mockResolvedValueOnce(
      jsonResponse({ id: "k", department_id: "p", text: "moi", normalized: "moi" }),
    );
    await suaTuKhoa("k-1", "moi");
    expect(thanDaGui()).toEqual({ text: "moi" });
    expect(phuongThuc()).toBe("PATCH");
  });
});

describe("layDanhSachTuKhoa", () => {
  it("không gửi tham số phân trang — endpoint trả mảng trần", async () => {
    await layDanhSachTuKhoa();
    expect(urlDaGoi().searchParams.has("limit")).toBe(false);
    expect(urlDaGoi().searchParams.has("offset")).toBe(false);
  });
});

describe("layDanhSachPhanTich", () => {
  it("gửi limit và offset lên URL", async () => {
    fetchMock.mockResolvedValueOnce(
      jsonResponse({ items: [], total: 0, limit: 25, offset: 50 }),
    );
    await layDanhSachPhanTich({ limit: 25, offset: 50 });
    expect(urlDaGoi().searchParams.get("limit")).toBe("25");
    expect(urlDaGoi().searchParams.get("offset")).toBe("50");
  });

  it("kích thước trang mặc định nằm trong trần 100 của backend", () => {
    // Gửi limit > 100 là 422 (đã thử thật). Hằng số này mà vượt trần thì mọi
    // lời gọi đều hỏng, nên khoá lại.
    expect(KICH_THUOC_TRANG_PHAN_TICH).toBeLessThanOrEqual(100);
    expect(KICH_THUOC_TRANG_PHAN_TICH).toBeGreaterThan(0);
  });
});
