/**
 * Test tầng gọi API của khu quản trị (#F2 task 1.8).
 *
 * Trọng tâm là **cách tham số lên URL và thân yêu cầu**, vì đó là chỗ hỏng mà
 * TypeScript không bắt được: `is_active: false` rất dễ bị coi là "không lọc" và
 * rơi mất, khiến bộ lọc "Đã vô hiệu hoá" im lặng trả về cả danh sách.
 */

import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { __resetApiClientState, setAccessToken } from "./api-client";
import {
  KICH_THUOC_TRANG,
  datLaiMatKhau,
  demNhanVienCuaPhong,
  khoaQuanTri,
  doiPhongBan,
  layDanhSachNguoiDung,
  layDanhSachPhongBan,
  suaKenh,
  taoNguoiDung,
} from "./quan-tri-api";

let fetchMock: ReturnType<typeof vi.fn>;

function jsonResponse(body: unknown): Response {
  return new Response(JSON.stringify(body), {
    status: 200,
    headers: { "Content-Type": "application/json" },
  });
}

/** URL của lần gọi `fetch` thứ `i` (mặc định lần đầu). */
function urlDaGoi(i = 0): URL {
  return new URL(String(fetchMock.mock.calls[i][0]));
}

/** Thân JSON đã gửi ở lần gọi `fetch` thứ `i`. */
function thanDaGui(i = 0): unknown {
  const init = fetchMock.mock.calls[i][1] as RequestInit;
  return JSON.parse(String(init.body));
}

beforeEach(() => {
  __resetApiClientState();
  fetchMock = vi.fn().mockResolvedValue(jsonResponse({ items: [], total: 0 }));
  vi.stubGlobal("fetch", fetchMock);
  setAccessToken("token-test");
});

afterEach(() => {
  vi.unstubAllGlobals();
  __resetApiClientState();
});

describe("layDanhSachNguoiDung", () => {
  it("is_active=false PHẢI lên URL, không được rơi mất", async () => {
    // Đây là lỗi kinh điển: `false` là giá trị falsy nên rất dễ bị lọc cùng
    // `undefined`, làm bộ lọc "Đã vô hiệu hoá" trả về cả danh sách.
    await layDanhSachNguoiDung({ is_active: false, limit: 25, offset: 0 });
    expect(urlDaGoi().searchParams.get("is_active")).toBe("false");
  });

  it("is_active=true lên URL đúng", async () => {
    await layDanhSachNguoiDung({ is_active: true, limit: 25, offset: 0 });
    expect(urlDaGoi().searchParams.get("is_active")).toBe("true");
  });

  it("không lọc trạng thái thì KHÔNG gửi tham số is_active", async () => {
    await layDanhSachNguoiDung({ limit: 25, offset: 0 });
    expect(urlDaGoi().searchParams.has("is_active")).toBe(false);
  });

  it("chuỗi tìm kiếm rỗng không lên URL", async () => {
    // Gửi `search=` khiến backend tìm chuỗi rỗng thay vì bỏ qua bộ lọc.
    await layDanhSachNguoiDung({ search: "", limit: 25, offset: 0 });
    expect(urlDaGoi().searchParams.has("search")).toBe(false);
  });

  it("offset của trang sau đi kèm limit", async () => {
    await layDanhSachNguoiDung({ limit: KICH_THUOC_TRANG, offset: KICH_THUOC_TRANG });
    const url = urlDaGoi();
    expect(url.searchParams.get("limit")).toBe(String(KICH_THUOC_TRANG));
    expect(url.searchParams.get("offset")).toBe(String(KICH_THUOC_TRANG));
  });
});

describe("layDanhSachPhongBan", () => {
  it("lấy trần 100 vì màn quản trị cần thấy cả phòng đã ngừng", async () => {
    await layDanhSachPhongBan();
    const url = urlDaGoi();
    expect(url.pathname).toMatch(/\/departments$/);
    expect(url.searchParams.get("limit")).toBe("100");
    // KHÔNG lọc `is_active`: khác `layPhongBanHoatDong` của #F1.
    expect(url.searchParams.has("is_active")).toBe(false);
  });
});

