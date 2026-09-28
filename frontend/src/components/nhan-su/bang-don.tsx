"use client";

/**
 * Bảng đơn từ (#F3 task 1.3, redesign Phần 3 D3/X5/X12).
 *
 * Nút "Duyệt"/"Từ chối" hiện theo RB-2 — quy tắc phụ thuộc **vai của người
 * gửi**, không phải của người đang xem. Vai đó không có trong `LeaveRequest`
 * (chỉ có `requester_id`), nên nơi gọi truyền xuống một bảng tra `id → người`.
 *
 * "Duyệt" là nút chính nhỏ trên dòng (việc hay làm nhất ở tab "Chờ duyệt");
 * "Từ chối" / "Thu hồi" nằm trong menu "⋯" và luôn qua hộp xác nhận.
 */

import { Check, Undo2, X } from "lucide-react";
import { t } from "@/lib/i18n";
import { NHAN_LOAI_DON, NHAN_TRANG_THAI_DON, mocDayDu, ngayVN } from "@/lib/hien-thi";
import { mocTuongDoi } from "@/lib/hop-thu";
import { hienDuyet, hienThuHoi, type NguoiNhanSu } from "@/lib/quyen-nhan-su";
import type { LeaveRequest, RequestStatus, UserResponse } from "@/lib/types";
import { Bang, Td, Th, Tr } from "@/components/ui/bang";
import { HuyHieu, type TongHuyHieu } from "@/components/ui/huy-hieu";
import { MenuHanhDong } from "@/components/ui/menu-hanh-dong";
import { Nut } from "@/components/ui/nut";

export type ThaoTacDon = "duyet" | "tuChoi" | "thuHoi";

export const TONG_TRANG_THAI_DON: Record<RequestStatus, TongHuyHieu> = {
  CHO_DUYET: "wait",
  DA_DUYET: "ok",
  TU_CHOI: "bad",
  DA_HUY: "trung",
};

export function BangDon({
  danhSach,
  nguoiTheoId,
  actor,
  chonThaoTac,
}: {
  danhSach: LeaveRequest[];
  /** Tra tên + vai của người gửi. Thiếu người nào thì hiện "Không rõ". */
  nguoiTheoId: Map<string, UserResponse>;
  actor: NguoiNhanSu;
  chonThaoTac: (thaoTac: ThaoTacDon, don: LeaveRequest) => void;
}) {
  const bayGio = new Date();
  return (
    <Bang aria-label={t("don.tieuDe")}>
      <thead>
        <tr>
          <Th className="w-56">{t("don.cotNguoiGui")}</Th>
          <Th className="w-32">{t("don.cotLoaiDon")}</Th>
          <Th>{t("don.cotNoiDung")}</Th>
          <Th className="w-32">{t("don.cotTrangThai")}</Th>
          <Th className="w-28">{t("don.cotNgayGui")}</Th>
          <Th className="w-36">
            <span className="sr-only">{t("nguoiDung.thaoTac")}</span>
          </Th>
        </tr>
      </thead>
      <tbody>
        {danhSach.map((don) => {
          const nguoiGui = nguoiTheoId.get(don.requester_id);
          const coDuyet = hienDuyet(actor, don, nguoiGui?.role ?? null);
          const coThuHoi = hienThuHoi(actor, don);

          return (
            <Tr key={don.id}>
              <Td className="align-top">
                <span className="block truncate font-bold">
                  {nguoiGui?.full_name ?? t("nhatKy.khongRo")}
                  {don.requester_id === actor.id && (
                    <span className="ml-1 font-normal text-ink-2">{t("don.chinhBan")}</span>
                  )}
                </span>
                {nguoiGui && <span className="block truncate text-xs text-ink-2">{nguoiGui.email}</span>}
              </Td>

              <Td className="align-top whitespace-nowrap">{NHAN_LOAI_DON[don.request_type]}</Td>

              <Td className="align-top">
                <span className="block">{don.reason}</span>
                {/* Khoảng nghỉ chỉ có với NGHI_PHEP. */}
                {don.leave_start && don.leave_end && (
                  <span className="mt-0.5 block text-xs font-semibold text-ink-2">
                    {t("don.khoangNghi", { tu: ngayVN(don.leave_start), den: ngayVN(don.leave_end) })}
                  </span>
                )}
                {/* D3: dòng riêng có nhãn — trước đây chữ đỏ lẫn vào nội dung. */}
                {don.decision_reason && (
                  <span className="mt-1.5 block rounded-[4px] border-l-4 border-bad bg-bad-bg px-2 py-1 text-xs text-ink">
                    <span className="font-bold text-bad">{t("don.lyDoTuChoi")}:</span> {don.decision_reason}
                  </span>
                )}
              </Td>

              <Td className="align-top">
                <HuyHieu tong={TONG_TRANG_THAI_DON[don.status]}>{NHAN_TRANG_THAI_DON[don.status]}</HuyHieu>
              </Td>

              <Td className="align-top whitespace-nowrap text-xs text-ink-2">
                <time dateTime={don.created_at} title={mocDayDu(don.created_at)}>
                  {mocTuongDoi(don.created_at, bayGio)}
                </time>
              </Td>

              <Td className="align-top">
                <div className="flex items-center justify-end gap-2">
                  {coDuyet && (
                    <Nut bienThe="chinh" co="sm" icon={Check} onClick={() => chonThaoTac("duyet", don)}>
                      {t("don.duyet")}
                    </Nut>
                  )}
                  <MenuHanhDong
                    nhan={`Thao tác khác với đơn của ${nguoiGui?.full_name ?? t("nhatKy.khongRo")}`}
                    muc={[
                      { nhan: t("don.tuChoi"), icon: X, nguyHiem: true, an: !coDuyet, onChon: () => chonThaoTac("tuChoi", don) },
                      { nhan: t("don.thuHoi"), icon: Undo2, nguyHiem: true, an: !coThuHoi, onChon: () => chonThaoTac("thuHoi", don) },
                    ]}
                  />
                </div>
              </Td>
            </Tr>
          );
        })}
      </tbody>
    </Bang>
  );
}
