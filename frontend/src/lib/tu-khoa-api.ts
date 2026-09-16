/**
 * Lời gọi API của khu Từ khoá & Phân tích AI (#F4) + khoá cache dùng chung.
 *
 * Cùng mẫu với `quan-tri-api.ts` / `nhan-su-api.ts`.
 *
 * **Hình dạng phản hồi không đồng nhất** — đã đối chiếu bằng lời gọi thật lên
 * server đang chạy, không suy từ tên endpoint:
 * - `GET /keywords` trả **mảng trần** (không phân trang, không `PageResponse`)
 * - `GET /analyses` trả `PageResponse`, `limit` trần **100** (gửi 101 là 422)
 * - `DELETE /keywords/{id}` trả **204 No Content**
 */

import { api } from "./api-client";
import type { ConversationAnalysis, Keyword, PageResponse } from "./types";

/** Số dòng mỗi trang phân tích. Backend chặn trần ở 100. */
export const KICH_THUOC_TRANG_PHAN_TICH = 25;

export const khoaTuKhoa = {
  tuKhoa: {
    all: ["tu-khoa"] as const,
  },
  phanTich: {
    all: ["phan-tich"] as const,
    trang: (offset: number) => ["phan-tich", "trang", offset] as const,
  },
};

// ---------------------------------------------------------------------------
// Từ khoá
// ---------------------------------------------------------------------------

/**
 * Mảng trần, KHÔNG phải `PageResponse`. Phạm vi do backend lọc theo vai
 * (`pham_vi_phong_doc`): Admin tất cả, Manager/Staff phòng mình.
 */
export function layDanhSachTuKhoa(signal?: AbortSignal): Promise<Keyword[]> {
  return api.get<Keyword[]>("/keywords", undefined, signal);
}

export function taoTuKhoa(duLieu: {
  department_id: string;
  /** 1..200 ký tự; ngoài khoảng là 422. */
  text: string;
}): Promise<Keyword> {
  return api.post<Keyword>("/keywords", duLieu);
}

/**
 * Đổi nội dung từ khoá.
 *
 * `UpdateKeywordRequest` **chỉ có `text`** — không đổi được phòng của từ khoá
 * (RB-6). Muốn chuyển phòng thì phải xoá rồi tạo lại.
 */
export function suaTuKhoa(keywordId: string, text: string): Promise<Keyword> {
  return api.patch<Keyword>(`/keywords/${keywordId}`, { text });
}

/**
 * Xoá từ khoá.
 *
 * Trả **204 No Content**, không trả `KeywordResponse` — đã xác nhận bằng lời
 * gọi thật. Khai nhầm là `Promise<Keyword>` thì `tsc` vẫn xanh (api-client trả
 * `undefined as T` cho 204) còn UI nhận `undefined` rồi vỡ lúc chạy. Đúng cái
 * bẫy đã dính ở `datLaiMatKhau` của #F2.
 */
export function xoaTuKhoa(keywordId: string): Promise<void> {
  return api.delete<void>(`/keywords/${keywordId}`);
}

// ---------------------------------------------------------------------------
// Phân tích AI
// ---------------------------------------------------------------------------

/** Chỉ đọc. Phạm vi lọc theo `suggested_department_id`. */
export function layDanhSachPhanTich(
  thamSo: { limit: number; offset: number },
  signal?: AbortSignal,
): Promise<PageResponse<ConversationAnalysis>> {
  return api.get<PageResponse<ConversationAnalysis>>(
    "/analyses",
    { limit: thamSo.limit, offset: thamSo.offset },
    signal,
  );
}
