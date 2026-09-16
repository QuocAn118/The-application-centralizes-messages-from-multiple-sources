"use client";

/**
 * Lưới lịch phân ca theo tuần: hàng là nhân viên, cột là ngày (#F3 task 2.2).
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
 * **Ô của ngày đã qua không có nút "+".** Backend trả `PAST_SHIFT_DATE` cho
 * ngày quá khứ, nên hiện nút ở đó là mời người dùng vào một thất bại đã biết
 * trước. Buổi ca cũ vẫn hiện bình thường — chỉ không xếp thêm được.
 */

import { t } from "@/lib/i18n";
import { THU_NGAN, gioNgan, ngayVN } from "@/lib/hien-thi";
import type { Shift, ShiftAssignment, UserResponse } from "@/lib/types";

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

  const homNay = (() => {
    const d = new Date();
    const thang = String(d.getMonth() + 1).padStart(2, "0");
    const ngay = String(d.getDate()).padStart(2, "0");
    return `${d.getFullYear()}-${thang}-${ngay}`;
  })();

  return (
    <div className="overflow-x-auto">
      <table className="w-full border-collapse text-left">
        <thead>
          <tr className="border-b border-border-subtle bg-surface/60 text-[11px] font-bold uppercase tracking-wider text-muted">
            <th scope="col" className="w-48 px-4 py-3">
              {t("lich.cotNhanVien")}
            </th>
            {tuan.map((ngay, i) => (
              <th
                key={ngay}
                scope="col"
                className={`px-2 py-3 text-center ${ngay === homNay ? "text-primary" : ""}`}
              >
                <span className="block">{THU_NGAN[i]}</span>
                <span className="block font-normal normal-case">
                  {ngay.slice(8)}/{ngay.slice(5, 7)}
                </span>
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {nhanVien.map((nv) => (
            <tr key={nv.id} className="border-b border-border-subtle last:border-0">
              <td className="px-4 py-2 align-top">
                <span className="block truncate text-sm font-medium text-foreground">
                  {nv.full_name}
                </span>
                <span className="block truncate text-xs text-muted">{nv.email}</span>
              </td>

              {tuan.map((ngay) => {
                const cacBuoi = theoO.get(`${nv.id}|${ngay}`) ?? [];
                const daQua = ngay < homNay;
                return (
                  <td key={ngay} className="px-1.5 py-2 align-top">
                    <div className="flex min-h-[3rem] flex-col gap-1">
                      {cacBuoi.map((b) => {
                        const ca = caTheoId.get(b.shift_id);
                        return (
                          <div
                            key={b.id}
                            className="rounded-md bg-primary-soft px-2 py-1 text-center"
                          >
                            <span className="block truncate text-[11px] font-semibold text-primary">
                              {ca?.name ?? t("nhatKy.khongRo")}
                            </span>
                            <span className="block text-[10px] text-primary/80">
                              {gioNgan(b.start_time)}–{gioNgan(b.end_time)}
                            </span>
                            {xepDuoc && (
                              <button
                                type="button"
                                onClick={() => onHuy(b)}
                                className="mt-0.5 text-[10px] text-muted transition hover:text-danger-fg"
                              >
                                {t("lich.huyPhanCa")}
                              </button>
                            )}
                          </div>
                        );
                      })}

                      {xepDuoc && !daQua && (
                        <button
                          type="button"
                          onClick={() => onXep(nv.id, ngay)}
                          aria-label={t("lich.themVaoO", { ngay: ngayVN(ngay) })}
                          className="rounded-md border border-dashed border-border-subtle py-1 text-[11px] text-muted-soft transition hover:border-primary hover:text-primary"
                        >
                          +
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
