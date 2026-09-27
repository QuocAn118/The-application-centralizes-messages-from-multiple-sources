"use client";

/**
 * Lưới lịch phân ca theo tuần: hàng là nhân viên, cột là ngày (#F3 task 2.2,
 * redesign Phần 3 S2–S5).
 *
 * **Chỉ hiện buổi ACTIVE.** `list_for_scope` của backend KHÔNG lọc `status`
 * (đã đọc `shift_assignment_repository.py:58-81`), nên buổi đã huỷ vẫn nằm
 * trong phản hồi. Không lọc ở đây thì ca đã huỷ vẫn hiện như còn hiệu lực —
 * lỗi im lặng, nhìn vào lịch không thể biết.
 *
 * Hàng nhân viên lấy từ danh sách người dùng chứ không từ chính các buổi ca:
 * người chưa được xếp ca nào vẫn phải có hàng, nếu không thì không bấm vào đâu
 * để xếp cho họ.
 *
 * **Ngày đã qua không xếp thêm được** (backend trả `PAST_SHIFT_DATE`): nền sọc
 * + nhãn "Đã qua", nhưng buổi ca cũ vẫn hiện (S2 — trước đây trông như trống vì
 * không giải thích).
 */

import { Plus, X } from "lucide-react";
import { t } from "@/lib/i18n";
import { THU_NGAN, gioNgan, ngayVN } from "@/lib/hien-thi";
import { lopMau, mauTuId } from "@/components/ui/ban-mau";
import type { Shift, ShiftAssignment, UserResponse } from "@/lib/types";

const NEN_DA_QUA =
  "bg-[repeating-linear-gradient(135deg,var(--sunken)_0_6px,var(--paper)_6px_12px)]";

/** "YYYY-MM-DD" của hôm nay theo giờ máy. */
export function ngayHomNay(d = new Date()): string {
  const thang = String(d.getMonth() + 1).padStart(2, "0");
  const ngay = String(d.getDate()).padStart(2, "0");
  return `${d.getFullYear()}-${thang}-${ngay}`;
}

