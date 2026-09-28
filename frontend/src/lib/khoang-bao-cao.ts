/**
 * Khoảng ngày nhanh của Báo cáo (redesign Phần 5 B3): 7 ngày · 30 ngày · Tháng
 * này · Tháng trước. Mọi mốc theo giờ MÁY (ngày địa phương), đóng hai đầu — cùng
 * quy ước ngày nghiệp vụ của backend.
 */

import type { KhoangNgay } from "./bao-cao-api";

export type LoaiKhoangNhanh = "7-ngay" | "30-ngay" | "thang-nay" | "thang-truoc";

export const CAC_KHOANG_NHANH: readonly { loai: LoaiKhoangNhanh; nhan: string }[] = [
  { loai: "7-ngay", nhan: "7 ngày" },
  { loai: "30-ngay", nhan: "30 ngày" },
  { loai: "thang-nay", nhan: "Tháng này" },
  { loai: "thang-truoc", nhan: "Tháng trước" },
];

/** "YYYY-MM-DD" của một ngày theo giờ máy. */
export function iso(d: Date): string {
  const y = d.getFullYear();
  const m = String(d.getMonth() + 1).padStart(2, "0");
  const ng = String(d.getDate()).padStart(2, "0");
  return `${y}-${m}-${ng}`;
}

export function khoangNhanh(loai: LoaiKhoangNhanh, homNay: Date = new Date()): KhoangNgay {
  const y = homNay.getFullYear();
  const m = homNay.getMonth();
  switch (loai) {
    case "7-ngay":
    case "30-ngay": {
      const tu = new Date(y, m, homNay.getDate() - (loai === "7-ngay" ? 6 : 29));
      return { tu: iso(tu), den: iso(homNay) };
    }
    case "thang-nay":
      return { tu: iso(new Date(y, m, 1)), den: iso(homNay) };
    case "thang-truoc":
      // Ngày 0 của tháng này = ngày cuối tháng trước (tự lo tháng 28/29/30/31 và qua năm).
      return { tu: iso(new Date(y, m - 1, 1)), den: iso(new Date(y, m, 0)) };
  }
}

/** Khoảng đang chọn trùng khoảng nhanh nào (để bật nút đó), hoặc `null` nếu tự chọn. */
export function loaiKhoangDangChon(k: KhoangNgay, homNay: Date = new Date()): LoaiKhoangNhanh | null {
  const trung = CAC_KHOANG_NHANH.find(({ loai }) => {
    const n = khoangNhanh(loai, homNay);
    return n.tu === k.tu && n.den === k.den;
  });
  return trung?.loai ?? null;
}
