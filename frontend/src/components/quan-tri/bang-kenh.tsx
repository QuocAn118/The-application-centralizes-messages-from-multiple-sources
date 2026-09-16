"use client";

/**
 * Bảng kênh đã kết nối (#F2 task 3.1).
 *
 * **RB-6 — credential không bao giờ xuất hiện ở đây.** `ChannelResponse` của
 * backend cố ý không mang credential về (có ghi chú trong chính schema), nên
 * bảng này không có gì để lộ. Đừng thêm cột nào đọc token, kể cả dạng che dấu:
 * FE không có token để che.
 *
 * Badge nền tảng dùng `LOP_BADGE_KENH`/`NHAN_KENH` — bảng tra phủ đủ 4 giá trị
 * `Platform` và có test duyệt toàn bộ enum (RB-9, bài học TELEGRAM).
 */

import { t } from "@/lib/i18n";
import { LOP_BADGE_KENH, NHAN_KENH } from "@/lib/hien-thi";
import type { Channel, Department } from "@/lib/types";

export type ThaoTacKenh = "sua" | "ngat";

export function BangKenh({
  danhSach,
  phongBan,
  chonThaoTac,
}: {
  danhSach: Channel[];
  phongBan: Department[];
  chonThaoTac: (thaoTac: ThaoTacKenh, kenh: Channel) => void;
}) {
  const tenPhong = new Map(phongBan.map((p) => [p.id, p.name]));

  return (
    <table className="w-full border-collapse text-left">
      <thead>
        <tr className="border-b border-border-subtle bg-surface/60 text-[11px] font-bold uppercase tracking-wider text-muted">
          <th scope="col" className="px-5 py-3.5">{t("kenh.cotKenh")}</th>
          <th scope="col" className="w-32 px-4 py-3.5">{t("kenh.cotNenTang")}</th>
          <th scope="col" className="w-48 px-4 py-3.5">{t("kenh.cotPhongBan")}</th>
          <th scope="col" className="w-40 px-4 py-3.5">{t("kenh.cotTrangThai")}</th>
          <th scope="col" className="w-44 px-5 py-3.5 text-right">
            <span className="sr-only">{t("nguoiDung.thaoTac")}</span>
          </th>
        </tr>
      </thead>
      <tbody>
        {danhSach.map((kenh) => (
          <tr
            key={kenh.id}
            className={`border-b border-border-subtle last:border-0 ${
              kenh.is_active ? "" : "bg-surface/40 opacity-60"
            }`}
          >
            <td className="px-5 py-3">
              <span className="block text-sm font-semibold text-foreground">
                {kenh.name}
              </span>
              {/* Mã kênh trên nền tảng (OA ID / Page ID) — công khai, không
                  phải bí mật. Token mới là bí mật, và nó không có ở đây. */}
              <span className="block truncate font-mono text-xs text-muted">
                {kenh.external_channel_id}
              </span>
            </td>

            <td className="px-4 py-3">
              <span
                className={`inline-block whitespace-nowrap rounded-full px-2.5 py-1 text-xs font-medium ${LOP_BADGE_KENH[kenh.platform]}`}
              >
                {NHAN_KENH[kenh.platform]}
              </span>
            </td>

            <td className="px-4 py-3 text-sm text-foreground">
              {kenh.department_id
                ? (tenPhong.get(kenh.department_id) ?? t("nguoiDung.khongPhong"))
                : t("nguoiDung.khongPhong")}
            </td>

            <td className="px-4 py-3">
              <span
                className={`inline-flex items-center gap-1.5 whitespace-nowrap rounded-full px-2.5 py-1 text-xs font-medium ${
                  kenh.is_active
                    ? "bg-dang-mo-bg text-dang-mo-fg"
                    : "bg-da-dong-bg text-da-dong-fg"
                }`}
              >
                <span aria-hidden className="h-1.5 w-1.5 rounded-full bg-current" />
                {kenh.is_active ? t("kenh.dangKetNoi") : t("kenh.daNgat")}
              </span>
            </td>

            <td className="px-5 py-3 text-right">
              <div className="flex justify-end gap-2">
                <button
                  type="button"
                  onClick={() => chonThaoTac("sua", kenh)}
                  className="whitespace-nowrap rounded-lg border border-border-subtle px-3 py-1.5 text-xs font-medium text-foreground transition hover:bg-surface"
                >
                  {t("kenh.sua")}
                </button>
                {/* Kênh đã ngắt không hiện nút: backend KHÔNG có endpoint kết
                    nối lại (chỉ `deactivate`), giống phòng ban. */}
                {kenh.is_active && (
                  <button
                    type="button"
                    onClick={() => chonThaoTac("ngat", kenh)}
                    className="whitespace-nowrap rounded-lg border border-border-subtle px-3 py-1.5 text-xs font-medium text-danger-fg transition hover:bg-danger-bg"
                  >
                    {t("kenh.ngat")}
                  </button>
                )}
              </div>
            </td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}
