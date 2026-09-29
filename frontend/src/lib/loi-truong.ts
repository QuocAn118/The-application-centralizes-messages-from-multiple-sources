/**
 * Đặt lỗi server dưới ĐÚNG ô gây ra nó (GĐ1 §4.6 — form dài: Tạo người dùng,
 * Kết nối kênh), thay vì một dòng đỏ chung ở cuối hộp.
 *
 * Nguồn khớp, theo thứ tự:
 * 1. `code` nghiệp vụ (`EMAIL_ALREADY_EXISTS` → ô email) — bảng do nơi gọi đưa;
 * 2. lỗi 422 của FastAPI: `details.cac_loi[].loc` = ["body", "<tên trường>"].
 * Không khớp ô nào → trả `truong: null`, nơi gọi hiện ở dòng lỗi chung.
 *
 * Thông điệp vẫn là của server (`thongDiepLoi`), FE không dịch lại mã.
 */

import { ApiError } from "./api-client";
import { thongDiepLoi } from "./loi-quan-tri";

export function loiTheoTruong<K extends string>(
  loi: unknown,
  theoMa: Partial<Record<string, K>>,
  theoTenTruong: Partial<Record<string, K>> = {},
): { truong: K | null; thongDiep: string } {
  const thongDiep = thongDiepLoi(loi);
  if (!(loi instanceof ApiError)) return { truong: null, thongDiep };

  const theoMaKhop = theoMa[loi.code];
  if (theoMaKhop) return { truong: theoMaKhop, thongDiep };

  const cacLoi = (loi.details as { cac_loi?: { loc?: unknown[]; msg?: string }[] } | null)?.cac_loi;
  for (const l of cacLoi ?? []) {
    const ten = l.loc?.at(-1);
    const truong = typeof ten === "string" ? theoTenTruong[ten] : undefined;
    if (truong) return { truong, thongDiep: "Giá trị ô này không hợp lệ." };
  }
  return { truong: null, thongDiep };
}
