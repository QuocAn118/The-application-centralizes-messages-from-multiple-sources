"use client";

/**
 * Xếp một buổi ca (#F3 task 2.3).
 *
 * **RB-6:** ô chọn nhân viên lọc theo phòng của **mẫu ca đang chọn**, không
 * phải phòng của người đang thao tác — backend trả `AGENT_OUT_OF_DEPARTMENT`
 * nếu lệch. Đổi mẫu ca thì danh sách nhân viên đổi theo, và người đã chọn bị
 * bỏ nếu không còn hợp lệ.
 *
 * **RB-5:** không tự tính trùng giờ ở FE. Logic khoảng-thời-gian có ca qua đêm
 * rất dễ sai, mà backend đã chặn bằng `SHIFT_OVERLAP` kèm thông điệp tiếng
 * Việt — hiện thẳng câu đó.
 */

import { useState } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { t } from "@/lib/i18n";
import { gioNgan, ngayVN } from "@/lib/hien-thi";
import { khoaNhanSu, phanCa } from "@/lib/nhan-su-api";
import { nhanVienPhanCaDuoc } from "@/lib/quyen-nhan-su";
import { thongDiepLoi } from "@/lib/loi-quan-tri";
import { HopThoai, NutChinh, NutPhu } from "@/components/hop-thoai";
import type { Shift, UserResponse } from "@/lib/types";

const LOP_O_NHAP =
  "mt-1 w-full rounded-lg border border-border-subtle bg-white px-3 py-2 text-sm text-foreground outline-none transition focus:border-primary";

export function HopThoaiPhanCa({
  ngay,
  userIdGoiY,
  danhSachCa,
  nhanVien,
  onDong,
}: {
  /** "YYYY-MM-DD" — ô người dùng vừa bấm. */
  ngay: string;
  /** Nhân viên của hàng vừa bấm; có thể không hợp lệ với mẫu ca mặc định. */
  userIdGoiY: string;
  /** Chỉ mẫu ca đang dùng — ca đã ngừng không xếp thêm được. */
  danhSachCa: Shift[];
  nhanVien: UserResponse[];
  onDong: () => void;
}) {
  const queryClient = useQueryClient();
  const [shiftId, setShiftId] = useState(danhSachCa[0]?.id ?? "");
  const [userId, setUserId] = useState(userIdGoiY);

  const caDangChon = danhSachCa.find((c) => c.id === shiftId);
  const nhanVienHopLe = caDangChon
    ? nhanVienPhanCaDuoc(nhanVien, caDangChon.department_id)
    : [];

  // Người ở hàng vừa bấm có thể khác phòng với mẫu ca đang chọn. Suy ra khi
  // render thay vì đồng bộ bằng effect: giá trị này tính được từ dữ liệu.
  const userHopLe = nhanVienHopLe.some((u) => u.id === userId)
    ? userId
    : (nhanVienHopLe[0]?.id ?? "");

  const luu = useMutation({
    mutationFn: () => phanCa({ shift_id: shiftId, user_id: userHopLe, work_date: ngay }),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: khoaNhanSu.phanCa.all });
      onDong();
    },
  });

  return (
    <HopThoai
      tieuDe={t("lich.phanCa")}
      moTa={ngayVN(ngay)}
      loi={luu.isError ? thongDiepLoi(luu.error) : null}
      onDong={onDong}
      chanDuoi={
        <>
          <NutPhu onClick={onDong} disabled={luu.isPending}>
            {t("chung.huy")}
          </NutPhu>
          <NutChinh
            onClick={() => luu.mutate()}
            disabled={luu.isPending || shiftId === "" || userHopLe === ""}
          >
            {luu.isPending ? t("nguoiDung.dangLuu") : t("lich.phanCa")}
          </NutChinh>
        </>
      }
    >
      <div className="mt-4 space-y-3">
        <label className="block">
          <span className="text-xs font-medium text-muted">{t("lich.chonCa")}</span>
          <select
            value={shiftId}
            onChange={(e) => setShiftId(e.target.value)}
            className={LOP_O_NHAP}
          >
            {danhSachCa.map((c) => (
              <option key={c.id} value={c.id}>
                {c.name} ({gioNgan(c.start_time)}–{gioNgan(c.end_time)})
              </option>
            ))}
          </select>
        </label>

        <label className="block">
          <span className="text-xs font-medium text-muted">
            {t("lich.chonNhanVien")}
          </span>
          <select
            value={userHopLe}
            onChange={(e) => setUserId(e.target.value)}
            disabled={nhanVienHopLe.length === 0}
            className={LOP_O_NHAP}
          >
            {nhanVienHopLe.map((u) => (
              <option key={u.id} value={u.id}>
                {u.full_name}
              </option>
            ))}
          </select>
          {nhanVienHopLe.length === 0 && (
            <span className="mt-1 block text-xs text-danger-fg">
              {t("lich.khongCoNhanVien")}
            </span>
          )}
        </label>
      </div>
    </HopThoai>
  );
}
