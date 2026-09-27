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

import { ApiError, api } from "./api-client";
import type { AnalysisOutcome, ConversationAnalysis, Keyword, PageResponse } from "./types";

/** Số dòng mỗi trang phân tích. Backend chặn trần ở 100. */
export const KICH_THUOC_TRANG_PHAN_TICH = 25;

export const khoaTuKhoa = {
  tuKhoa: {
    all: ["tu-khoa"] as const,
  },
  phanTich: {
    all: ["phan-tich"] as const,
    trang: (offset: number, loc: string) => ["phan-tich", "trang", loc, offset] as const,
    dem: (loc: string) => ["phan-tich", "dem", loc] as const,
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

/**
 * Chỉ đọc. Phạm vi do backend lọc (BE-10): Admin tất cả; Manager phòng đề xuất
 * + hội thoại đang chờ phân; Staff phòng đề xuất.
 *
 * `outcomes` lọc Ở SERVER trên toàn bộ dữ liệu (`?outcome=` lặp được) — lọc ở
 * client sau phân trang chỉ lọc được trang đang xem.
 */
export function layDanhSachPhanTich(
  thamSo: { limit: number; offset: number; outcomes?: readonly AnalysisOutcome[] },
  signal?: AbortSignal,
): Promise<PageResponse<ConversationAnalysis>> {
  return api.get<PageResponse<ConversationAnalysis>>(
    "/analyses",
    { limit: thamSo.limit, offset: thamSo.offset, outcome: thamSo.outcomes },
    signal,
  );
}

/**
 * Từ khoá ĐANG CÓ mà lỗi 409 `KEYWORD_DUPLICATE` chỉ ra (`error.details.existing_keyword`).
 * `null` nếu không phải lỗi trùng hoặc server không gửi kèm — UI khi đó chỉ hiện
 * thông điệp, không đoán (RB-3: FE không tự bỏ dấu để tìm chip trùng).
 */
export function tuKhoaTrung(loi: unknown): { id: string; text: string } | null {
  if (!(loi instanceof ApiError) || loi.code !== "KEYWORD_DUPLICATE") return null;
  const k = (loi.details as { existing_keyword?: { id?: unknown; text?: unknown } } | null)
    ?.existing_keyword;
  return typeof k?.id === "string" && typeof k.text === "string" ? { id: k.id, text: k.text } : null;
}