export function LuoiLich({
  tuan,
  nhanVien,
  buoi,
  caTheoId,
  xepDuoc,
  onXep,
  onHuy,
}: {
  /** Bảy ngày "YYYY-MM-DD", bắt đầu thứ Hai. */
  tuan: string[];
  nhanVien: UserResponse[];
  buoi: ShiftAssignment[];
  caTheoId: Map<string, Shift>;
  /** Manager/Admin mới xếp và huỷ được. */
  xepDuoc: boolean;
  onXep: (userId: string, ngay: string) => void;
  onHuy: (buoiCa: ShiftAssignment) => void;
}) {
  // Gom theo "userId|ngày" để tra O(1) khi vẽ 7 × N ô.
  const theoO = new Map<string, ShiftAssignment[]>();
  for (const b of buoi) {
    if (b.status !== "ACTIVE") continue;
    const khoa = `${b.user_id}|${b.work_date}`;
    const cu = theoO.get(khoa);
    if (cu) cu.push(b);
    else theoO.set(khoa, [b]);
  }

  const homNay = ngayHomNay();

  return (
    <div className="overflow-x-auto">
      <table className="w-full table-fixed border-collapse text-left">
        <thead>
          <tr className="border-b-2 border-ink">
            <th
              scope="col"
              className="w-52 bg-sunken px-4 py-2.5 text-xs font-bold uppercase tracking-wide text-ink-2"
            >
              {t("lich.cotNhanVien")}
            </th>
            {tuan.map((ngay, i) => {
              const laHomNay = ngay === homNay;
              const daQua = ngay < homNay;
              return (
                <th
                  key={ngay}
                  scope="col"
                  aria-current={laHomNay ? "date" : undefined}
                  className={`px-2 py-2 text-center ${
                    laHomNay ? "border-x-[3px] border-t-[3px] border-ink bg-accent" : "bg-sunken"
                  }`}
                >
                  <span className={`block text-xs font-bold uppercase ${daQua ? "text-ink-2" : "text-ink"}`}>
                    {THU_NGAN[i]} {ngay.slice(8)}/{ngay.slice(5, 7)}
                  </span>
                  <span className="block text-xs font-semibold text-ink-2">
                    {laHomNay ? "Hôm nay" : daQua ? "Đã qua" : " "}
                  </span>
                </th>
              );
            })}
          </tr>
        </thead>
        <tbody>
          {nhanVien.map((nv) => (
            <tr key={nv.id} className="border-t border-line first:border-t-0">
              <td className="px-4 py-2 align-top">
                <span className="block truncate text-sm font-semibold text-ink">{nv.full_name}</span>
                <span className="block truncate text-xs text-ink-2">{nv.email}</span>
              </td>

              {tuan.map((ngay) => {
                const cacBuoi = theoO.get(`${nv.id}|${ngay}`) ?? [];
                const daQua = ngay < homNay;
                const laHomNay = ngay === homNay;
                return (
                  <td
                    key={ngay}
                    className={`p-1.5 align-top ${
                      laHomNay ? "border-x-[3px] border-ink bg-swatch-6" : daQua ? NEN_DA_QUA : ""
                    }`}
                  >
                    <div className="flex min-h-14 flex-col gap-1">
                      {cacBuoi.map((b) => {
                        const ca = caTheoId.get(b.shift_id);
                        const ten = ca?.name ?? t("nhatKy.khongRo");
                        return (
                          <div
                            key={b.id}
                            className={`relative rounded-[4px] border-2 border-ink px-2 py-1 ${lopMau(mauTuId(b.shift_id))}`}
                          >
                            <span className="block truncate pr-5 text-xs font-bold text-ink">{ten}</span>
                            <span className="block text-xs text-ink">
                              {gioNgan(b.start_time)}–{gioNgan(b.end_time)}
                            </span>
                            {xepDuoc && (
                              <button
                                type="button"
                                onClick={() => onHuy(b)}
                                aria-label={`${t("lich.huyPhanCa")} ${ten} ngày ${ngayVN(ngay)}`}
                                title={t("lich.huyPhanCa")}
                                className="absolute right-0.5 top-0.5 inline-flex size-6 items-center justify-center rounded-[3px] text-ink hover:bg-ink hover:text-card"
                              >
                                <X aria-hidden className="size-3.5" strokeWidth={2.5} />
                              </button>
                            )}
                          </div>
                        );
                      })}

                      {/* Cả phần còn lại của ô là vùng bấm (S3); "+" rõ khi rê/focus. */}
                      {xepDuoc && !daQua && (
                        <button
                          type="button"
                          onClick={() => onXep(nv.id, ngay)}
                          aria-label={t("lich.themVaoO", { ngay: ngayVN(ngay) })}
                          className="group flex min-h-7 flex-1 items-center justify-center rounded-[4px] border-2 border-dashed border-transparent text-ink-2 hover:border-ink hover:bg-card hover:text-ink focus-visible:border-ink"
                        >
                          <Plus
                            aria-hidden
                            className="size-4 opacity-30 group-hover:opacity-100 group-focus-visible:opacity-100"
                            strokeWidth={2.5}
                          />
                        </button>
                      )}
                    </div>
                  </td>
                );
              })}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

/** Chú giải màu mẫu ca (S4) — chỉ các mẫu đang dùng. */
export function ChuGiaiCa({ ca }: { ca: Shift[] }) {
  if (ca.length === 0) return null;
  return (
    <ul aria-label="Chú giải mẫu ca" className="flex flex-wrap gap-x-4 gap-y-1.5">
      {ca.map((c) => (
        <li key={c.id} className="flex items-center gap-1.5 text-xs font-semibold text-ink">
          <span aria-hidden className={`size-3.5 rounded-[3px] border-2 border-ink ${lopMau(mauTuId(c.id))}`} />
          {c.name} · {gioNgan(c.start_time)}–{gioNgan(c.end_time)}
        </li>
      ))}
    </ul>
  );
}
