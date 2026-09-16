"use client";

/**
 * Bảng đơn từ (#F3 task 1.3).
 *
 * Nút "Duyệt"/"Từ chối" hiện theo RB-2 — quy tắc phụ thuộc **vai của người
 * gửi**, không phải của người đang xem. Vai đó không có trong `LeaveRequest`
 * (chỉ có `requester_id`), nên nơi gọi truyền xuống một bảng tra `id → người`.
 */

import { t } from "@/lib/i18n";
import {
  LOP_BADGE_TRANG_THAI_DON,
  NHAN_LOAI_DON,
  NHAN_TRANG_THAI_DON,
  mocDayDu,
  ngayVN,
} from "@/lib/hien-thi";
import { hienDuyet, hienThuHoi, type NguoiNhanSu } from "@/lib/quyen-nhan-su";
import type { LeaveRequest, UserResponse } from "@/lib/types";

export type ThaoTacDon = "duyet" | "tuChoi" | "thuHoi";

export function BangDon({
  danhSach,
  nguoiTheoId,
  actor,
  chonThaoTac,
}: {
  danhSach: LeaveRequest[];
  /** Tra tên + vai của người gửi. Thiếu người nào thì hiện id rút gọn. */
  nguoiTheoId: Map<string, UserResponse>;
  actor: NguoiNhanSu;
  chonThaoTac: (thaoTac: ThaoTacDon, don: LeaveRequest) => void;
}) {
  return (
    <table className="w-full border-collapse text-left">
      <thead>
        <tr className="border-b border-border-subtle bg-surface/60 text-[11px] font-bold uppercase tracking-wider text-muted">
          <th scope="col" className="w-52 px-5 py-3.5">{t("don.cotNguoiGui")}</th>
          <th scope="col" className="w-32 px-4 py-3.5">{t("don.cotLoaiDon")}</th>
          <th scope="col" className="px-4 py-3.5">{t("don.cotNoiDung")}</th>
          <th scope="col" className="w-32 px-4 py-3.5">{t("don.cotTrangThai")}</th>
          <th scope="col" className="w-40 px-4 py-3.5">{t("don.cotNgayGui")}</th>
          <th scope="col" className="w-48 px-5 py-3.5 text-right">
            <span className="sr-only">{t("nguoiDung.thaoTac")}</span>
          </th>
        </tr>
      </thead>
      <tbody>
        {danhSach.map((don) => {
          const nguoiGui = nguoiTheoId.get(don.requester_id);
          const coDuyet = hienDuyet(actor, don, nguoiGui?.role ?? null);
          const coThuHoi = hienThuHoi(actor, don);

          return (
            <tr key={don.id} className="border-b border-border-subtle last:border-0">
              <td className="px-5 py-3">
                <span className="block truncate text-sm font-semibold text-foreground">
                  {nguoiGui?.full_name ?? t("nhatKy.khongRo")}
                  {don.requester_id === actor.id && (
                    <span className="ml-1 font-normal text-muted-soft">
                      {t("don.chinhBan")}
                    </span>
                  )}
                </span>
                {nguoiGui && (
                  <span className="block truncate text-xs text-muted">
                    {nguoiGui.email}
                  </span>
                )}
              </td>

              <td className="px-4 py-3">
                <span className="whitespace-nowrap text-sm text-foreground">
                  {NHAN_LOAI_DON[don.request_type]}
                </span>
              </td>

              <td className="px-4 py-3">
                <span className="block text-sm text-foreground">{don.reason}</span>
                {/* Khoảng nghỉ chỉ có với NGHI_PHEP. */}
                {don.leave_start && don.leave_end && (
                  <span className="block text-xs text-muted">
                    {t("don.khoangNghi", {
                      tu: ngayVN(don.leave_start),
                      den: ngayVN(don.leave_end),
                    })}
                  </span>
                )}
                {/* Lý do từ chối là thông tin người gửi cần nhất khi đơn hỏng. */}
                {don.decision_reason && (
                  <span className="block text-xs text-danger-fg">
                    {don.decision_reason}
                  </span>
                )}
              </td>

              <td className="px-4 py-3">
                <span
                  className={`inline-block whitespace-nowrap rounded-full px-2.5 py-1 text-xs font-medium ${LOP_BADGE_TRANG_THAI_DON[don.status]}`}
                >
                  {NHAN_TRANG_THAI_DON[don.status]}
                </span>
              </td>

              <td className="px-4 py-3 text-xs text-muted">
                {mocDayDu(don.created_at)}
              </td>

              <td className="px-5 py-3 text-right">
                <div className="flex justify-end gap-2">
                  {coDuyet && (
                    <>
                      <button
                        type="button"
                        onClick={() => chonThaoTac("duyet", don)}
                        className="whitespace-nowrap rounded-lg bg-primary px-3 py-1.5 text-xs font-semibold text-white transition hover:brightness-95"
                      >
                        {t("don.duyet")}
                      </button>
                      <button
                        type="button"
                        onClick={() => chonThaoTac("tuChoi", don)}
                        className="whitespace-nowrap rounded-lg border border-border-subtle px-3 py-1.5 text-xs font-medium text-danger-fg transition hover:bg-danger-bg"
                      >
                        {t("don.tuChoi")}
                      </button>
                    </>
                  )}
                  {coThuHoi && (
                    <button
                      type="button"
                      onClick={() => chonThaoTac("thuHoi", don)}
                      className="whitespace-nowrap rounded-lg border border-border-subtle px-3 py-1.5 text-xs font-medium text-muted transition hover:bg-surface"
                    >
                      {t("don.thuHoi")}
                    </button>
                  )}
                </div>
              </td>
            </tr>
          );
        })}
      </tbody>
    </table>
  );
}