describe("demNhanVienCuaPhong", () => {
  it("chỉ xin limit=1 vì chỉ cần `total`, không kéo cả danh sách về", async () => {
    fetchMock.mockResolvedValueOnce(
      new Response(JSON.stringify({ items: [], total: 7, limit: 1, offset: 0 }), {
        status: 200,
        headers: { "Content-Type": "application/json" },
      }),
    );
    const so = await demNhanVienCuaPhong("p-1");

    expect(so).toBe(7);
    const url = urlDaGoi();
    expect(url.pathname).toMatch(/\/users$/);
    expect(url.searchParams.get("department_id")).toBe("p-1");
    expect(url.searchParams.get("limit")).toBe("1");
    // Chỉ đếm người ĐANG hoạt động — số này dùng để quyết định có ngừng được
    // phòng không, mà backend cũng chỉ chặn theo người đang hoạt động.
    expect(url.searchParams.get("is_active")).toBe("true");
  });
});

describe("khoá cache đếm nhân viên", () => {
  it("nằm dưới nhánh nguoi-dung để thao tác trên người dùng tự làm mới nó", () => {
    // Nếu để dưới nhánh `phong-ban` thì mỗi lần đổi phòng của một nhân viên
    // phải nhớ vô hiệu hoá hai nhánh — và sẽ có lúc quên, khiến con số trong
    // bảng Phòng ban đứng yên sai.
    const khoa = khoaQuanTri.phongBan.demNhanVien("p-1");
    expect(khoa.slice(0, 2)).toEqual(khoaQuanTri.nguoiDung.all);
  });
});

describe("taoNguoiDung", () => {
  it("Admin gửi department_id = null, không phải chuỗi rỗng", async () => {
    // Backend trả `ADMIN_CANNOT_HAVE_DEPARTMENT` nếu có phòng; "" không phải
    // UUID hợp lệ nên sẽ thành lỗi 422 khó hiểu thay vì hành vi đúng.
    await taoNguoiDung({
      email: "admin2@congty.vn",
      full_name: "Quản trị 2",
      role: "ADMIN",
      department_id: null,
      password: "matkhau123",
    });
    expect(thanDaGui()).toMatchObject({ role: "ADMIN", department_id: null });
  });
});

describe("datLaiMatKhau", () => {
  it("chịu được 204 No Content — endpoint này KHÔNG trả UserResponse", async () => {
    // Phát hiện khi chạy thật: `/users/{id}/reset-password` là endpoint duy
    // nhất của `/users` trả 204. Khai nhầm thành `UserResponse` thì `tsc` vẫn
    // xanh (api-client trả `undefined as T`) nhưng UI nhận `undefined`. Test
    // này khoá đúng chỗ đó.
    fetchMock.mockResolvedValueOnce(new Response(null, { status: 204 }));
    await expect(datLaiMatKhau("u-1", "MatKhauMoi!2026")).resolves.toBeUndefined();
    expect(thanDaGui()).toEqual({ new_password: "MatKhauMoi!2026" });
  });
});

describe("doiPhongBan", () => {
  it("gỡ phòng gửi department_id = null", async () => {
    await doiPhongBan("u-1", null);
    expect(thanDaGui()).toEqual({ department_id: null });
  });
});

describe("suaKenh", () => {
  it("gỡ phòng của kênh phải dùng clear_department, không phải department_id=null", async () => {
    // `UpdateChannelRequest` hiểu `department_id: null` là "không đổi" — chỉ
    // `clear_department: true` mới gỡ thật (RB-7).
    await suaKenh("k-1", { clear_department: true });
    expect(thanDaGui()).toEqual({ clear_department: true });
  });

  it("không gửi credential khi để trống — giữ nguyên token hiện tại", async () => {
    await suaKenh("k-1", { name: "Kênh mới" });
    expect(thanDaGui()).toEqual({ name: "Kênh mới" });
  });
});
